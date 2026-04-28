"""Command line interface for x-com."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from datetime import datetime

from .client import XComClient
from .config import load_config
from .errors import ConfigError, XComApiError
from .models import FetchUsageRequest, FetchUserTweetsRequest
from .service import XComService


def build_request(argv: Sequence[str]) -> FetchUserTweetsRequest:
    parser = _build_parser()
    args = parser.parse_args(list(argv))
    if args.command != "tweets":
        parser.error("Only the 'tweets' command is supported.")

    usernames = list(args.username or [])
    usernames.extend(_split_csv(args.usernames))
    user_ids = list(args.user_id or [])

    exclude: list[str] = []
    for value in args.exclude or []:
        exclude.extend(_split_csv(value))

    return FetchUserTweetsRequest(
        usernames=usernames,
        user_ids=user_ids,
        latest_count=args.latest,
        max_pages_per_user=args.max_pages,
        start_time=args.start_time,
        end_time=args.end_time,
        since_id=args.since_id,
        until_id=args.until_id,
        exclude=exclude or None,
        include_retweets=args.include_retweets,
        include_replies=args.include_replies,
        fields_profile=args.fields_profile,
    )


def build_usage_request(argv: Sequence[str]) -> FetchUsageRequest:
    parser = _build_parser()
    args = parser.parse_args(list(argv))
    if args.command != "usage":
        parser.error("Only the 'usage' command is supported.")

    usage_fields: list[str] = []
    for value in args.fields or []:
        usage_fields.extend(_split_csv(value))

    return FetchUsageRequest(
        days=args.days,
        usage_fields=usage_fields or None,
        include_summary=not args.no_summary,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    service_factory: Callable[[], XComService] | None = None,
) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "usage":
        request = build_usage_request(argv)
    else:
        request = build_request(argv)
    errors = request.validation_errors()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2

    try:
        service = (
            service_factory() if service_factory else _default_service(args.env_file)
        )
        if args.command == "usage":
            result = service.fetch_usage(request)
        else:
            result = service.fetch_user_tweets(request, fail_fast=args.fail_fast)
    except (ConfigError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except XComApiError as error:
        print(str(error), file=sys.stderr)
        return 1
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _default_service(env_file: str | None) -> XComService:
    config = load_config(env_file=env_file)
    client = XComClient(
        bearer_token=config.bearer_token,
        api_base_url=config.api_base_url,
        allow_custom_api_base_url=config.allow_custom_api_base_url,
    )
    return XComService(client)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="x-com")
    parser.add_argument(
        "--env-file", help="Load local environment variables from a file."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    tweets = subparsers.add_parser("tweets", help="Fetch posts for one or more users.")
    tweets.add_argument("--username", action="append", help="Username to fetch.")
    tweets.add_argument("--usernames", help="Comma-separated usernames to fetch.")
    tweets.add_argument("--user-id", action="append", help="User ID to fetch.")
    tweets.add_argument("--latest", type=int, help="Fetch the latest N posts per user.")
    tweets.add_argument("--max-pages", type=int, default=1)
    tweets.add_argument("--start-time", type=_parse_datetime_arg)
    tweets.add_argument("--end-time", type=_parse_datetime_arg)
    tweets.add_argument("--since-id")
    tweets.add_argument("--until-id")
    tweets.add_argument("--exclude", action="append")
    tweets.add_argument(
        "--include-retweets",
        action="store_true",
        help="Include retweets instead of excluding them by default.",
    )
    tweets.add_argument(
        "--include-replies",
        action="store_true",
        help="Include replies instead of excluding them by default.",
    )
    tweets.add_argument(
        "--fields-profile",
        choices=["minimal", "default", "full"],
        default="default",
    )
    tweets.add_argument("--json", action="store_true")
    tweets.add_argument("--fail-fast", action="store_true")
    usage = subparsers.add_parser("usage", help="Fetch X API post usage.")
    usage.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to include, from 1 to 90.",
    )
    usage.add_argument(
        "--fields",
        action="append",
        help="Comma-separated usage.fields values to request.",
    )
    usage.add_argument(
        "--no-summary",
        action="store_true",
        help="Return raw usage data without a computed summary.",
    )
    usage.add_argument("--json", action="store_true")
    return parser


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_datetime_arg(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"Invalid datetime: {value}") from error


if __name__ == "__main__":
    raise SystemExit(main())
