"""MCP adapter for x-com."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from .client import XComClient
from .config import load_config
from .errors import ConfigError, XComApiError
from .models import FetchUsageRequest, FetchUserTweetsRequest
from .service import XComService


def register_tools(
    mcp, *, service_factory: Callable[[], XComService] | None = None
) -> None:
    @mcp.tool(
        name="x_com_fetch_user_tweets",
        description="Fetch X.com posts for one or more users with contextual includes.",
    )
    def fetch_user_tweets(
        usernames: list[str] | None = None,
        user_ids: list[str] | None = None,
        latest_count: int | None = None,
        max_pages_per_user: int = 1,
        start_time: str | None = None,
        end_time: str | None = None,
        since_id: str | None = None,
        until_id: str | None = None,
        exclude: list[str] | None = None,
        include_retweets: bool = False,
        include_replies: bool = False,
        include_context: bool = True,
        fields_profile: str = "default",
    ) -> dict:
        try:
            parsed_start_time = _parse_datetime(start_time, "start_time")
            parsed_end_time = _parse_datetime(end_time, "end_time")
        except ValueError as error:
            return _error_result("validation_error", str(error))
        normalized_latest_count = latest_count
        if (
            parsed_start_time is None
            and parsed_end_time is None
            and normalized_latest_count is None
        ):
            normalized_latest_count = 10
        request = FetchUserTweetsRequest(
            usernames=usernames or [],
            user_ids=user_ids or [],
            latest_count=normalized_latest_count,
            max_pages_per_user=max_pages_per_user,
            start_time=parsed_start_time,
            end_time=parsed_end_time,
            since_id=since_id,
            until_id=until_id,
            exclude=exclude,
            include_retweets=include_retweets,
            include_replies=include_replies,
            include_context=include_context,
            fields_profile=fields_profile,  # type: ignore[arg-type]
        )
        errors = request.validation_errors()
        if errors:
            return _error_result("validation_error", "; ".join(errors))
        try:
            service = service_factory() if service_factory else _default_service()
            return service.fetch_user_tweets(request).to_dict()
        except ValueError as error:
            return _error_result("validation_error", str(error))
        except ConfigError as error:
            return _error_result("configuration_error", str(error))
        except XComApiError as error:
            return _error_result("x_api_error", str(error), error.to_dict())

    @mcp.tool(
        name="x_com_get_usage",
        description="Fetch X API post usage for the configured project/account.",
    )
    def get_usage(
        days: int = 7,
        usage_fields: list[str] | None = None,
        include_summary: bool = True,
    ) -> dict:
        request = FetchUsageRequest(
            days=days,
            usage_fields=usage_fields,
            include_summary=include_summary,
        )
        errors = request.validation_errors()
        if errors:
            return _usage_error_result("validation_error", "; ".join(errors))
        try:
            service = service_factory() if service_factory else _default_service()
            return service.fetch_usage(request).to_dict()
        except ValueError as error:
            return _usage_error_result("validation_error", str(error))
        except ConfigError as error:
            return _usage_error_result("configuration_error", str(error))
        except XComApiError as error:
            return _usage_error_result("x_api_error", str(error), error.to_dict())


def create_mcp_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("agentkit-x-com", json_response=True)
    register_tools(mcp)
    return mcp


def main() -> None:
    create_mcp_server().run()


def _default_service() -> XComService:
    config = load_config()
    return XComService(
        XComClient(
            bearer_token=config.bearer_token,
            api_base_url=config.api_base_url,
            allow_custom_api_base_url=config.allow_custom_api_base_url,
        )
    )


def _parse_datetime(value: str | None, field_name: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field_name} must be an ISO 8601 datetime.") from error


def _error_result(error_type: str, message: str, payload: dict | None = None) -> dict:
    error = {"type": error_type, "message": message}
    if payload:
        error["payload"] = payload
    return {"users": [], "errors": [error]}


def _usage_error_result(
    error_type: str, message: str, payload: dict | None = None
) -> dict:
    error = {"type": error_type, "message": message}
    if payload:
        error["payload"] = payload
    return {"data": {}, "summary": {}, "meta": {}, "errors": [error]}


if __name__ == "__main__":
    main()
