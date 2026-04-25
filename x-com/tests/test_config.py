from __future__ import annotations

import pytest

from x_com.config import ConfigError, load_config


def test_load_config_reads_standard_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTKIT_X_COM_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("AGENTKIT_X_COM_API_BASE_URL", "https://api.x.com")

    config = load_config()

    assert config.bearer_token == "token-123"
    assert config.api_base_url == "https://api.x.com"


def test_load_config_requires_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTKIT_X_COM_BEARER_TOKEN", raising=False)

    with pytest.raises(ConfigError, match="AGENTKIT_X_COM_BEARER_TOKEN"):
        load_config()


def test_load_config_reads_explicit_env_file(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AGENTKIT_X_COM_BEARER_TOKEN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AGENTKIT_X_COM_BEARER_TOKEN=file-token\n"
        "AGENTKIT_X_COM_API_BASE_URL=https://file.example\n",
        encoding="utf-8",
    )

    config = load_config(env_file=env_file, allow_custom_api_base_url=True)

    assert config.bearer_token == "file-token"
    assert config.api_base_url == "https://file.example"


def test_load_config_maps_missing_env_file_to_config_error(tmp_path) -> None:
    missing_file = tmp_path / "missing.env"

    with pytest.raises(ConfigError, match="Unable to read env file"):
        load_config(env_file=missing_file)


def test_load_config_rejects_non_https_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTKIT_X_COM_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("AGENTKIT_X_COM_API_BASE_URL", "http://api.x.com")

    with pytest.raises(ConfigError, match="https"):
        load_config()


def test_load_config_rejects_custom_base_url_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTKIT_X_COM_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("AGENTKIT_X_COM_API_BASE_URL", "https://example.test")

    with pytest.raises(ConfigError, match="api.x.com"):
        load_config()


def test_load_config_allows_custom_base_url_when_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTKIT_X_COM_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("AGENTKIT_X_COM_API_BASE_URL", "https://example.test")
    monkeypatch.setenv("AGENTKIT_X_COM_ALLOW_CUSTOM_API_BASE_URL", "1")

    config = load_config()

    assert config.api_base_url == "https://example.test"
