# 实施方案：x-com 工具

## 概述

`x-com` 是 AgentKit 中面向 X API 的工具目录。第一阶段目标是通过 X API v2
获取一个或多个用户的推文，并返回包含作者、引用/回复关系、媒体、地点、投票
和上下文注解等字段的结构化结果。工具需要同时提供 CLI 和 MCP 入口，并为后续
扩展到搜索、用户信息、会话上下文、列表、空间等 X API 能力预留稳定架构。

## 需求

- 创建独立工具目录 `x-com/`。
- 支持按 username 或 user id 获取单人或多人推文。
- 获取范围支持两种模式：指定时间范围，或指定最新 N 条。两者都未指定时默认
  获取最新 10 条；两者同时指定时以时间范围优先。
- 默认排除 retweets 和 replies，以降低无关内容与 API 消耗；可通过参数显式
  包含 retweets 或 replies。
- 返回推文上下文详细字段，包括 `includes` 中的关联用户、媒体、地点、投票和
  被引用推文。
- 支持 CLI 和 MCP 两种入口。
- 访问 X API 的 token 配置方案要可复用，并作为 AgentKit 工具集统一约定。
- 保持扩展性，后续可以继续接入 X API 其他端点。

## 外部 API 依据

基于 Context7 查询到的 X API v2 文档，首期使用以下端点：

- `GET /2/users/by`
  - 用途：批量通过 usernames 解析用户。
  - 关键参数：`usernames`、`user.fields`。
  - 适用场景：输入是一个或多个 username 时，先解析为 user id。
- `GET /2/users/by/username/:username`
  - 用途：通过单个 username 获取用户详情。
  - 关键参数：`user.fields`、`expansions`、`tweet.fields`。
  - 适用场景：单用户查询或调试。
- `GET /2/users/{id}/tweets`
  - 用途：获取指定用户发布的推文。
  - 关键参数：`max_results`、`pagination_token`、`start_time`、`end_time`、
    `since_id`、`until_id`、`exclude`、`tweet.fields`、`expansions`、
    `user.fields`、`media.fields`、`poll.fields`。
  - 适用场景：首期核心能力。
- `GET /2/tweets/search/recent`
  - 用途：后续支持搜索式获取，例如 `from:username` 或多条件组合。
  - 关键参数：`query`、`max_results`、`pagination_token`、`tweet.fields`、
    `expansions`、`user.fields`、`media.fields`。
  - 适用场景：阶段 2 扩展。

默认字段建议：

```text
tweet.fields:
  id,text,author_id,created_at,conversation_id,context_annotations,
  referenced_tweets,in_reply_to_user_id,attachments,entities,geo,lang,
  public_metrics,possibly_sensitive,reply_settings,source,edit_history_tweet_ids,
  edit_controls,note_tweet

expansions:
  author_id,in_reply_to_user_id,referenced_tweets.id,
  referenced_tweets.id.author_id,attachments.media_keys,attachments.poll_ids,
  geo.place_id,entities.mentions.username

user.fields:
  id,name,username,created_at,description,entities,location,profile_image_url,
  protected,public_metrics,url,verified,verified_type,withheld

media.fields:
  media_key,type,url,preview_image_url,duration_ms,height,width,alt_text,
  public_metrics,variants

poll.fields:
  id,options,duration_minutes,end_datetime,voting_status

place.fields:
  id,full_name,country,country_code,geo,name,place_type
```

## 目标目录结构

```text
x-com/
  DESIGN.md
  README.md
  pyproject.toml
  src/x_com/
    __init__.py
    config.py
    models.py
    errors.py
    client.py
    service.py
    cli.py
    mcp.py
  tests/
    test_config.py
    test_models.py
    test_service.py
    test_cli.py
    test_mcp.py
```

说明：

- 仓库根目录使用 `x-com/`，便于工具目录名称贴近产品/接口名称。
- Python 包使用 `x_com`，避免连字符导致导入问题。
- `client.py` 只负责 X API HTTP 调用、分页、重试和错误转换。
- `service.py` 负责编排“解析用户 -> 拉取推文 -> 归一化响应”。
- `cli.py` 和 `mcp.py` 都只调用 `service.py`，不重复业务逻辑。

## 核心模型设计

```python
class XComAuthConfig:
    bearer_token: SecretStr
    api_base_url: str = "https://api.x.com"

class FetchUserTweetsRequest:
    usernames: list[str] = []
    user_ids: list[str] = []
    latest_count: int | None = None
    max_pages_per_user: int = 1
    start_time: datetime | None = None
    end_time: datetime | None = None
    since_id: str | None = None
    until_id: str | None = None
    exclude: list[Literal["retweets", "replies"]] | None = None
    include_retweets: bool = False
    include_replies: bool = False
    include_context: bool = True
    fields_profile: Literal["default", "minimal", "full"] = "default"

class XComTweetBundle:
    requested_user: XComUserRef
    tweets: list[XComTweet]
    includes: XComIncludes
    meta: XComPageMeta
    errors: list[XComApiError] = []

class FetchUserTweetsResult:
    users: list[XComTweetBundle]
    errors: list[XComApiError] = []
```

设计原则：

- 所有 X API ID 都使用 `str`，避免大整数精度问题。
- 输出保留 X API 原始字段，同时可以提供归一化辅助字段。
- `includes` 不丢弃，便于智能体追溯上下文。
- 获取范围在服务层归一化：
  - 如果提供 `start_time` 或 `end_time`，使用时间范围模式。
  - 如果没有时间范围但提供 `latest_count`，获取最新 N 条。
  - 如果时间范围和 `latest_count` 都未提供，默认 `latest_count = 10`。
  - 如果时间范围和 `latest_count` 同时提供，以时间范围优先，忽略
    `latest_count`。
- errors 按用户聚合，单个用户失败不应默认导致整个批次失败；CLI 可通过
  `--fail-fast` 改变行为。

## CLI 设计

首期命令：

```bash
uv run --project x-com x-com tweets --username XDevelopers --latest 50 --json
uv run --project x-com x-com tweets --usernames XDevelopers,OpenAI --include-replies --json
uv run --project x-com x-com tweets --user-id 2244994945 --start-time 2026-01-01T00:00:00Z --json
```

关键参数：

- `--username`：单个 username，可重复。
- `--usernames`：逗号分隔 usernames。
- `--user-id`：单个 user id，可重复。
- `--latest`：每个用户获取最新 N 条；未指定时间范围且未指定 `--latest` 时默认
  为 10。
- `--max-pages`：每个用户最多分页数，防止意外拉取过多。
- `--start-time` / `--end-time`：时间范围模式。只要指定任一时间边界，就优先按
  时间范围获取，即使同时提供 `--latest` 也忽略 `--latest`。
- `--since-id` / `--until-id`：ID 边界，可与时间模式或 latest 模式组合传给
  X API，但不决定“时间范围 vs 最新 N 条”的主选择模式。
- 默认排除 `retweets,replies`：减少噪声和 API 消耗。
- `--include-retweets`：包含转推。
- `--include-replies`：包含回复。
- `--exclude retweets,replies`：显式设置排除项；未设置时使用默认排除项。
- 同一类型不能同时 include 和 exclude，例如 `--include-retweets` 不能和
  `--exclude retweets` 同时使用。
- `--fields-profile minimal|default|full`：控制字段集合。
- `--json`：输出结构化 JSON。
- `--fail-fast`：遇到单用户失败立即退出。

## MCP 设计

Python MCP 首选 `mcp.server.fastmcp.FastMCP`。MCP 注册层只定义工具 schema 和调用
服务层，不直接拼 X API 请求。

首期 MCP tool：

```text
x_com_fetch_user_tweets
```

输入：

```json
{
  "usernames": ["XDevelopers", "OpenAI"],
  "user_ids": [],
  "latest_count": 50,
  "max_pages_per_user": 1,
  "start_time": null,
  "end_time": null,
  "since_id": null,
  "until_id": null,
  "exclude": null,
  "include_retweets": false,
  "include_replies": false,
  "include_context": true,
  "fields_profile": "default"
}
```

MCP 输入归一化规则与 CLI 一致：

- `start_time` 或 `end_time` 任一存在时，按时间范围获取。
- `start_time`、`end_time`、`latest_count` 都为空时，默认 `latest_count = 10`。
- 时间范围和 `latest_count` 同时存在时，时间范围优先。

输出：

```json
{
  "users": [
    {
      "requested_user": {"id": "2244994945", "username": "XDevelopers"},
      "tweets": [],
      "includes": {
        "users": [],
        "tweets": [],
        "media": [],
        "polls": [],
        "places": []
      },
      "meta": {"result_count": 0, "next_token": null},
      "errors": []
    }
  ],
  "errors": []
}
```

后续 MCP tools 可按能力扩展：

- `x_com_lookup_users`
- `x_com_search_recent_posts`
- `x_com_fetch_post`
- `x_com_fetch_conversation`
- `x_com_fetch_mentions`

## Access Token 与密钥约定

AgentKit 统一采用“环境变量优先，本地 `.env` 仅用于开发，不提交仓库”的密钥
策略：

1. 所有工具的密钥环境变量使用 `AGENTKIT_<TOOL>_<NAME>` 格式。
2. `<TOOL>` 使用大写蛇形命名，和工具目录对应。例如 `x-com` 对应 `X_COM`。
3. 常用变量：
   - `AGENTKIT_X_COM_BEARER_TOKEN`
   - `AGENTKIT_X_COM_API_BASE_URL`
4. CLI 和 MCP 都通过同一套 `config.py` 读取配置。
5. 不在命令参数中鼓励传 token，避免 shell history 泄漏。仅可提供
   `--profile`、`--env-file` 之类的配置定位参数。
6. `.env`、`.env.*`、本地 MCP 配置和任何真实凭据不得提交。
7. 错误消息不得打印 token 原文，只能提示变量缺失或权限不足。

配置加载优先级：

```text
显式 env_file（仅本地开发） > 当前进程环境变量 > 工具默认值
```

第一阶段只要求 Bearer Token。若后续引入需要用户上下文的写操作或私有数据读取，
再扩展：

- `AGENTKIT_X_COM_CLIENT_ID`
- `AGENTKIT_X_COM_CLIENT_SECRET`
- `AGENTKIT_X_COM_REFRESH_TOKEN`
- `AGENTKIT_X_COM_ACCESS_TOKEN`

## 架构变更

- `AGENTS.md`
  - 增加“每个新工具必须拥有独立根目录”的项目约定。
- `x-com/DESIGN.md`
  - 记录 x-com 工具的首期设计、目录结构、API 依据、CLI/MCP 契约和密钥约定。

## 实施步骤

### 阶段 1：设计与项目约定

1. **创建工具目录**（文件：`x-com/DESIGN.md`）
   - 操作：建立 `x-com/` 并写入当前设计。
   - 原因：后续所有实现、文档和测试都在独立工具目录内演进。
   - 依赖：无。
   - 风险：低。

2. **更新仓库指令**（文件：`AGENTS.md`）
   - 操作：写入“每个新工具必须拥有独立目录”的约定。
   - 原因：这是跨工具结构规范，应放入项目级 Codex 指令。
   - 依赖：无。
   - 风险：低。

### 阶段 2：核心库骨架

1. **初始化 Python 包**（文件：`x-com/pyproject.toml`、`x-com/src/x_com/*`）
   - 操作：定义包、依赖、CLI script、基础模块。
   - 原因：建立可由 CLI 和 MCP 复用的核心代码。
   - 依赖：阶段 1。
   - 风险：低。

2. **实现配置加载**（文件：`x-com/src/x_com/config.py`）
   - 操作：读取 `AGENTKIT_X_COM_BEARER_TOKEN`，支持可选 env file。
   - 原因：统一工具集的 token 管理方式。
   - 依赖：包骨架。
   - 风险：中；必须避免泄漏 secret。

3. **实现 X API client**（文件：`x-com/src/x_com/client.py`）
   - 操作：封装 `/2/users/by` 和 `/2/users/{id}/tweets`，处理分页、状态码、
     rate limit 和 X API errors。
   - 原因：隔离外部 API 细节，便于后续扩展端点。
   - 依赖：配置与模型。
   - 风险：中；需处理权限、限流和部分用户失败。

4. **实现服务层**（文件：`x-com/src/x_com/service.py`）
   - 操作：完成批量用户解析和推文获取编排，返回 `FetchUserTweetsResult`。
   - 原因：CLI/MCP 共享同一行为。
   - 依赖：client。
   - 风险：中；需保证输出结构稳定。

### 阶段 3：入口适配

1. **实现 CLI**（文件：`x-com/src/x_com/cli.py`）
   - 操作：实现 `x-com tweets` 命令和 JSON 输出。
   - 原因：满足 shell/自动化使用。
   - 依赖：服务层。
   - 风险：低。

2. **实现 MCP server**（文件：`x-com/src/x_com/mcp.py`）
   - 操作：使用 FastMCP 注册 `x_com_fetch_user_tweets`。
   - 原因：满足智能体协议调用。
   - 依赖：服务层。
   - 风险：中；需保持 schema 与服务模型一致。

### 阶段 4：测试与文档

1. **测试配置与模型**（文件：`x-com/tests/test_config.py`、`test_models.py`）
   - 操作：覆盖 token 缺失、env 加载、字段 profile。
   - 风险：低。

2. **测试服务层**（文件：`x-com/tests/test_service.py`）
   - 操作：mock X API 响应，覆盖单用户、多用户、分页、部分失败、空结果。
   - 风险：中。

3. **测试 CLI/MCP 冒烟**（文件：`x-com/tests/test_cli.py`、`test_mcp.py`）
   - 操作：验证命令参数映射、JSON 输出、MCP tool schema。
   - 风险：中。

4. **补充 README**（文件：`x-com/README.md`）
   - 操作：记录安装、环境变量、CLI 示例、MCP 配置和限制。
   - 风险：低。

## 测试策略

- 单元测试：配置加载、字段 profile、模型校验、错误映射。
- 集成式单元测试：使用 mock HTTP transport 验证 X API client。
- CLI 冒烟：用 fake service 或 mock transport 验证 `--json` 输出。
- MCP 冒烟：验证 FastMCP tool 注册和参数到服务层的映射。
- 不在默认测试中调用真实 X API；真实 API 测试应通过显式环境变量开启。

## 风险与缓解措施

- **风险：X API 权限和计费层限制导致端点不可用。**
  - 缓解：错误响应保留 X API code/title/detail，文档说明所需权限；测试不依赖
    真实 API。
- **风险：字段集合过大导致响应膨胀或接口拒绝。**
  - 缓解：提供 `minimal/default/full` profile，默认只取智能体常用上下文字段。
- **风险：多用户批量请求中部分用户失败。**
  - 缓解：默认按用户聚合错误并继续；提供 `fail_fast` 模式。
- **风险：token 泄漏。**
  - 缓解：统一环境变量配置，不在日志、异常和 CLI 输出中打印 secret。
- **风险：后续扩展端点导致服务层膨胀。**
  - 缓解：按能力拆分 service 方法和 request/result 模型，client 每个端点独立方法。

## 成功标准

- [x] 创建 `x-com/` 独立工具目录。
- [x] 在 `AGENTS.md` 写入新工具独立目录约定。
- [x] 设计支持通过 username 或 user id 获取一人或多人推文。
- [x] 设计包含 X API 上下文字段、expansions 和 includes 处理方案。
- [x] 设计包含 CLI 与 MCP 入口。
- [x] 设计包含统一 token/secret 配置约定。
- [ ] 后续实现完成后，`uv run pytest` 通过。
- [ ] 后续实现完成后，CLI 与 MCP 冒烟测试通过。
