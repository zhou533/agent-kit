from __future__ import annotations

import json

import pytest

from x_com.cli import build_request, build_usage_request, main
from x_com.errors import XComApiError


def test_build_request_parses_latest_mode() -> None:
    request = build_request(
        [
            "tweets",
            "--usernames",
            "OpenAI,XDevelopers",
            "--latest",
            "25",
            "--exclude",
            "retweets,replies",
            "--json",
        ]
    )

    assert request.usernames == ["OpenAI", "XDevelopers"]
    assert request.latest_count == 25
    assert request.exclude == ["retweets", "replies"]


def test_build_request_excludes_retweets_and_replies_by_default() -> None:
    request = build_request(["tweets", "--username", "OpenAI"])

    assert request.exclude == ["retweets", "replies"]


def test_build_request_can_include_retweets_and_replies() -> None:
    request = build_request(
        [
            "tweets",
            "--username",
            "OpenAI",
            "--include-retweets",
            "--include-replies",
        ]
    )

    assert request.exclude == []


def test_build_request_parses_time_mode_and_user_id() -> None:
    request = build_request(
        [
            "tweets",
            "--user-id",
            "2244994945",
            "--latest",
            "50",
            "--start-time",
            "2026-01-01T00:00:00Z",
            "--json",
        ]
    )

    assert request.user_ids == ["2244994945"]
    assert request.latest_count == 50
    assert request.start_time is not None


def test_main_outputs_json_with_injected_service(capsys) -> None:
    class FakeResult:
        def to_dict(self):
            return {"users": [], "errors": []}

    class FakeService:
        def fetch_user_tweets(self, request, *, fail_fast=False):
            assert request.usernames == ["OpenAI"]
            assert fail_fast is False
            return FakeResult()

    exit_code = main(
        ["tweets", "--username", "OpenAI", "--json"],
        service_factory=lambda: FakeService(),
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"users": [], "errors": []}


def test_build_usage_request_parses_days_and_fields() -> None:
    request = build_usage_request(
        [
            "usage",
            "--days",
            "30",
            "--fields",
            "project_usage,project_cap",
            "--json",
        ]
    )

    assert request.days == 30
    assert request.usage_fields == ["project_usage", "project_cap"]


def test_main_outputs_usage_json_with_injected_service(capsys) -> None:
    class FakeResult:
        def to_dict(self):
            return {
                "data": {"project_usage": 10},
                "summary": {"project_usage": 10},
                "meta": {"endpoint": "/2/usage/tweets"},
                "errors": [],
            }

    class FakeService:
        def fetch_usage(self, request):
            assert request.days == 7
            assert request.usage_fields is None
            return FakeResult()

    exit_code = main(["usage", "--json"], service_factory=lambda: FakeService())

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["data"] == {"project_usage": 10}


def test_main_rejects_invalid_usage_days_before_loading_config(capsys) -> None:
    exit_code = main(["usage", "--days", "91", "--json"], service_factory=lambda: None)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "days" in captured.err
    assert captured.out == ""


def test_build_request_rejects_invalid_datetime() -> None:
    with pytest.raises(SystemExit):
        build_request(["tweets", "--username", "OpenAI", "--start-time", "invalid"])


def test_build_request_normalizes_mixed_datetime_awareness() -> None:
    request = build_request(
        [
            "tweets",
            "--user-id",
            "123",
            "--start-time",
            "2026-01-01T00:00:00",
            "--end-time",
            "2026-01-02T00:00:00Z",
        ]
    )

    assert request.validation_errors() == []


def test_main_maps_missing_config_to_stderr(
    capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AGENTKIT_X_COM_BEARER_TOKEN", raising=False)

    exit_code = main(["tweets", "--username", "OpenAI", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "AGENTKIT_X_COM_BEARER_TOKEN" in captured.err
    assert captured.out == ""


def test_main_maps_missing_env_file_to_stderr(capsys) -> None:
    exit_code = main(["--env-file", "missing.env", "tweets", "--user-id", "123"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Unable to read env file" in captured.err
    assert captured.out == ""


def test_main_maps_api_error_to_stderr(capsys) -> None:
    class FakeService:
        def fetch_user_tweets(self, request, *, fail_fast=False):
            raise XComApiError("rate limited", status_code=429)

    exit_code = main(
        ["tweets", "--username", "OpenAI", "--json"],
        service_factory=lambda: FakeService(),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "rate limited" in captured.err
