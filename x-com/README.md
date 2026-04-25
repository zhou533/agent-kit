# x-com

`x-com` is an AgentKit tool for fetching X.com posts through X API v2. It exposes
the same core behavior through a CLI and an MCP tool.

## Configuration

Set credentials with AgentKit's standard environment variable pattern:

```bash
export AGENTKIT_X_COM_BEARER_TOKEN="..."
export AGENTKIT_X_COM_API_BASE_URL="https://api.x.com"
```

`AGENTKIT_X_COM_API_BASE_URL` is optional. Do not commit `.env` files or local MCP
configuration containing real credentials.

Custom API hosts are rejected by default. For local test doubles only, set
`AGENTKIT_X_COM_ALLOW_CUSTOM_API_BASE_URL=1` and keep the URL on HTTPS.

## CLI

```bash
uv run --project x-com x-com tweets --username XDevelopers --latest 10 --json
uv run --project x-com x-com tweets --usernames XDevelopers,OpenAI --exclude retweets --json
uv run --project x-com x-com tweets --user-id 2244994945 --start-time 2026-01-01T00:00:00Z --json
```

Fetch range rules:

- `--start-time` or `--end-time` selects time-range mode.
- `--latest N` selects latest-N mode.
- If neither is provided, the tool defaults to latest 10 posts.
- If both are provided, time-range mode takes precedence.

## MCP

Run the MCP server:

```bash
uv run --project x-com x-com-mcp
```

Registered tool:

```text
x_com_fetch_user_tweets
```

The MCP tool accepts `usernames`, `user_ids`, `latest_count`, `start_time`,
`end_time`, `exclude`, and related pagination/context parameters. It returns
structured JSON containing per-user tweets, includes, metadata, and errors.
