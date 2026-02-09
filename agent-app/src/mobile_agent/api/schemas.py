"""请求/响应模型"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Chat ──────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str = Field(..., description="用户消息")
    conversation_id: str = Field(default="", description="会话 ID（为空则自动生成）")
    user_id: str = Field(default="default", description="用户 ID")


# ── Status ────────────────────────────────────────────────────


class ToolDetail(BaseModel):
    """工具详情"""

    name: str
    description: str = ""


class StatusResponse(BaseModel):
    """状态响应"""

    ready: bool
    mcp_connected: bool
    tools_count: int
    tool_names: list[str]
    tools: list[ToolDetail] = Field(default_factory=list)
    mcp_url: str = ""
    uptime_seconds: float = 0.0


# ── Devices ───────────────────────────────────────────────────


class DeviceInfo(BaseModel):
    """设备信息"""

    id: str
    name: str
    platform: str
    version: str
    resolution: str
    connected: bool


class DeviceListResponse(BaseModel):
    """设备列表响应"""

    devices: list[DeviceInfo]


# ── History / Conversations ───────────────────────────────────


class ConversationMessage(BaseModel):
    """会话消息"""

    id: str
    type: str  # user / assistant / tool_call / tool_result
    content: str
    tool_name: str = ""
    tool_args: dict = Field(default_factory=dict)
    has_image: bool = False
    timestamp: str = ""


class ConversationSummary(BaseModel):
    """会话摘要（列表用）"""

    id: str
    created_at: str
    summary: str
    status: str = "success"  # success / failed
    steps: int = 0
    duration: str = ""


class ConversationDetail(BaseModel):
    """会话详情"""

    id: str
    created_at: str
    summary: str
    status: str = "success"
    steps: int = 0
    duration: str = ""
    messages: list[ConversationMessage] = Field(default_factory=list)


class ConversationListResponse(BaseModel):
    """会话列表响应"""

    conversations: list[ConversationSummary]
    total: int


# ── Settings ──────────────────────────────────────────────────


class LLMSettingsModel(BaseModel):
    """LLM 配置模型"""

    model: str = "openai:gpt-4o"
    api_key: str = ""
    base_url: str = ""


class MCPSettingsModel(BaseModel):
    """MCP Server 配置模型"""

    url: str = "http://localhost:3100/sse"


class AgentSettingsModel(BaseModel):
    """Agent 配置模型"""

    max_iterations: int = 20
    system_prompt: str = ""


class MiddlewareSettingsModel(BaseModel):
    """中间件配置模型"""

    operation_logger: bool = True
    screenshot_optimizer: bool = True
    screenshot_max_consecutive: int = 2
    retry: bool = True
    retry_max_attempts: int = 2
    retry_interval: float = 1.0


class SettingsResponse(BaseModel):
    """完整设置响应"""

    llm: LLMSettingsModel
    mcp: MCPSettingsModel
    agent: AgentSettingsModel
    middleware: MiddlewareSettingsModel


class SettingsUpdateRequest(BaseModel):
    """设置更新请求（部分更新）"""

    llm: LLMSettingsModel | None = None
    mcp: MCPSettingsModel | None = None
    agent: AgentSettingsModel | None = None
    middleware: MiddlewareSettingsModel | None = None


class TestLLMResponse(BaseModel):
    """测试 LLM 连接响应"""

    success: bool
    message: str
    model: str = ""
    latency_ms: float = 0.0
