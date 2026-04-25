"""Data models and request normalization for x-com."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import re
from typing import Any, Literal

DEFAULT_TWEET_FIELDS = [
    "id",
    "text",
    "author_id",
    "created_at",
    "conversation_id",
    "context_annotations",
    "referenced_tweets",
    "in_reply_to_user_id",
    "attachments",
    "entities",
    "geo",
    "lang",
    "public_metrics",
    "possibly_sensitive",
    "reply_settings",
    "source",
    "edit_history_tweet_ids",
    "edit_controls",
    "note_tweet",
]

DEFAULT_EXPANSIONS = [
    "author_id",
    "in_reply_to_user_id",
    "referenced_tweets.id",
    "referenced_tweets.id.author_id",
    "attachments.media_keys",
    "attachments.poll_ids",
    "geo.place_id",
    "entities.mentions.username",
]

DEFAULT_USER_FIELDS = [
    "id",
    "name",
    "username",
    "created_at",
    "description",
    "entities",
    "location",
    "profile_image_url",
    "protected",
    "public_metrics",
    "url",
    "verified",
    "verified_type",
    "withheld",
]

DEFAULT_MEDIA_FIELDS = [
    "media_key",
    "type",
    "url",
    "preview_image_url",
    "duration_ms",
    "height",
    "width",
    "alt_text",
    "public_metrics",
    "variants",
]

DEFAULT_POLL_FIELDS = [
    "id",
    "options",
    "duration_minutes",
    "end_datetime",
    "voting_status",
]

DEFAULT_PLACE_FIELDS = [
    "id",
    "full_name",
    "country",
    "country_code",
    "geo",
    "name",
    "place_type",
]

FULL_TWEET_FIELDS = [
    *DEFAULT_TWEET_FIELDS,
    "article",
    "card_uri",
    "community_id",
    "display_text_range",
    "media_metadata",
    "non_public_metrics",
    "organic_metrics",
    "promoted_metrics",
    "scopes",
    "suggested_source_links",
    "suggested_source_links_with_counts",
    "withheld",
]

MINIMAL_TWEET_FIELDS = [
    "id",
    "text",
    "author_id",
    "created_at",
    "conversation_id",
    "public_metrics",
    "referenced_tweets",
]

MINIMAL_EXPANSIONS = ["author_id", "referenced_tweets.id"]

ALLOWED_EXCLUDE_VALUES = {"retweets", "replies"}
ALLOWED_FIELD_PROFILES = {"minimal", "default", "full"}
USER_ID_PATTERN = re.compile(r"^[0-9]{1,19}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,15}$")


@dataclass(frozen=True)
class FieldProfile:
    tweet_fields: list[str]
    expansions: list[str]
    user_fields: list[str]
    media_fields: list[str]
    poll_fields: list[str]
    place_fields: list[str]


@dataclass(frozen=True)
class FetchWindow:
    mode: Literal["latest", "time_range"]
    latest_count: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass
class FetchUserTweetsRequest:
    usernames: list[str] = field(default_factory=list)
    user_ids: list[str] = field(default_factory=list)
    latest_count: int | None = None
    max_pages_per_user: int = 1
    start_time: datetime | None = None
    end_time: datetime | None = None
    since_id: str | None = None
    until_id: str | None = None
    exclude: list[Literal["retweets", "replies"]] = field(default_factory=list)
    include_context: bool = True
    fields_profile: Literal["default", "minimal", "full"] = "default"

    def __post_init__(self) -> None:
        cleaned_usernames = [_clean_username(value) for value in self.usernames]
        self.usernames = [value for value in cleaned_usernames if value]
        self.user_ids = [
            str(value).strip() for value in self.user_ids if str(value).strip()
        ]
        self.exclude = [value for value in self.exclude if value]
        self.start_time = _as_utc(self.start_time)
        self.end_time = _as_utc(self.end_time)

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.usernames and not self.user_ids:
            errors.append("At least one of usernames or user_ids is required.")
        invalid_user_ids = [
            user_id
            for user_id in self.user_ids
            if not USER_ID_PATTERN.fullmatch(user_id)
        ]
        if invalid_user_ids:
            errors.append("user_ids must be numeric strings with 1 to 19 digits.")
        invalid_usernames = [
            username
            for username in self.usernames
            if not USERNAME_PATTERN.fullmatch(username)
        ]
        if invalid_usernames:
            errors.append(
                "usernames must contain only letters, numbers, and underscores "
                "with length 1 to 15."
            )
        if self.latest_count is not None and self.latest_count <= 0:
            errors.append("latest_count must be greater than zero.")
        if self.max_pages_per_user <= 0:
            errors.append("max_pages_per_user must be greater than zero.")
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            errors.append("start_time must be earlier than end_time.")
        invalid_exclude = sorted(set(self.exclude) - ALLOWED_EXCLUDE_VALUES)
        if invalid_exclude:
            errors.append(
                "exclude contains unsupported values: " + ", ".join(invalid_exclude)
            )
        if self.fields_profile not in ALLOWED_FIELD_PROFILES:
            errors.append(
                "fields_profile must be one of: "
                + ", ".join(sorted(ALLOWED_FIELD_PROFILES))
            )
        return errors


@dataclass
class XComTweetBundle:
    requested_user: dict[str, Any]
    tweets: list[dict[str, Any]] = field(default_factory=list)
    includes: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_user": self.requested_user,
            "tweets": self.tweets,
            "includes": self.includes,
            "meta": self.meta,
            "errors": self.errors,
        }


@dataclass
class FetchUserTweetsResult:
    users: list[XComTweetBundle] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "users": [bundle.to_dict() for bundle in self.users],
            "errors": self.errors,
        }


def resolve_fetch_window(request: FetchUserTweetsRequest) -> FetchWindow:
    if request.start_time is not None or request.end_time is not None:
        return FetchWindow(
            mode="time_range",
            start_time=request.start_time,
            end_time=request.end_time,
        )
    return FetchWindow(mode="latest", latest_count=request.latest_count or 10)


def get_field_profile(profile: str) -> FieldProfile:
    if profile == "minimal":
        return FieldProfile(
            tweet_fields=MINIMAL_TWEET_FIELDS,
            expansions=MINIMAL_EXPANSIONS,
            user_fields=["id", "name", "username", "verified"],
            media_fields=[],
            poll_fields=[],
            place_fields=[],
        )
    if profile == "full":
        return FieldProfile(
            tweet_fields=FULL_TWEET_FIELDS,
            expansions=DEFAULT_EXPANSIONS,
            user_fields=DEFAULT_USER_FIELDS,
            media_fields=DEFAULT_MEDIA_FIELDS,
            poll_fields=DEFAULT_POLL_FIELDS,
            place_fields=DEFAULT_PLACE_FIELDS,
        )
    return FieldProfile(
        tweet_fields=DEFAULT_TWEET_FIELDS,
        expansions=DEFAULT_EXPANSIONS,
        user_fields=DEFAULT_USER_FIELDS,
        media_fields=DEFAULT_MEDIA_FIELDS,
        poll_fields=DEFAULT_POLL_FIELDS,
        place_fields=DEFAULT_PLACE_FIELDS,
    )


def _clean_username(value: str) -> str:
    return value.strip().removeprefix("@")


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
