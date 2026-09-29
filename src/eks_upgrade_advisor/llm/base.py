"""LLM provider abstraction.

The pipeline is provider-agnostic: it fetches source documents itself
(changelog_fetch.py) and only asks the provider to summarize already-fetched,
already-trusted text. Swapping providers must never change what gets fetched.
"""

from __future__ import annotations

from typing import Protocol

from eks_upgrade_advisor.changelog_fetch import ChangelogSource


class LLMProvider(Protocol):
    def summarize_changelog(
        self,
        current_version: str,
        target_version: str,
        sources: list[ChangelogSource],
    ) -> str:
        """Return a Markdown summary (new features + deprecations), citing
        the source URL for every claim. Must not invent sources beyond what
        was passed in `sources`."""
        ...


def get_provider(name: str, **kwargs: object) -> LLMProvider:
    if name == "copilot-cli":
        from eks_upgrade_advisor.llm.copilot_cli import CopilotCliProvider

        return CopilotCliProvider(**kwargs)  # type: ignore[arg-type]
    raise ValueError(f"Unknown LLM_PROVIDER: {name}")
