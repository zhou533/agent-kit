"""Service layer for x-com."""

from __future__ import annotations

from typing import Any

from .errors import XComApiError
from .models import (
    FetchUserTweetsRequest,
    FetchUserTweetsResult,
    XComTweetBundle,
    resolve_fetch_window,
)

X_API_MIN_PAGE_SIZE = 5
X_API_MAX_PAGE_SIZE = 100


class XComService:
    def __init__(self, client) -> None:
        self.client = client

    def fetch_user_tweets(
        self,
        request: FetchUserTweetsRequest,
        *,
        fail_fast: bool = False,
    ) -> FetchUserTweetsResult:
        errors = request.validation_errors()
        if errors:
            raise ValueError("; ".join(errors))

        resolved_users, lookup_errors = self._resolve_users(request)
        window = resolve_fetch_window(request)
        result = FetchUserTweetsResult(errors=lookup_errors)

        for user in resolved_users:
            try:
                bundle = self._fetch_for_user(user, request, window)
                result.users.append(bundle)
            except XComApiError as error:
                error_payload = error.to_dict()
                if fail_fast:
                    raise
                result.users.append(
                    XComTweetBundle(
                        requested_user=user,
                        tweets=[],
                        includes={},
                        meta={"selection_mode": window.mode},
                        errors=[error_payload],
                    )
                )
        return result

    def _resolve_users(
        self, request: FetchUserTweetsRequest
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        users = [{"id": user_id} for user_id in request.user_ids]
        errors: list[dict[str, Any]] = []
        if request.usernames:
            payload = self.client.lookup_users(request.usernames)
            users.extend(payload.get("data") or [])
            for error in payload.get("errors") or []:
                if isinstance(error, dict):
                    errors.append({"stage": "lookup_users", **error})
                else:
                    errors.append({"stage": "lookup_users", "message": str(error)})
        return users, errors

    def _fetch_for_user(
        self,
        user: dict[str, Any],
        request: FetchUserTweetsRequest,
        window,
    ) -> XComTweetBundle:
        tweets: list[dict[str, Any]] = []
        includes: dict[str, Any] = {}
        meta: dict[str, Any] = {"selection_mode": window.mode}
        next_token: str | None = None

        for _ in range(request.max_pages_per_user):
            max_results = _page_size(window, len(tweets))
            if max_results <= 0:
                break
            payload = self.client.fetch_user_tweets(
                user_id=user["id"],
                max_results=max_results,
                pagination_token=next_token,
                start_time=window.start_time,
                end_time=window.end_time,
                since_id=request.since_id,
                until_id=request.until_id,
                exclude=request.exclude,
                include_context=request.include_context,
                fields_profile=request.fields_profile,
            )
            tweets.extend(payload.get("data") or [])
            includes = _merge_includes(includes, payload.get("includes") or {})
            meta.update(payload.get("meta") or {})
            next_token = (payload.get("meta") or {}).get("next_token")
            if not next_token or _latest_target_reached(window, len(tweets)):
                break

        if window.mode == "latest" and window.latest_count is not None:
            tweets = tweets[: window.latest_count]
        meta["selection_mode"] = window.mode
        return XComTweetBundle(
            requested_user=user,
            tweets=tweets,
            includes=includes,
            meta=meta,
            errors=[],
        )


def _page_size(window, collected_count: int) -> int:
    if window.mode == "time_range":
        return X_API_MAX_PAGE_SIZE
    remaining = (window.latest_count or 10) - collected_count
    if remaining <= 0:
        return 0
    return max(X_API_MIN_PAGE_SIZE, min(X_API_MAX_PAGE_SIZE, remaining))


def _latest_target_reached(window, collected_count: int) -> bool:
    return window.mode == "latest" and collected_count >= (window.latest_count or 10)


def _merge_includes(
    current: dict[str, Any],
    next_includes: dict[str, Any],
) -> dict[str, Any]:
    merged = {
        key: list(value) for key, value in current.items() if isinstance(value, list)
    }
    for key, value in next_includes.items():
        if isinstance(value, list):
            merged.setdefault(key, []).extend(value)
        else:
            merged[key] = value
    return merged
