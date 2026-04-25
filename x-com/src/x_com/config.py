"""Configuration loading for x-com."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .errors import ConfigError

DEFAULT_API_BASE_URL = "https://api.x.com"
TOKEN_ENV_VAR = "AGENTKIT_X_COM_BEARER_TOKEN"
BASE_URL_ENV_VAR = "AGENTKIT_X_COM_API_BASE_URL"
ALLOW_CUSTOM_BASE_URL_ENV_VAR = "AGENTKIT_X_COM_ALLOW_CUSTOM_API_BASE_URL"


@dataclass(frozen=True)
class XComAuthConfig:
    bearer_token: str
    api_base_url: str = DEFAULT_API_BASE_URL
    allow_custom_api_base_url: bool = False


def load_config(
    env_file: str | Path | None = None,
    *,
    allow_custom_api_base_url: bool | None = None,
) -> XComAuthConfig:
    values = dict(os.environ)
    if env_file is not None:
        values.update(_read_env_file(Path(env_file)))

    token = values.get(TOKEN_ENV_VAR, "").strip()
    if not token:
        raise ConfigError(f"Missing required environment variable: {TOKEN_ENV_VAR}")

    base_url = values.get(BASE_URL_ENV_VAR, DEFAULT_API_BASE_URL).strip()
    if allow_custom_api_base_url is None:
        allow_custom_api_base_url = values.get(ALLOW_CUSTOM_BASE_URL_ENV_VAR) in {
            "1",
            "true",
            "TRUE",
            "yes",
            "YES",
        }
    _validate_api_base_url(base_url, allow_custom_api_base_url)
    return XComAuthConfig(
        bearer_token=token,
        api_base_url=base_url.rstrip("/") or DEFAULT_API_BASE_URL,
        allow_custom_api_base_url=allow_custom_api_base_url,
    )


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ConfigError(f"Unable to read env file: {path}") from error
    except UnicodeDecodeError as error:
        raise ConfigError(f"Env file must be UTF-8 encoded: {path}") from error

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = _unquote(value.strip())
    return values


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _validate_api_base_url(value: str, allow_custom: bool) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ConfigError(f"{BASE_URL_ENV_VAR} must use https.")
    if parsed.hostname != "api.x.com" and not allow_custom:
        raise ConfigError(
            f"{BASE_URL_ENV_VAR} must point to api.x.com unless "
            f"{ALLOW_CUSTOM_BASE_URL_ENV_VAR}=1 is set."
        )
