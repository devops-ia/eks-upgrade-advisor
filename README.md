# eks-upgrade-advisor

> Auto-discovers EKS addons and ArgoCD-managed Helm charts on a cluster, cross-checks
> compatibility with a target EKS/Kubernetes version, detects deprecated APIs, and generates
> a Markdown upgrade report — citing official sources throughout.

Runs as a one-shot Kubernetes `Job` with read-only RBAC. It does not perform the upgrade
itself; the report is meant to be read by a human before any change is made.

## What it does

1. Reads the cluster's current EKS version and installed addons (AWS API).
2. Reads all ArgoCD `Application` resources to inventory Helm-deployed apps, including which
   Git repo each one is deployed from.
3. Checks each EKS-managed addon against `aws eks describe-addon-versions` for the target
   version.
4. Checks third-party charts against the Artifact Hub API.
5. Renders each chart with `helm template` and runs
   [`pluto`](https://github.com/FairwindsOps/pluto) against it to flag deprecated/removed
   Kubernetes APIs.
6. Fetches the official Kubernetes and AWS EKS changelogs itself (deterministically, via
   HTTP) and asks an LLM to summarize new features and deprecations — the model only ever
   sees text this tool already downloaded, so every claim in the report is traceable to an
   official source URL.

## Run

```bash
CLUSTER_NAME=prod-eu \
TARGET_EKS_VERSION=1.32 \
AWS_REGION=eu-west-1 \
OUTPUT_PATH=./report.md \
python -m eks_upgrade_advisor
```

Requires AWS credentials with `eks:Describe*`/`eks:List*` and a kubeconfig (or in-cluster
ServiceAccount) with read access to `applications.argoproj.io`.

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `CLUSTER_NAME` | yes | — | EKS cluster name |
| `TARGET_EKS_VERSION` | yes | — | EKS/Kubernetes version to upgrade to (e.g. `1.32`) |
| `AWS_REGION` | no | `eu-west-1` | AWS region of the cluster |
| `ARGOCD_NAMESPACE` | no | all namespaces | Restrict ArgoCD Application discovery to one namespace |
| `LLM_PROVIDER` | no | `copilot-cli` | LLM provider used to summarize changelogs |
| `COPILOT_MODEL` | no | `claude-sonnet-4.5` | Model passed to the Copilot CLI |
| `OUTPUT_PATH` | no | `/output/report.md` | Where the rendered report is written |

## Deploying

A Helm chart is published separately: [`helm-eks-upgrade-advisor`](https://github.com/devops-ia/helm-eks-upgrade-advisor).

## Development

```bash
pip install -e .
pip install -r requirements-dev.txt

python -m pytest --cov=eks_upgrade_advisor --cov-report=term-missing
ruff check src/
mypy src/ --ignore-missing-imports
bandit -r src/ -ll -q
```

## License

MIT — see [LICENSE](LICENSE).
