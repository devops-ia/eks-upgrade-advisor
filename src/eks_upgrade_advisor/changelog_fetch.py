"""Deterministic fetch of official changelog sources.

Downloading the source text ourselves (instead of letting the LLM browse) is
what makes the citations in the final report trustworthy: the model only
ever summarizes text we already know came from the official source.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

K8S_CHANGELOG_URL_TPL = (
    "https://raw.githubusercontent.com/kubernetes/kubernetes/master/"
    "CHANGELOG/CHANGELOG-{version}.md"
)
EKS_RELEASE_NOTES_URL = "https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html"


class ChangelogSource:
    """A fetched document, kept alongside the URL it came from for citation."""

    def __init__(self, url: str, content: str) -> None:
        self.url = url
        self.content = content


def fetch_sources(target_version: str, http_client: httpx.Client | None = None) -> list[ChangelogSource]:
    client = http_client or httpx.Client(timeout=30.0, follow_redirects=True)

    k8s_url = K8S_CHANGELOG_URL_TPL.format(version=target_version)
    fetched: list[ChangelogSource | None] = [
        _fetch(client, k8s_url),
        _fetch(client, EKS_RELEASE_NOTES_URL),
    ]

    return [s for s in fetched if s is not None]


def _fetch(client: httpx.Client, url: str) -> ChangelogSource | None:
    logger.info("[Changelog] Step: fetch action=start url=%s", url)
    try:
        resp = client.get(url)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("[Changelog] Step: fetch action=fail url=%s error=%s", url, exc)
        return None
    logger.info("[Changelog] Step: fetch action=end url=%s bytes=%s", url, len(resp.text))
    return ChangelogSource(url=url, content=resp.text)
