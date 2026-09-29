"""EKS discovery via boto3. Read-only: describe/list calls only."""

from __future__ import annotations

import logging

import boto3

from eks_upgrade_advisor.models import AddonCompatResult, ClusterInfo, CompatStatus, EksAddon

logger = logging.getLogger(__name__)


class EksClient:
    def __init__(self, region: str) -> None:
        self._eks = boto3.client("eks", region_name=region)

    def get_cluster_info(self, cluster_name: str, target_version: str) -> ClusterInfo:
        logger.info("[AWS] Step: describe_cluster action=start cluster=%s", cluster_name)
        resp = self._eks.describe_cluster(name=cluster_name)
        current_version = resp["cluster"]["version"]
        logger.info(
            "[AWS] Step: describe_cluster action=end current=%s target=%s",
            current_version,
            target_version,
        )
        return ClusterInfo(
            name=cluster_name,
            current_version=current_version,
            target_version=target_version,
            region=self._eks.meta.region_name,
        )

    def list_addons(self, cluster_name: str) -> list[EksAddon]:
        logger.info("[AWS] Step: list_addons action=start cluster=%s", cluster_name)
        names = self._eks.list_addons(clusterName=cluster_name)["addons"]
        addons: list[EksAddon] = []
        for name in names:
            detail = self._eks.describe_addon(clusterName=cluster_name, addonName=name)["addon"]
            addons.append(EksAddon(name=name, current_version=detail["addonVersion"]))
        logger.info("[AWS] Step: list_addons action=end total=%s", len(addons))
        return addons

    def check_addon_compat(self, addon: EksAddon, target_version: str) -> AddonCompatResult:
        """Cross-reference an installed addon's version against what AWS
        publishes as compatible with the target Kubernetes version."""
        resp = self._eks.describe_addon_versions(addonName=addon.name, kubernetesVersion=target_version)
        addon_versions = resp.get("addons", [])
        source_url = (
            f"https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html#{addon.name}"
        )
        if not addon_versions:
            return AddonCompatResult(
                addon=addon,
                target_compatible_version=None,
                status=CompatStatus.UNKNOWN,
                source_url=source_url,
            )

        available = {v["addonVersion"] for v in addon_versions[0].get("addonVersions", [])}
        target_compatible_version: str | None
        if addon.current_version in available:
            status = CompatStatus.COMPATIBLE
            target_compatible_version = addon.current_version
        else:
            status = CompatStatus.UPGRADE_REQUIRED
            # Latest returned version is typically the most recent compatible one.
            target_compatible_version = sorted(available)[-1] if available else None

        return AddonCompatResult(
            addon=addon,
            target_compatible_version=target_compatible_version,
            status=status,
            source_url=source_url,
        )
