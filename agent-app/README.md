# Mobile Agent

基于 `langchain.agents.create_agent` + `langgraph-agent-kit` 的移动端自动化 Agent。

**mobile-mcp 零改动** — 本项目作为独立的 MCP 客户端，通过 stdio 协议连接 mobile-mcp，替代 Cursor 实现自主移动端操作。

## 架构

```
用户 ──HTTP/CLI──→ Mobile Agent
                    ├── LLM（GPT-4o 等）
                    ├── langchain.agents.create_agent（Agent 框架）
                    ├── AgentMiddleware（日志/截图优化/重试）
                    └── MCP Client（langchain-mcp-adapters）
                           │
                           │ MCP 协议（stdio）
                           ↓
                    mobile-mcp（MCP Server，不动）
                           │
                           ↓
                        📱 手机设备
```

## 快速开始

### 1. 环境准备

```bash
cd agent-app

# 复制环境变量
cp .env.example .env
# 编辑 .env，填入 LLM API Key 等配置
```

### 2. 安装依赖

```bash
# 添加 embedease-sdk 子模块（如果还没有）
git submodule add <embedease-sdk-repo> packages/embedease-sdk

# 安装依赖
uv sync
```

### 3. CLI 模式

```bash
python -m mobile_agent.cli.interactive
```

```
🤖 Mobile Agent 已启动，输入任务开始操作手机
   输入 'quit' 退出

👤 > 打开微信，进入朋友圈
🤖 好的，我来帮你打开微信并进入朋友圈。
  🔧 mobile_launch_app(package_name='com.tencent.mm')
  🔧 mobile_list_elements()
  🔧 mobile_click_by_text(text='发现')
  🔧 mobile_click_by_text(text='朋友圈')
🤖 已成功进入微信朋友圈。
```

### 4. HTTP API 模式

```bash
uvicorn mobile_agent.api.app:app --host 0.0.0.0 --port 8088
```

**SSE 聊天：**

```bash
curl -N -X POST http://localhost:8088/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "打开微信"}'
```

**查看状态：**

```bash
curl http://localhost:8088/api/v1/status
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | SSE 流式聊天 |
| GET | `/api/v1/status` | Agent 和设备状态 |

## 项目结构

```
agent-app/
├── pyproject.toml                     # 依赖管理
├── .env                               # 环境变量
├── packages/
│   └── embedease-sdk/                 # Git Submodule
└── src/
    └── mobile_agent/
        ├── core/
        │   ├── config.py              # 配置管理
        │   ├── mcp_connection.py      # MCP 客户端连接
        │   ├── agent_builder.py       # Agent 构建器（create_agent）
        │   └── service.py             # Agent 服务（单例）
        ├── prompts/
        │   └── system_prompt.py       # System Prompt
        ├── streams/
        │   └── mobile_handler.py      # 响应处理器
        ├── middleware/
        │   ├── operation_logger.py    # 操作日志
        │   ├── screenshot_optimizer.py # 截图优化
        │   └── retry.py              # 工具重试
        ├── api/
        │   ├── app.py                 # FastAPI 入口
        │   ├── chat.py                # 聊天端点
        │   └── schemas.py             # 数据模型
        └── cli/
            └── interactive.py         # CLI 交互
```

## 技术栈

- **Agent 框架**: `langchain.agents.create_agent`（对 langgraph 的高层封装）
- **中间件**: `AgentMiddleware`（before_agent / before_model / after_model / after_agent / wrap_model_call / wrap_tool_call）
- **MCP 客户端**: `langchain-mcp-adapters`（自动转换 MCP 工具为 LangChain BaseTool）
- **流式编排**: `langgraph-agent-kit`（ChatStreamKit / SSE 事件系统）
- **HTTP**: FastAPI + SSE
