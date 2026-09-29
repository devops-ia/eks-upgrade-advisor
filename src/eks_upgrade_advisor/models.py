"""Shared data models.

All dataclasses used across the codebase live here. Do not define new
dataclasses in discovery/compat/report modules — import from here instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CompatStatus(str, Enum):
    COMPATIBLE = "compatible"
    UPGRADE_REQUIRED = "upgrade_required"
    UNKNOWN = "unknown"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class ClusterInfo:
    name: str
    current_version: str
    target_version: str
    region: str


@dataclass(frozen=True)
class EksAddon:
    """An EKS-managed addon (vpc-cni, coredns, kube-proxy, ebs-csi, ...)."""

    name: str
    current_version: str


@dataclass(frozen=True)
class HelmApp:
    """A Helm application discovered from an ArgoCD Application resource."""

    name: str
    namespace: str
    chart: str
    chart_version: str
    repo_url: str
    is_eks_managed_addon: bool = False


@dataclass(frozen=True)
class AddonCompatResult:
    addon: EksAddon
    target_compatible_version: str | None
    status: CompatStatus
    source_url: str


@dataclass(frozen=True)
class ChartCompatResult:
    app: HelmApp
    min_kube_version: str | None
    latest_chart_version: str | None
    status: CompatStatus
    source_url: str


@dataclass(frozen=True)
class DeprecatedApiFinding:
    chart_name: str
    api_version: str
    kind: str
    replacement: str | None
    removed_in_version: str | None


@dataclass(frozen=True)
class ClusterInventory:
    cluster: ClusterInfo
    addons: list[EksAddon] = field(default_factory=list)
    apps: list[HelmApp] = field(default_factory=list)


@dataclass(frozen=True)
class ReportContext:
    """Everything the report template needs, fully resolved before rendering."""

    cluster: ClusterInfo
    addon_results: list[AddonCompatResult]
    chart_results: list[ChartCompatResult]
    deprecated_apis: list[DeprecatedApiFinding]
    changelog_summary: str
    """LLM-generated Markdown summary of new features / deprecations, with citations."""
