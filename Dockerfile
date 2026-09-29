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

ARG KUBECTL_VERSION=v1.32.0
ARG HELM_VERSION=v3.16.3
ARG PLUTO_VERSION=5.20.4
ARG TARGETARCH

# System deps: curl/unzip for installers, nodejs/npm for the Copilot CLI (npm package @github/copilot).
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      unzip \
      ca-certificates \
      nodejs \
      npm \
    && rm -rf /var/lib/apt/lists/*

# kubectl
RUN curl -fsSLo /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" && \
    chmod +x /usr/local/bin/kubectl

# helm
RUN curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-${TARGETARCH}.tar.gz" -o /tmp/helm.tar.gz && \
    tar -xzf /tmp/helm.tar.gz -C /tmp && \
    mv /tmp/linux-${TARGETARCH}/helm /usr/local/bin/helm && \
    rm -rf /tmp/helm.tar.gz /tmp/linux-${TARGETARCH}

# pluto (deprecated/removed Kubernetes API detection)
RUN curl -fsSL "https://github.com/FairwindsOps/pluto/releases/download/v${PLUTO_VERSION}/pluto_${PLUTO_VERSION}_linux_${TARGETARCH}.tar.gz" -o /tmp/pluto.tar.gz && \
    tar -xzf /tmp/pluto.tar.gz -C /usr/local/bin pluto && \
    rm -f /tmp/pluto.tar.gz

# aws-cli v2
RUN ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
    curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${ARCH}.zip" -o /tmp/awscliv2.zip && \
    unzip -q /tmp/awscliv2.zip -d /tmp && \
    /tmp/aws/install && \
    rm -rf /tmp/awscliv2.zip /tmp/aws

# GitHub Copilot CLI
RUN npm install -g @github/copilot && npm cache clean --force

# Non-root user
RUN groupadd -r advisor && useradd -r -g advisor -d /app -s /sbin/nologin advisor

COPY --from=builder /install /usr/local
WORKDIR /app
COPY src/ ./src/

RUN mkdir -p /output && chown -R advisor:advisor /app /output

ENV PYTHONPATH=/app/src

USER advisor

ENTRYPOINT ["python", "-m", "eks_upgrade_advisor"]
