"""X API client for x-com."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from .errors import XComApiError
from .models import (
    DEFAULT_USER_FIELDS,
    get_field_profile,
)


class Transport(Protocol):
    def get_json(
        self,
        path: str,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> dict[str, Any]: ...


class UrllibTransport:
    def __init__(
        self, base_url: str, *, allow_custom_api_base_url: bool = False
    ) -> None:
        self.base_url = base_url.rstrip("/")
        _validate_api_base_url(self.base_url, allow_custom_api_base_url)

    def get_json(
        self,
        path: str,
        params: dict[str, str],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        query = urlencode(params)
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
                return json.loads(raw)
        except HTTPError as error:
            payload = _read_error_payload(error)
            raise XComApiError(
                _extract_error_message(payload)
                or f"X API request failed: {error.code}",
                status_code=error.code,
                payload=payload,
            ) from error
        except (URLError, TimeoutError) as error:
            raise XComApiError(f"X API network error: {error}") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise XComApiError(f"Invalid JSON response from X API: {error}") from error


class XComClient:
    def __init__(
        self,
        *,
        bearer_token: str,
        api_base_url: str = "https://api.x.com",
        transport: Transport | None = None,
        allow_custom_api_base_url: bool = False,
    ) -> None:
        self.bearer_token = bearer_token
        self.transport = transport or UrllibTransport(
            api_base_url,
            allow_custom_api_base_url=allow_custom_api_base_url,
        )

    def lookup_users(self, usernames: list[str]) -> dict[str, Any]:
        return self._get(
            "/2/users/by",
            {
                "usernames": ",".join(usernames),
                "user.fields": ",".join(DEFAULT_USER_FIELDS),
            },
        )

    def get_usage(
        self,
        *,
        days: int = 7,
        usage_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        params = {"days": str(days)}
        if usage_fields:
            params["usage.fields"] = ",".join(usage_fields)
        return self._get("/2/usage/tweets", params)

    def fetch_user_tweets(
        self,
        *,
        user_id: str,
        max_results: int,
        pagination_token: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        since_id: str | None = None,
        until_id: str | None = None,
        exclude: list[str] | None = None,
        include_context: bool = True,
        fields_profile: str = "default",
    ) -> dict[str, Any]:
        params: dict[str, str] = {"max_results": str(max_results)}
        _set_optional(params, "pagination_token", pagination_token)
        _set_optional(params, "start_time", _format_datetime(start_time))
        _set_optional(params, "end_time", _format_datetime(end_time))
        _set_optional(params, "since_id", since_id)
        _set_optional(params, "until_id", until_id)
        if exclude:
            params["exclude"] = ",".join(exclude)
        if include_context:
            profile = get_field_profile(fields_profile)
            params.update(
                {
                    "tweet.fields": ",".join(profile.tweet_fields),
                    "expansions": ",".join(profile.expansions),
                    "user.fields": ",".join(profile.user_fields),
                }
            )
            _set_optional(params, "media.fields", ",".join(profile.media_fields))
            _set_optional(params, "poll.fields", ",".join(profile.poll_fields))
            _set_optional(params, "place.fields", ",".join(profile.place_fields))
        escaped_user_id = quote(user_id, safe="")
        return self._get(f"/2/users/{escaped_user_id}/tweets", params)

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        return self.transport.get_json(path, params, self._headers())

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Accept": "application/json",
        }


def _set_optional(params: dict[str, str], key: str, value: str | None) -> None:
    if value:
        params[key] = value


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _read_error_payload(error: HTTPError) -> dict[str, Any]:
    raw = error.read().decode("utf-8", errors="replace")
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return payload if isinstance(payload, dict) else {"raw": payload}


def _extract_error_message(payload: dict[str, Any]) -> str | None:
    if "detail" in payload:
        return str(payload["detail"])
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict):
            return str(first.get("detail") or first.get("title") or first)
    return None


def _validate_api_base_url(value: str, allow_custom: bool) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise XComApiError("X API base URL must use https.")
    if parsed.hostname != "api.x.com" and not allow_custom:
        raise XComApiError(
            "X API base URL must point to api.x.com unless custom hosts are "
            "explicitly allowed."
        )
