"""Third-party Helm chart compatibility via the Artifact Hub API."""

from __future__ import annotations

import logging
import re

import httpx

from eks_upgrade_advisor.models import ChartCompatResult, CompatStatus, HelmApp

logger = logging.getLogger(__name__)

ARTIFACT_HUB_API = "https://artifacthub.io/api/v1"

_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)(?:\.(\d+))?")
_TERM_RE = re.compile(r"^(>=|<=|>|<|=)?\s*(.+)$")


def _parse_version(raw: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.match(raw.strip())
    if not match:
        return None
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def _eval_term(term: str, version: tuple[int, int, int]) -> bool | None:
    match = _TERM_RE.match(term.strip())
    if not match:
        return None
    op, raw_version = match.groups()
    target = _parse_version(raw_version)
    if target is None:
        return None
    op = op or "="
    if op == ">=":
        return version >= target
    if op == "<=":
        return version <= target
    if op == ">":
        return version > target
    if op == "<":
        return version < target
    return version == target


def _kube_version_satisfies(constraint: str, version: tuple[int, int, int]) -> bool | None:
    """Evaluate a Chart.yaml `kubeVersion` range against a target k8s version.

    Helm follows the Masterminds/semver range syntax: comma-separated terms
    within a group are AND'd (e.g. ">=1.28.0-0,<1.31.0"), and "||"-separated
    groups are OR'd. Returns None — never a guess — when every group
    contains a term this parser can't understand, so an unparseable
    constraint surfaces as CompatStatus.UNKNOWN rather than a false
    "compatible"/"upgrade_required" verdict.
    """
    any_group_parsed = False
    for group in constraint.split("||"):
        terms = [t for t in group.split(",") if t.strip()]
        if not terms:
            continue
        results = [_eval_term(t, version) for t in terms]
        if any(r is None for r in results):
            continue
        any_group_parsed = True
        if all(results):
            return True
    return False if any_group_parsed else None


class ArtifactHubClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self._client = http_client or httpx.Client(timeout=15.0)

    def check_chart_compat(self, app: HelmApp, target_kube_version: str) -> ChartCompatResult:
        source_url = f"https://artifacthub.io/packages/search?ts_query_web={app.chart}"
        pkg = self._find_package(app.chart)
        if pkg is None:
            logger.warning("[ArtifactHub] Step: search action=miss chart=%s", app.chart)
            return ChartCompatResult(
                app=app,
                min_kube_version=None,
                latest_chart_version=None,
                status=CompatStatus.UNKNOWN,
                source_url=source_url,
            )

        min_kube_version = pkg.get("data", {}).get("kubeVersion")
        latest_version = pkg.get("version")
        status = self._resolve_status(min_kube_version, target_kube_version)
        return ChartCompatResult(
            app=app,
            min_kube_version=min_kube_version,
            latest_chart_version=latest_version,
            status=status,
            source_url=f"https://artifacthub.io/packages/helm/{pkg.get('repository', {}).get('name', '')}/{app.chart}",
        )

    def _find_package(self, chart_name: str) -> dict | None:
        resp = self._client.get(
            f"{ARTIFACT_HUB_API}/packages/search",
            params={"kind": "0", "ts_query_web": chart_name, "limit": 1},
        )
        resp.raise_for_status()
        packages = resp.json().get("packages", [])
        return packages[0] if packages else None

    @staticmethod
    def _resolve_status(min_kube_version: str | None, target_kube_version: str) -> CompatStatus:
        if not min_kube_version:
            return CompatStatus.UNKNOWN

        target = _parse_version(target_kube_version)
        if target is None:
            return CompatStatus.UNKNOWN

        satisfied = _kube_version_satisfies(min_kube_version, target)
        if satisfied is None:
            return CompatStatus.UNKNOWN
        return CompatStatus.COMPATIBLE if satisfied else CompatStatus.UPGRADE_REQUIRED
