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
Eres un asistente de SRE. Resume, en Markdown, los cambios relevantes para un \
upgrade de Kubernetes/EKS de la version {current_version} a {target_version}.

Usa EXCLUSIVAMENTE el contenido de las fuentes que se incluyen a continuacion. \
No añadas informacion que no este en ellas. Cita la URL de la fuente en cada \
punto que menciones.

Estructura de salida (nada de texto fuera de esta estructura):

## Features nuevas relevantes
- <punto> (fuente: <url>)

## APIs / funcionalidades deprecadas
- <punto> (fuente: <url>)

--- FUENTES ---

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
