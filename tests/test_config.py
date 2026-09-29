import pytest

from eks_upgrade_advisor.config import AppConfig, ConfigError


class TestAppConfig:
    def test_from_env_requires_cluster_name(self, monkeypatch):
        monkeypatch.delenv("CLUSTER_NAME", raising=False)
        monkeypatch.setenv("TARGET_EKS_VERSION", "1.32")
        with pytest.raises(ConfigError):
            AppConfig.from_env()

    def test_from_env_requires_target_version(self, monkeypatch):
        monkeypatch.setenv("CLUSTER_NAME", "prod-eu")
        monkeypatch.delenv("TARGET_EKS_VERSION", raising=False)
        with pytest.raises(ConfigError):
            AppConfig.from_env()

    def test_from_env_applies_defaults(self, monkeypatch):
        monkeypatch.setenv("CLUSTER_NAME", "prod-eu")
        monkeypatch.setenv("TARGET_EKS_VERSION", "1.32")
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        config = AppConfig.from_env()

        assert config.cluster_name == "prod-eu"
        assert config.target_eks_version == "1.32"
        assert config.aws_region == "eu-west-1"
        assert config.llm_provider == "copilot-cli"
        assert config.argocd_namespace is None
