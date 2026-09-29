"""Runtime configuration, loaded from environment variables.

Kept intentionally flat (env-var only, no YAML) since this tool runs as a
one-shot Job with its full config injected by the Helm chart.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class AppConfig:
    cluster_name: str
    target_eks_version: str
    aws_region: str
    argocd_namespace: str | None
    """If set, only Applications in this namespace are discovered. None = all namespaces."""
    llm_provider: str
    copilot_model: str
    output_path: str

    @staticmethod
    def from_env() -> AppConfig:
        cluster_name = os.environ.get("CLUSTER_NAME")
        target_version = os.environ.get("TARGET_EKS_VERSION")
        if not cluster_name:
            raise ConfigError("CLUSTER_NAME is required")
        if not target_version:
            raise ConfigError("TARGET_EKS_VERSION is required")

        return AppConfig(
            cluster_name=cluster_name,
            target_eks_version=target_version,
            aws_region=os.environ.get("AWS_REGION", "eu-west-1"),
            argocd_namespace=os.environ.get("ARGOCD_NAMESPACE") or None,
            llm_provider=os.environ.get("LLM_PROVIDER", "copilot-cli"),
            copilot_model=os.environ.get("COPILOT_MODEL", "claude-sonnet-4.5"),
            output_path=os.environ.get("OUTPUT_PATH", "/output/report.md"),
        )
