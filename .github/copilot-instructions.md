# Copilot Instructions — eks-upgrade-advisor

## Commands

```bash
# Install (editable, no dev extras needed)
pip install -e .
pip install -r requirements-dev.txt

# Run full test suite
python -m pytest

# Run a single test file
python -m pytest tests/test_render.py -v

# Run the tool locally (requires AWS creds + kubeconfig with ArgoCD Application CRDs)
CLUSTER_NAME=prod-eu TARGET_EKS_VERSION=1.32 OUTPUT_PATH=./report.md \
  python -m eks_upgrade_advisor

# Run tests with coverage
python -m pytest --cov=eks_upgrade_advisor --cov-report=term-missing
```

Linters and static analysis (configured in `pyproject.toml`, installed via `requirements-dev.txt`):
```bash
ruff check src/
mypy src/ --ignore-missing-imports
bandit -r src/ -ll -q
```

There is no formatter configured.

---

## Architecture

`eks-upgrade-advisor` is a **one-shot CLI**, not a daemon. It runs to completion inside a
Kubernetes `Job` (bianual EKS version upgrades), writes a Markdown report to `OUTPUT_PATH`,
and exits. `__main__.py` orchestrates the full pipeline in `run()`:

1. **Cluster + addon discovery** (`aws_client.py`) — read-only boto3 calls
   (`describe_cluster`, `list_addons`, `describe_addon`, `describe_addon_versions`) against
   the EKS API. `check_addon_compat` cross-references each installed addon's version against
   what AWS publishes as compatible with the target Kubernetes version.
2. **ArgoCD app discovery** (`k8s_client.py`) — lists `applications.argoproj.io` Custom
   Resources cluster-wide (or scoped to `ARGOCD_NAMESPACE`) via the Kubernetes API. Only
   Applications with a Helm `chart` source are kept; Applications sourced from a plain git
   path (no chart) are silently skipped. `_EKS_MANAGED_ADDON_NAMES` is used to route
   already-EKS-managed charts to the addon compat path instead of Artifact Hub.
3. **Third-party chart compat** (`chart_compat.py`) — queries the Artifact Hub API for each
   non-addon chart. `ArtifactHubClient._resolve_status` is a known stub: kubeVersion
   constraints in `Chart.yaml` are semver-range expressions (e.g. `>=1.28.0-0`) and there is
   no range parser yet — implement one once real-world constraint strings are on hand to
   test against, rather than guessing the grammar.
4. **Deprecated API detection** (`deprecations.py`) — shells out to `helm template` then
   pipes the rendered manifests into `pluto detect -` targeting the upgrade's Kubernetes
   version. Both subprocess calls fail soft (return `[]` + a warning log) rather than
   aborting the whole run — a single broken chart must not blank out the rest of the report.
5. **Changelog summarization** (`changelog_fetch.py` + `llm/`) — **the fetch is deterministic
   and provider-agnostic**: official sources (Kubernetes `CHANGELOG-<version>.md`, AWS EKS
   release notes) are downloaded by this codebase with `httpx`, never by the LLM. The
   `LLMProvider` Protocol (`llm/base.py`) only ever summarizes text it's handed; it must not
   be given browsing/tool access. This is what makes the report's citations trustworthy —
   never change this so the LLM fetches its own sources.
6. **Render** (`report/render.py`) — Jinja2, template lives in `report/template.md.j2`
   (packaged via `importlib.resources`, see `tool.setuptools.package-data` in
   `pyproject.toml` — a new template file must be added there too).

**Data models** live in `models.py` — all shared frozen dataclasses (`ClusterInfo`,
`EksAddon`, `HelmApp`, `AddonCompatResult`, `ChartCompatResult`, `DeprecatedApiFinding`,
`ReportContext`) are defined there. Import from `models.py`; do not define new dataclasses
elsewhere.

**Config** (`config.py`) is env-var only, no YAML — this tool runs as a Helm-templated `Job`
with its full config injected as container env vars, so there's no long-lived config file to
maintain. `CLUSTER_NAME` and `TARGET_EKS_VERSION` are required; everything else defaults.

**LLM provider abstraction** (`llm/base.py`) — `get_provider(name, **kwargs)` is a factory
keyed by `LLM_PROVIDER`. Currently only `copilot-cli` is implemented
(`llm/copilot_cli.py`, invokes the `copilot` binary as a non-interactive subprocess with
`-p`/`-s`, and explicitly denies all tool/URL access with `--deny-tool 'shell(*)'
--deny-url '*'` since it should only ever summarize the context it's given). Adding a new
provider means implementing the `LLMProvider` Protocol and adding a branch to
`get_provider` — never change what `changelog_fetch.py` fetches based on which provider is
selected.

**Logging** follows the structured pattern used across devops-ia Python tools:
```
[Component] Step: step_name action=verb key=value
```
Examples: `[AWS] Step: describe_cluster action=start cluster=prod-eu`,
`[ArgoCD] Step: list_applications action=end total=42`.

---

## Key Conventions

### RBAC / permissions are read-only, always
Every AWS and Kubernetes call in this codebase must remain `describe`/`list`/`get`. This
tool never mutates cluster or AWS state — the actual upgrade is performed by a human,
separately. If a change requires a write permission to implement, stop and flag it rather
than adding the permission.

### Subprocess calls fail soft, not hard
`deprecations.py`'s `helm template` / `pluto detect` calls catch their own exceptions and
return `[]` with a warning log. Follow this pattern for any new subprocess integration — one
broken chart or addon must not abort the whole report.

### `ReportContext` is the single hand-off point to rendering
`render_report()` takes only a `ReportContext`; it has no knowledge of AWS, Kubernetes or the
LLM provider. Any new report field is added to `ReportContext` in `models.py` first, then
threaded through `__main__.py`'s `run()`, then referenced in `template.md.j2`.

### Docker
Multi-stage build: Python deps in `builder`, plus `kubectl`, `helm`, `pluto`, `aws-cli v2`
and the GitHub Copilot CLI (npm package `@github/copilot`, needs Node.js) installed in the
runtime stage. Runs as non-root user `advisor`. No `HEALTHCHECK`/`EXPOSE` — this is a
one-shot `Job`, not a long-running service.

### Testing patterns
- **Render tests** — build `ReportContext` directly with in-memory dataclasses (see
  `test_render.py`), no mocking needed since rendering is pure.
- **Config tests** — use `monkeypatch.setenv`/`delenv` (see `test_config.py`).
- Tests are plain classes with descriptive method names; no pytest markers are used.
