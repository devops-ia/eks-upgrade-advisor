"""Entrypoint: orchestrates discovery, compatibility checks and report
rendering. Runs once and exits — this is a Job, not a daemon."""

from __future__ import annotations

import logging
import sys

from eks_upgrade_advisor.aws_client import EksClient
from eks_upgrade_advisor.changelog_fetch import fetch_sources
from eks_upgrade_advisor.chart_compat import ArtifactHubClient
from eks_upgrade_advisor.config import AppConfig, ConfigError
from eks_upgrade_advisor.deprecations import detect_deprecated_apis
from eks_upgrade_advisor.k8s_client import ArgoCdClient
from eks_upgrade_advisor.llm.base import get_provider
from eks_upgrade_advisor.models import ReportContext
from eks_upgrade_advisor.report.render import render_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run(config: AppConfig) -> str:
    eks = EksClient(region=config.aws_region)
    cluster = eks.get_cluster_info(config.cluster_name, config.target_eks_version)

    addons = eks.list_addons(config.cluster_name)
    addon_results = [eks.check_addon_compat(a, config.target_eks_version) for a in addons]

    argocd = ArgoCdClient()
    apps = argocd.list_applications(namespace=config.argocd_namespace)
    third_party_apps = [a for a in apps if not a.is_eks_managed_addon]

    artifact_hub = ArtifactHubClient()
    chart_results = [
        artifact_hub.check_chart_compat(a, config.target_eks_version) for a in third_party_apps
    ]

    deprecated_apis = []
    for app in third_party_apps:
        deprecated_apis.extend(detect_deprecated_apis(app, config.target_eks_version))

    sources = fetch_sources(config.target_eks_version)
    llm = get_provider(config.llm_provider, model=config.copilot_model)
    changelog_summary = llm.summarize_changelog(
        current_version=cluster.current_version,
        target_version=cluster.target_version,
        sources=sources,
    )

    ctx = ReportContext(
        cluster=cluster,
        addon_results=addon_results,
        chart_results=chart_results,
        deprecated_apis=deprecated_apis,
        changelog_summary=changelog_summary,
    )
    return render_report(ctx)


def main() -> None:
    try:
        config = AppConfig.from_env()
    except ConfigError as exc:
        logger.error("[Core] Step: load_config action=fail error=%s", exc)
        sys.exit(1)

    logger.info(
        "[Core] Step: run action=start cluster=%s target=%s",
        config.cluster_name,
        config.target_eks_version,
    )
    report = run(config)

    with open(config.output_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info("[Core] Step: run action=end output=%s", config.output_path)


if __name__ == "__main__":
    main()
