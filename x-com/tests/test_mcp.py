from __future__ import annotations

from x_com.mcp import register_tools


class FakeMcp:
    def __init__(self) -> None:
        self.tools = {}

    def tool(self, name=None, description=None):
        def decorator(func):
            self.tools[name or func.__name__] = {
                "description": description,
                "handler": func,
            }
            return func

        return decorator


def test_register_tools_exposes_fetch_user_tweets_tool() -> None:
    class FakeResult:
        def to_dict(self):
            return {"users": [{"requested_user": {"username": "OpenAI"}}], "errors": []}

    class FakeService:
        def fetch_user_tweets(self, request):
            assert request.usernames == ["OpenAI"]
            assert request.latest_count == 10
            assert request.exclude == ["retweets", "replies"]
            return FakeResult()

    fake_mcp = FakeMcp()

    register_tools(fake_mcp, service_factory=lambda: FakeService())

    tool = fake_mcp.tools["x_com_fetch_user_tweets"]
    result = tool["handler"](usernames=["OpenAI"])

    assert tool["description"]
    assert result["users"][0]["requested_user"]["username"] == "OpenAI"


def test_register_tools_exposes_get_usage_tool() -> None:
    class FakeResult:
        def to_dict(self):
            return {
                "data": {"project_usage": 25},
                "summary": {"project_usage": 25},
                "meta": {"endpoint": "/2/usage/tweets"},
                "errors": [],
            }

    class FakeService:
        def fetch_usage(self, request):
            assert request.days == 7
            assert request.usage_fields is None
            return FakeResult()

    fake_mcp = FakeMcp()

    register_tools(fake_mcp, service_factory=lambda: FakeService())

    tool = fake_mcp.tools["x_com_get_usage"]
    result = tool["handler"]()

    assert tool["description"]
    assert result["data"] == {"project_usage": 25}


def test_mcp_usage_tool_validates_input_before_loading_configuration() -> None:
    fake_mcp = FakeMcp()

    register_tools(fake_mcp, service_factory=lambda: object())

    result = fake_mcp.tools["x_com_get_usage"]["handler"](
        days=91,
        usage_fields=["project_usage"],
    )

    assert result["data"] == {}
    assert result["errors"][0]["type"] == "validation_error"
    assert "days" in result["errors"][0]["message"]


def test_mcp_tool_can_include_retweets_and_replies() -> None:
    class FakeResult:
        def to_dict(self):
            return {"users": [], "errors": []}

    class FakeService:
        def fetch_user_tweets(self, request):
            assert request.exclude == []
            return FakeResult()

    fake_mcp = FakeMcp()
    register_tools(fake_mcp, service_factory=lambda: FakeService())

    result = fake_mcp.tools["x_com_fetch_user_tweets"]["handler"](
        usernames=["OpenAI"],
        include_retweets=True,
        include_replies=True,
    )

    assert result == {"users": [], "errors": []}


def test_mcp_tool_returns_structured_validation_error_for_invalid_time() -> None:
    fake_mcp = FakeMcp()

    register_tools(fake_mcp, service_factory=lambda: object())

    result = fake_mcp.tools["x_com_fetch_user_tweets"]["handler"](
        usernames=["OpenAI"],
        start_time="not-a-date",
    )

    assert result["users"] == []
    assert result["errors"][0]["type"] == "validation_error"
    assert "start_time" in result["errors"][0]["message"]


def test_mcp_tool_validates_input_before_loading_configuration() -> None:
    fake_mcp = FakeMcp()

    register_tools(fake_mcp, service_factory=lambda: object())

    result = fake_mcp.tools["x_com_fetch_user_tweets"]["handler"](
        usernames=["OpenAI"],
        exclude=["likes"],
    )

    assert result["users"] == []
    assert result["errors"][0]["type"] == "validation_error"
    assert "exclude" in result["errors"][0]["message"]


def test_mcp_tool_rejects_empty_username_after_cleanup() -> None:
    fake_mcp = FakeMcp()

    register_tools(fake_mcp, service_factory=lambda: object())

    result = fake_mcp.tools["x_com_fetch_user_tweets"]["handler"](usernames=["@"])

    assert result["users"] == []
    assert result["errors"][0]["type"] == "validation_error"
    assert "usernames or user_ids" in result["errors"][0]["message"]


def test_mcp_tool_handles_mixed_datetime_awareness() -> None:
    class FakeResult:
        def to_dict(self):
            return {"users": [], "errors": []}

    class FakeService:
        def fetch_user_tweets(self, request):
            assert request.validation_errors() == []
            return FakeResult()

    fake_mcp = FakeMcp()
    register_tools(fake_mcp, service_factory=lambda: FakeService())

    result = fake_mcp.tools["x_com_fetch_user_tweets"]["handler"](
        user_ids=["123"],
        start_time="2026-01-01T00:00:00",
        end_time="2026-01-02T00:00:00Z",
    )

    assert result == {"users": [], "errors": []}
