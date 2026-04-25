"""Error types for the x-com tool."""

from __future__ import annotations


class XComError(Exception):
    """Base error for x-com failures."""


class ConfigError(XComError):
    """Raised when required configuration is missing or invalid."""


class XComApiError(XComError):
    """Raised when X API returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> dict:
        return {
            "message": str(self),
            "status_code": self.status_code,
            "payload": self.payload,
        }
