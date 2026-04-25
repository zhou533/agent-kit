from __future__ import annotations

from datetime import UTC, datetime

from x_com.models import FetchUserTweetsRequest
from x_com.service import XComService


class FakeClient:
    def __init__(self) -> None:
        self.lookup_calls = []
        self.tweet_calls = []

    def lookup_users(self, usernames):
        self.lookup_calls.append(list(usernames))
        return {
            "data": [
                {"id": "1", "username": "OpenAI", "name": "OpenAI"},
                {"id": "2", "username": "XDevelopers", "name": "X Developers"},
            ],
            "errors": [],
        }

    def fetch_user_tweets(self, **kwargs):
        self.tweet_calls.append(kwargs)
        return {
            "data": [
                {
                    "id": str(index),
                    "text": f"post {index}",
                    "author_id": kwargs["user_id"],
                }
                for index in range(1, 6)
            ],
            "includes": {"users": [{"id": kwargs["user_id"]}]},
            "meta": {"result_count": 5},
        }


def test_service_fetches_latest_posts_by_username_and_slices_to_requested_count() -> (
    None
):
    client = FakeClient()
    service = XComService(client)

    result = service.fetch_user_tweets(
        FetchUserTweetsRequest(usernames=["OpenAI"], latest_count=3)
    )

    assert client.lookup_calls == [["OpenAI"]]
    assert client.tweet_calls[0]["user_id"] == "1"
    assert client.tweet_calls[0]["max_results"] == 5
    assert len(result.users[0].tweets) == 3
    assert result.users[0].meta["selection_mode"] == "latest"


def test_service_fetches_each_resolved_user() -> None:
    client = FakeClient()
    service = XComService(client)

    result = service.fetch_user_tweets(
        FetchUserTweetsRequest(usernames=["OpenAI", "XDevelopers"], latest_count=2)
    )

    assert [call["user_id"] for call in client.tweet_calls] == ["1", "2"]
    assert [bundle.requested_user["username"] for bundle in result.users] == [
        "OpenAI",
        "XDevelopers",
    ]


def test_service_prefers_time_range_over_latest_count() -> None:
    client = FakeClient()
    service = XComService(client)
    start_time = datetime(2026, 1, 1, tzinfo=UTC)

    result = service.fetch_user_tweets(
        FetchUserTweetsRequest(
            user_ids=["1"],
            latest_count=50,
            start_time=start_time,
        )
    )

    assert client.tweet_calls[0]["start_time"] == start_time
    assert client.tweet_calls[0]["max_results"] == 100
    assert result.users[0].meta["selection_mode"] == "time_range"


def test_service_preserves_lookup_errors() -> None:
    class LookupErrorClient(FakeClient):
        def lookup_users(self, usernames):
            return {
                "data": [{"id": "1", "username": "OpenAI", "name": "OpenAI"}],
                "errors": [
                    {
                        "resource_id": "MissingUser",
                        "title": "Not Found Error",
                        "detail": "Could not find user.",
                    }
                ],
            }

    service = XComService(LookupErrorClient())

    result = service.fetch_user_tweets(
        FetchUserTweetsRequest(usernames=["OpenAI", "MissingUser"], latest_count=1)
    )

    assert result.errors[0]["stage"] == "lookup_users"
    assert result.errors[0]["resource_id"] == "MissingUser"
    assert len(result.users) == 1


def test_service_passes_fields_profile_to_client() -> None:
    client = FakeClient()
    service = XComService(client)

    service.fetch_user_tweets(
        FetchUserTweetsRequest(user_ids=["1"], latest_count=1, fields_profile="minimal")
    )

    assert client.tweet_calls[0]["fields_profile"] == "minimal"
