"""ArgoCD Application discovery via the Kubernetes API.

Read-only: only `get`/`list` on `applications.argoproj.io`. Intended to run
in-cluster (loads the ServiceAccount's mounted config); falls back to the
local kubeconfig for local development.
"""

from __future__ import annotations

import logging

from kubernetes import client, config

from eks_upgrade_advisor.models import HelmApp

logger = logging.getLogger(__name__)

ARGOCD_GROUP = "argoproj.io"
ARGOCD_VERSION = "v1alpha1"
ARGOCD_PLURAL = "applications"

# Charts that ship as EKS-managed addons rather than third-party Helm charts.
# Their compatibility is checked against the AWS API instead of Artifact Hub.
_EKS_MANAGED_ADDON_NAMES = {
    "vpc-cni",
    "coredns",
    "kube-proxy",
    "aws-ebs-csi-driver",
    "aws-efs-csi-driver",
    "aws-load-balancer-controller",
    "eks-pod-identity-agent",
}


def _load_kube_config() -> None:
    try:
        config.load_incluster_config()
        logger.info("[K8s] Step: load_config action=end mode=in-cluster")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("[K8s] Step: load_config action=end mode=kubeconfig")


class ArgoCdClient:
    def __init__(self) -> None:
        _load_kube_config()
        self._api = client.CustomObjectsApi()

    def list_applications(self, namespace: str | None = None) -> list[HelmApp]:
        logger.info("[ArgoCD] Step: list_applications action=start namespace=%s", namespace or "*")

        if namespace:
            items = self._api.list_namespaced_custom_object(
                group=ARGOCD_GROUP,
                version=ARGOCD_VERSION,
                namespace=namespace,
                plural=ARGOCD_PLURAL,
            )["items"]
        else:
            items = self._api.list_cluster_custom_object(
                group=ARGOCD_GROUP,
                version=ARGOCD_VERSION,
                plural=ARGOCD_PLURAL,
            )["items"]

        apps = [app for item in items if (app := self._parse_application(item)) is not None]
        logger.info("[ArgoCD] Step: list_applications action=end total=%s", len(apps))
        return apps

    @staticmethod
    def _parse_application(item: dict) -> HelmApp | None:
        meta = item.get("metadata", {})
        spec = item.get("spec", {})
        source = spec.get("source") or (spec.get("sources") or [{}])[0]

        chart = source.get("chart")
        if not chart:
            # Not a Helm-sourced Application (could be a plain-manifest/kustomize app).
            return None

        return HelmApp(
            name=meta.get("name", "unknown"),
            namespace=meta.get("namespace", "unknown"),
            chart=chart,
            chart_version=source.get("targetRevision", "unknown"),
            repo_url=source.get("repoURL", "unknown"),
            is_eks_managed_addon=chart in _EKS_MANAGED_ADDON_NAMES,
        )
