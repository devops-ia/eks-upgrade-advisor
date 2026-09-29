# ============================================================
# Stage 1: Install Python dependencies
# ============================================================
FROM python:3.14-slim AS builder

WORKDIR /build
COPY requirements.txt pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    pip install --no-cache-dir --prefix=/install --no-deps .

# ============================================================
# Stage 2: Runtime image
# ============================================================
FROM python:3.14-slim

LABEL maintainer="devops-ia"

# helm / pluto / the Copilot CLI are the only external binaries this tool
# actually shells out to (see deprecations.py and llm/copilot_cli.py).
# kubectl and aws-cli were dropped: all AWS/Kubernetes API access goes
# through boto3 and the kubernetes Python client, never a CLI subprocess.
ARG HELM_VERSION=v3.16.3
ARG PLUTO_VERSION=5.24.1
ARG COPILOT_CLI_VERSION=1.0.89
ARG TARGETARCH

# System deps: curl for installers, nodejs/npm for the Copilot CLI (npm
# package @github/copilot).
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      ca-certificates \
      nodejs \
      npm \
    && rm -rf /var/lib/apt/lists/*

# helm — downloaded tarball is verified against the project's published
# sha256 before extraction.
RUN curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-${TARGETARCH}.tar.gz" -o /tmp/helm.tar.gz && \
    curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-${TARGETARCH}.tar.gz.sha256" -o /tmp/helm.tar.gz.sha256 && \
    echo "$(cat /tmp/helm.tar.gz.sha256)  /tmp/helm.tar.gz" | sha256sum -c - && \
    tar -xzf /tmp/helm.tar.gz -C /tmp && \
    mv /tmp/linux-${TARGETARCH}/helm /usr/local/bin/helm && \
    rm -rf /tmp/helm.tar.gz /tmp/helm.tar.gz.sha256 /tmp/linux-${TARGETARCH}

# pluto (deprecated/removed Kubernetes API detection) — verified against the
# release's checksums.txt (goreleaser's default, fixed filename per release).
RUN curl -fsSL "https://github.com/FairwindsOps/pluto/releases/download/v${PLUTO_VERSION}/pluto_${PLUTO_VERSION}_linux_${TARGETARCH}.tar.gz" -o /tmp/pluto.tar.gz && \
    curl -fsSL "https://github.com/FairwindsOps/pluto/releases/download/v${PLUTO_VERSION}/checksums.txt" -o /tmp/pluto_checksums.txt && \
    (cd /tmp && grep " pluto_${PLUTO_VERSION}_linux_${TARGETARCH}.tar.gz\$" pluto_checksums.txt | sha256sum -c -) && \
    tar -xzf /tmp/pluto.tar.gz -C /usr/local/bin pluto && \
    rm -f /tmp/pluto.tar.gz /tmp/pluto_checksums.txt

# GitHub Copilot CLI — version pinned (npm install -g without a version
# resolves to whatever is "latest" at build time, which is not reproducible
# between builds of the same commit).
RUN npm install -g "@github/copilot@${COPILOT_CLI_VERSION}" && npm cache clean --force

# Non-root user. Home is a dedicated, empty-by-default directory (not /app,
# which holds the read-only application code) so it can be mounted as a
# writable emptyDir at runtime — the Copilot CLI persists session state
# under $HOME, and that's the only runtime write this container needs
# outside of /output. This is what lets the Helm chart run the pod with
# readOnlyRootFilesystem: true.
RUN groupadd -r advisor && useradd -r -g advisor -d /home/advisor -s /sbin/nologin advisor

COPY --from=builder /install /usr/local
WORKDIR /app
COPY src/ ./src/

RUN mkdir -p /output /home/advisor && chown -R advisor:advisor /app /output /home/advisor

ENV PYTHONPATH=/app/src
ENV HOME=/home/advisor

USER advisor

ENTRYPOINT ["python", "-m", "eks_upgrade_advisor"]
