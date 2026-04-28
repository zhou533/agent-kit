from __future__ import annotations

from datetime import UTC, datetime

from x_com.models import (
    FetchUsageRequest,
    FetchUsageResult,
    FetchUserTweetsRequest,
    get_field_profile,
    resolve_fetch_window,
)


def test_fetch_window_defaults_to_latest_10() -> None:
    request = FetchUserTweetsRequest(usernames=["OpenAI"])

    window = resolve_fetch_window(request)

    assert window.mode == "latest"
    assert window.latest_count == 10


def test_fetch_window_uses_explicit_latest_count() -> None:
    request = FetchUserTweetsRequest(usernames=["OpenAI"], latest_count=25)

    window = resolve_fetch_window(request)

    assert window.mode == "latest"
    assert window.latest_count == 25


def test_fetch_window_prefers_time_range_over_latest_count() -> None:
    start_time = datetime(2026, 1, 1, tzinfo=UTC)
    request = FetchUserTweetsRequest(
        usernames=["OpenAI"],
        latest_count=50,
        start_time=start_time,
    )

    window = resolve_fetch_window(request)

    assert window.mode == "time_range"
    assert window.latest_count is None
    assert window.start_time == start_time


def test_request_requires_username_or_user_id() -> None:
    request = FetchUserTweetsRequest()

    errors = request.validation_errors()

    assert "usernames or user_ids" in errors[0]


def test_request_rejects_invalid_exclude_value() -> None:
    request = FetchUserTweetsRequest(usernames=["OpenAI"], exclude=["likes"])

    errors = request.validation_errors()

    assert "exclude" in errors[0]


def test_request_excludes_retweets_and_replies_by_default() -> None:
    request = FetchUserTweetsRequest(usernames=["OpenAI"])

    assert request.exclude == ["retweets", "replies"]


def test_request_can_include_retweets_or_replies() -> None:
    request = FetchUserTweetsRequest(
        usernames=["OpenAI"],
        include_retweets=True,
        include_replies=True,
    )

    assert request.exclude == []


def test_request_rejects_conflicting_exclude_and_include() -> None:
    request = FetchUserTweetsRequest(
        usernames=["OpenAI"],
        exclude=["retweets"],
        include_retweets=True,
    )

    errors = request.validation_errors()

    assert "include_retweets" in errors[0]


def test_request_rejects_invalid_fields_profile() -> None:
    request = FetchUserTweetsRequest(usernames=["OpenAI"], fields_profile="tiny")

    errors = request.validation_errors()

    assert "fields_profile" in errors[0]


def test_request_rejects_invalid_user_id() -> None:
    request = FetchUserTweetsRequest(user_ids=["123/456"])

    errors = request.validation_errors()

    assert "user_ids" in errors[0]


def test_request_rejects_empty_username_after_cleanup() -> None:
    request = FetchUserTweetsRequest(usernames=["@"])

    errors = request.validation_errors()

    assert "usernames or user_ids" in errors[0]


def test_request_rejects_invalid_username_characters() -> None:
    request = FetchUserTweetsRequest(usernames=["bad-name"])

    errors = request.validation_errors()

    assert "usernames" in errors[0]


def test_request_rejects_reversed_time_range() -> None:
    request = FetchUserTweetsRequest(
        user_ids=["123"],
        start_time=datetime(2026, 1, 2, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, tzinfo=UTC),
    )

    errors = request.validation_errors()

    assert "start_time" in errors[0]


def test_request_normalizes_naive_and_aware_time_range_before_validation() -> None:
    request = FetchUserTweetsRequest(
        user_ids=["123"],
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert request.validation_errors() == []
    assert request.start_time.tzinfo == UTC
    assert request.end_time.tzinfo == UTC


def test_field_profiles_change_requested_context_fields() -> None:
    minimal = get_field_profile("minimal")
    default = get_field_profile("default")
    full = get_field_profile("full")

    assert len(minimal.tweet_fields) < len(default.tweet_fields)
    assert len(default.tweet_fields) < len(full.tweet_fields)
    assert "context_annotations" in default.tweet_fields
    assert "non_public_metrics" in full.tweet_fields


def test_usage_request_defaults_to_7_days() -> None:
    request = FetchUsageRequest()

    assert request.days == 7
    assert request.usage_fields is None
    assert request.validation_errors() == []


def test_usage_request_accepts_boundary_days() -> None:
    assert FetchUsageRequest(days=1).validation_errors() == []
    assert FetchUsageRequest(days=90).validation_errors() == []


def test_usage_request_rejects_days_outside_supported_range() -> None:
    assert "days" in FetchUsageRequest(days=0).validation_errors()[0]
    assert "days" in FetchUsageRequest(days=91).validation_errors()[0]


def test_usage_request_rejects_unknown_usage_fields() -> None:
    request = FetchUsageRequest(usage_fields=["project_usage", "unknown"])

    errors = request.validation_errors()

    assert "usage_fields" in errors[0]
    assert "unknown" in errors[0]


def test_usage_result_serializes_stable_shape() -> None:
    result = FetchUsageResult(
        data={"project_usage": 12},
        summary={"remaining_project_usage": 88},
        meta={"endpoint": "/2/usage/tweets"},
    )

    assert result.to_dict() == {
        "data": {"project_usage": 12},
        "summary": {"remaining_project_usage": 88},
        "meta": {"endpoint": "/2/usage/tweets"},
        "errors": [],
    }
