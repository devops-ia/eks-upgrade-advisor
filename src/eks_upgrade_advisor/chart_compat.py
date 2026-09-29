"""Third-party Helm chart compatibility via the Artifact Hub API."""

from __future__ import annotations

import logging

import httpx

from eks_upgrade_advisor.models import ChartCompatResult, CompatStatus, HelmApp

logger = logging.getLogger(__name__)

ARTIFACT_HUB_API = "https://artifacthub.io/api/v1"


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
        # kubeVersion constraints in Chart.yaml are semver-range expressions
        # (e.g. ">=1.28.0-0"); a full parser belongs here once real ranges
        # from production charts are on hand to test against.
        return CompatStatus.UNKNOWN
