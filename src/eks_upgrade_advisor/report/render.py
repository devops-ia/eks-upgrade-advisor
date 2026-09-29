from __future__ import annotations

from importlib import resources

from jinja2 import Environment

from eks_upgrade_advisor.models import ReportContext


def render_report(ctx: ReportContext) -> str:
    template_source = resources.files("eks_upgrade_advisor.report").joinpath("template.md.j2").read_text()
    env = Environment(trim_blocks=True, lstrip_blocks=True)
    template = env.from_string(template_source)
    return template.render(
        cluster=ctx.cluster,
        addon_results=ctx.addon_results,
        chart_results=ctx.chart_results,
        deprecated_apis=ctx.deprecated_apis,
        changelog_summary=ctx.changelog_summary,
    )
