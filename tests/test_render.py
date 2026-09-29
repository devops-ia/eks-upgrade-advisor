from eks_upgrade_advisor.models import (
    AddonCompatResult,
    ChartCompatResult,
    ClusterInfo,
    CompatStatus,
    EksAddon,
    HelmApp,
    ReportContext,
)
from eks_upgrade_advisor.report.render import render_report


class TestRenderReport:
    def test_render_includes_cluster_versions(self):
        cluster = ClusterInfo(name="prod-eu", current_version="1.31", target_version="1.32", region="eu-west-1")
        addon = EksAddon(name="vpc-cni", current_version="1.18.0")
        addon_result = AddonCompatResult(
            addon=addon,
            target_compatible_version="1.19.0",
            status=CompatStatus.UPGRADE_REQUIRED,
            source_url="https://example.com/vpc-cni",
        )
        app = HelmApp(
            name="ingress-nginx",
            namespace="ingress",
            chart="ingress-nginx",
            chart_version="4.10.0",
            repo_url="https://kubernetes.github.io/ingress-nginx",
        )
        chart_result = ChartCompatResult(
            app=app,
            min_kube_version=">=1.28.0-0",
            latest_chart_version="4.11.0",
            status=CompatStatus.UNKNOWN,
            source_url="https://artifacthub.io/packages/helm/ingress-nginx/ingress-nginx",
        )
        ctx = ReportContext(
            cluster=cluster,
            addon_results=[addon_result],
            chart_results=[chart_result],
            deprecated_apis=[],
            changelog_summary="- Ejemplo de feature nueva (fuente: https://example.com)",
        )

        report = render_report(ctx)

        assert "1.31 → 1.32" in report
        assert "vpc-cni" in report
        assert "ingress-nginx" in report
        assert "No se han detectado APIs deprecadas" in report
