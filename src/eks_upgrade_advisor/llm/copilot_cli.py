"""GitHub Copilot CLI provider (github/copilot-cli), invoked as a subprocess
in non-interactive mode.

All tool/URL access is denied — this pipeline already fetches the source
documents itself (changelog_fetch.py) and passes their content as context, so
the CLI has nothing left to do but summarize text it's given.
"""

from __future__ import annotations

import logging
import shutil
import subprocess

from eks_upgrade_advisor.changelog_fetch import ChangelogSource

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
You are a Senior Site Reliability Engineer writing the "changelog" section of \
a formal Kubernetes/EKS upgrade compatibility report, from version \
{current_version} to {target_version}. The audience is other SREs deciding \
whether the upgrade is safe to schedule, so the tone must be technical and \
professional: precise, neutral, no marketing language, no filler sentences.

Grounding rules (do not deviate):
- Use ONLY the content under "SOURCES" below. Do not use prior knowledge of \
Kubernetes/EKS releases, and do not infer or guess anything not explicitly \
stated in the provided text.
- Every bullet MUST end with a citation of the exact source URL it came from, \
in the form `(source: <url>)`. A bullet with no direct textual support in the \
sources must not be written.
- If a section has no relevant findings in the sources, write exactly: \
`- No relevant changes found in the provided sources.` for that section. \
Never leave a section silently empty and never pad it with speculation.
- Do not editorialize on business impact, urgency, or recommendations — state \
facts only. That judgment is made by the human reading the report.

Output language: write the summary content itself in Spanish (the rest of the \
report this section is embedded in is in Spanish), while still following \
every rule above exactly.

Output structure (Markdown, nothing outside this structure — no preamble, no \
closing remarks):

## Novedades y features relevantes
- <finding> (source: <url>)

## APIs y funcionalidades obsoletas o eliminadas
- <finding> (source: <url>)

## Otros cambios con impacto operativo
- <finding> (source: <url>)

--- SOURCES ---

{sources_block}
"""


class CopilotCliProvider:
    def __init__(self, model: str = "claude-sonnet-4.5", binary: str = "copilot") -> None:
        self.model = model
        self.binary = binary

    def summarize_changelog(
        self,
        current_version: str,
        target_version: str,
        sources: list[ChangelogSource],
    ) -> str:
        if not sources:
            return "_No se pudieron descargar fuentes oficiales; revisar manualmente._"

        sources_block = "\n\n".join(
            f"### Fuente: {s.url}\n\n{s.content[:20000]}" for s in sources
        )
        prompt = _PROMPT_TEMPLATE.format(
            current_version=current_version,
            target_version=target_version,
            sources_block=sources_block,
        )

        # Resolve to an absolute path (rather than letting subprocess search
        # PATH implicitly) — satisfies bandit's B607 and fails fast with a
        # clear error if the image is missing the Copilot CLI.
        binary_path = shutil.which(self.binary)
        if binary_path is None:
            raise RuntimeError(f"required binary not found on PATH: {self.binary}")

        logger.info("[CopilotCLI] Step: summarize action=start model=%s", self.model)
        result = subprocess.run(
            [
                binary_path,
                "--model", self.model,
                "-p", prompt,
                "-s",
                "--no-color",
                "--no-auto-update",
                "--deny-tool", "shell(*)",
                "--deny-url", "*",
            ],
            capture_output=True, text=True, timeout=300, check=True,
        )
        logger.info("[CopilotCLI] Step: summarize action=end bytes=%s", len(result.stdout))
        return result.stdout.strip()
