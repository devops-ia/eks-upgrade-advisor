from __future__ import annotations

from importlib import resources

from jinja2 import Environment

from eks_upgrade_advisor.models import ReportContext


def render_report(ctx: ReportContext) -> str:
    template_source = resources.files("eks_upgrade_advisor.report").joinpath("template.md.j2").read_text()
    # autoescape is HTML/XML escaping (&, <, > -> entities) and deliberately
    # off: the output is plain Markdown, not HTML rendered in a browser, so
    # there is no XSS surface here — enabling it would instead corrupt
    # ordinary characters (e.g. "&" in a chart name) in the report text.
    env = Environment(trim_blocks=True, lstrip_blocks=True, autoescape=False)  # nosec B701
    template = env.from_string(template_source)
    return template.render(
        cluster=ctx.cluster,
        addon_results=ctx.addon_results,
        chart_results=ctx.chart_results,
        deprecated_apis=ctx.deprecated_apis,
        changelog_summary=ctx.changelog_summary,
    )
