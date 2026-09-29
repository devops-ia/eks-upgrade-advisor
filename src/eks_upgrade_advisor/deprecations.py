"""Deprecated/removed Kubernetes API detection via `pluto` (FairwindsOps/pluto).

Renders each Helm chart with `helm template` and pipes the manifests through
`pluto detect -` targeting the upgrade's target Kubernetes version.
"""

from __future__ import annotations

import json
import logging
import subprocess

from eks_upgrade_advisor.models import DeprecatedApiFinding, HelmApp

logger = logging.getLogger(__name__)


def detect_deprecated_apis(app: HelmApp, target_kube_version: str) -> list[DeprecatedApiFinding]:
    try:
        template = subprocess.run(
            [
                "helm", "template", app.name,
                app.chart,
                "--repo", app.repo_url,
                "--version", app.chart_version,
            ],
            capture_output=True, text=True, timeout=120, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        logger.warning("[Pluto] Step: helm_template action=fail app=%s error=%s", app.name, exc)
        return []

    try:
        pluto_result = subprocess.run(
            [
                "pluto", "detect", "-",
                "--target-versions", f"k8s={target_kube_version}",
                "-o", "json",
            ],
            input=template.stdout,
            capture_output=True, text=True, timeout=60, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logger.warning("[Pluto] Step: detect action=fail app=%s error=%s", app.name, exc)
        return []

    if not pluto_result.stdout.strip():
        return []

    try:
        parsed = json.loads(pluto_result.stdout)
    except json.JSONDecodeError:
        logger.warning("[Pluto] Step: detect action=parse_fail app=%s", app.name)
        return []

    findings = []
    for item in parsed.get("items", []):
        findings.append(
            DeprecatedApiFinding(
                chart_name=app.name,
                api_version=item.get("api", ""),
                kind=item.get("kind", ""),
                replacement=item.get("replacement-api") or None,
                removed_in_version=item.get("removed-in") or None,
            )
        )
    return findings
