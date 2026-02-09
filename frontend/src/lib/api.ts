/**
 * API 客户端 - 与后端 FastAPI 通信
 *
 * Chat SSE 由 @embedease/chat-sdk 的 ChatClient 负责，
 * 本文件只提供 REST API 和截图 URL 工具函数。
 */

/**
 * Backend API 基础地址
 * 优先级：localStorage > 环境变量 > 默认值
 */
function resolveApiBase(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("api_base");
    if (stored) return stored;
  }
  return (
    (typeof import.meta !== "undefined" && (import.meta as unknown as Record<string, Record<string, string>>).env?.VITE_API_BASE) ||
    "http://localhost:8088/api/v1"
  );
}

export let API_BASE = resolveApiBase();

/** 运行时更新 Backend 地址（Settings 页面使用） */
export function setApiBase(url: string): void {
  API_BASE = url;
  if (typeof window !== "undefined") {
    localStorage.setItem("api_base", url);
  }
}

// ── 通用请求 ─────────────────────────────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.text().catch(() => "");
    throw new Error(`API ${resp.status}: ${body}`);
  }
  return resp.json();
}

// ── Types ────────────────────────────────────────────────────

export interface ToolDetail {
  name: string;
  description: string;
}

export interface StatusResponse {
  ready: boolean;
  mcp_connected: boolean;
  tools_count: number;
  tool_names: string[];
  tools: ToolDetail[];
  mcp_url: string;
  uptime_seconds: number;
}

export interface DeviceInfo {
  id: string;
  name: string;
  platform: string;
  version: string;
  resolution: string;
  connected: boolean;
}

export interface DeviceListResponse {
  devices: DeviceInfo[];
}

export interface ConversationMessage {
  id: string;
  type: string;
  content: string;
  tool_name: string;
  tool_args: Record<string, unknown>;
  has_image: boolean;
  timestamp: string;
}

export interface ConversationSummary {
  id: string;
  created_at: string;
  summary: string;
  status: string;
  steps: number;
  duration: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[];
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
}

export interface LLMSettings {
  model: string;
  api_key: string;
  base_url: string;
}

export interface MCPSettings {
  url: string;
}

export interface AgentSettings {
  max_iterations: number;
  system_prompt: string;
}

export interface MiddlewareSettings {
  operation_logger: boolean;
  screenshot_optimizer: boolean;
  screenshot_max_consecutive: number;
  retry: boolean;
  retry_max_attempts: number;
  retry_interval: number;
}

export interface SettingsResponse {
  llm: LLMSettings;
  mcp: MCPSettings;
  agent: AgentSettings;
  middleware: MiddlewareSettings;
}

export interface SettingsUpdateRequest {
  llm?: Partial<LLMSettings>;
  mcp?: Partial<MCPSettings>;
  agent?: Partial<AgentSettings>;
  middleware?: Partial<MiddlewareSettings>;
}

export interface TestLLMResponse {
  success: boolean;
  message: string;
  model: string;
  latency_ms: number;
}

// ── API 方法 ─────────────────────────────────────────────────

export const api = {
  // Status
  getStatus: () => request<StatusResponse>("/status"),

  // Screenshot
  getScreenshotUrl: (screenshotId: string) =>
    `${API_BASE}/screenshot/${screenshotId}`,

  // Devices
  getDevices: () => request<DeviceListResponse>("/devices"),

  // Conversations
  getConversations: (query = "") =>
    request<ConversationListResponse>(
      `/conversations${query ? `?query=${encodeURIComponent(query)}` : ""}`,
    ),

  getConversation: (id: string) =>
    request<ConversationDetail>(`/conversations/${id}`),

  deleteConversation: (id: string) =>
    request<{ ok: boolean }>(`/conversations/${id}`, { method: "DELETE" }),

  // Settings
  getSettings: () => request<SettingsResponse>("/settings"),

  updateSettings: (data: SettingsUpdateRequest) =>
    request<SettingsResponse>("/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  testLLM: () =>
    request<TestLLMResponse>("/settings/test-llm", { method: "POST" }),

  reconnectMCP: () =>
    request<{ success: boolean; message: string; tools_count: number }>(
      "/settings/reconnect-mcp",
      { method: "POST" },
    ),
};
