from __future__ import annotations

import pytest
from urllib.error import URLError

from x_com.client import XComClient
import x_com.client as client_module
from x_com.errors import XComApiError
from x_com.models import DEFAULT_EXPANSIONS, DEFAULT_TWEET_FIELDS


class FakeTransport:
    def __init__(self) -> None:
        self.calls = []

    def get_json(self, path, params, headers):
        self.calls.append({"path": path, "params": params, "headers": headers})
        if path == "/2/users/by":
            return {"data": [{"id": "1", "username": "OpenAI", "name": "OpenAI"}]}
        return {"data": [{"id": "10", "text": "hello", "author_id": "1"}]}


def test_lookup_users_calls_batch_username_endpoint() -> None:
    transport = FakeTransport()
    client = XComClient(bearer_token="secret", transport=transport)

    payload = client.lookup_users(["OpenAI", "XDevelopers"])

    assert payload["data"][0]["id"] == "1"
    assert transport.calls[0]["path"] == "/2/users/by"
    assert transport.calls[0]["params"]["usernames"] == "OpenAI,XDevelopers"
    assert transport.calls[0]["headers"]["Authorization"] == "Bearer secret"


def test_fetch_user_tweets_requests_context_fields() -> None:
    transport = FakeTransport()
    client = XComClient(bearer_token="secret", transport=transport)

    client.fetch_user_tweets(user_id="1", max_results=10)

    params = transport.calls[0]["params"]
    assert transport.calls[0]["path"] == "/2/users/1/tweets"
    assert set(DEFAULT_TWEET_FIELDS).issubset(set(params["tweet.fields"].split(",")))
    assert set(DEFAULT_EXPANSIONS).issubset(set(params["expansions"].split(",")))
    assert "user.fields" in params
    assert "media.fields" in params
    assert "poll.fields" in params


def test_fetch_user_tweets_sends_exclude_parameter() -> None:
    transport = FakeTransport()
    client = XComClient(bearer_token="secret", transport=transport)

    client.fetch_user_tweets(
        user_id="1",
        max_results=10,
        exclude=["retweets", "replies"],
    )

    assert transport.calls[0]["params"]["exclude"] == "retweets,replies"


def test_fetch_user_tweets_escapes_user_id_path_segment() -> None:
    transport = FakeTransport()
    client = XComClient(bearer_token="secret", transport=transport)

    client.fetch_user_tweets(user_id="1/2", max_results=10)

    assert transport.calls[0]["path"] == "/2/users/1%2F2/tweets"


def test_fetch_user_tweets_applies_fields_profile() -> None:
    transport = FakeTransport()
    client = XComClient(bearer_token="secret", transport=transport)

    client.fetch_user_tweets(user_id="1", max_results=10, fields_profile="minimal")

    params = transport.calls[0]["params"]
    assert "context_annotations" not in params["tweet.fields"].split(",")
    assert "tweet.fields" in params
    assert "expansions" in params


def test_transport_wraps_network_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise URLError("network down")

    monkeypatch.setattr(client_module, "urlopen", fail)
    transport = client_module.UrllibTransport("https://api.x.com")

    with pytest.raises(XComApiError, match="network"):
        transport.get_json("/2/users/by", {}, {})


def test_transport_wraps_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"not-json"

    monkeypatch.setattr(
        client_module, "urlopen", lambda *args, **kwargs: FakeResponse()
    )
    transport = client_module.UrllibTransport("https://api.x.com")

    with pytest.raises(XComApiError, match="Invalid JSON"):
        transport.get_json("/2/users/by", {}, {})


def test_client_rejects_custom_api_base_url_by_default() -> None:
    with pytest.raises(XComApiError, match="api.x.com"):
        XComClient(bearer_token="secret", api_base_url="https://attacker.example")


def test_client_allows_custom_api_base_url_when_explicit() -> None:
    client = XComClient(
        bearer_token="secret",
        api_base_url="https://example.test",
        allow_custom_api_base_url=True,
    )

    assert client.transport is not None
