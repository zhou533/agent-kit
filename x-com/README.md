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

Or run it directly from the GitHub remote:

```bash
uv tool run --from "git+https://github.com/zhou533/agent-kit.git#subdirectory=x-com" x-com-mcp
```

Registered tool:

```text
x_com_fetch_user_tweets
```

The MCP tool accepts `usernames`, `user_ids`, `latest_count`, `start_time`,
`end_time`, `exclude`, and related pagination/context parameters. It returns
structured JSON containing per-user tweets, includes, metadata, and errors.

### Codex MCP setup

Codex reads MCP servers from `config.toml`. Use user-level
`~/.codex/config.toml`, or project-level `.codex/config.toml` when this repository
is trusted.

Recommended project-level example:

```toml
[mcp_servers.x-com]
command = "uv"
args = [
  "tool",
  "run",
  "--from",
  "git+https://github.com/zhou533/agent-kit.git#subdirectory=x-com",
  "x-com-mcp"
]
env_vars = ["AGENTKIT_X_COM_BEARER_TOKEN"]

[mcp_servers.x-com.env]
AGENTKIT_X_COM_API_BASE_URL = "https://api.x.com"
```

Then start or reload Codex and use `/mcp` to confirm `x-com` is connected.

Avoid putting the bearer token directly in `config.toml`; set it in your shell or
secret manager instead:

```bash
export AGENTKIT_X_COM_BEARER_TOKEN="..."
```

### Claude Code MCP setup

For a stdio server installed from GitHub, run:

```bash
claude mcp add --transport stdio --scope local \
  --env AGENTKIT_X_COM_BEARER_TOKEN="$AGENTKIT_X_COM_BEARER_TOKEN" \
  --env AGENTKIT_X_COM_API_BASE_URL="https://api.x.com" \
  x-com -- uv tool run --from "git+https://github.com/zhou533/agent-kit.git#subdirectory=x-com" x-com-mcp
```

This avoids local path assumptions. Claude Code may start stdio MCP servers from
a different working directory, so project-relative commands like
`uv run --project x-com x-com-mcp` can fail with
`Project directory 'x-com' does not exist`.

Use `--scope project` if the team should share the MCP server definition through
`.mcp.json`. In that case, prefer environment variable expansion so credentials
stay local:

```json
{
  "mcpServers": {
    "x-com": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "git+https://github.com/zhou533/agent-kit.git#subdirectory=x-com",
        "x-com-mcp"
      ],
      "env": {
        "AGENTKIT_X_COM_BEARER_TOKEN": "${AGENTKIT_X_COM_BEARER_TOKEN}",
        "AGENTKIT_X_COM_API_BASE_URL": "${AGENTKIT_X_COM_API_BASE_URL:-https://api.x.com}"
      }
    }
  }
}
```

Verify in Claude Code with:

```bash
claude mcp list
```

or use `/mcp` inside Claude Code.
