# SSE 交互拓扑图 — 测试 App 登录流程

## 一、整体架构

```
┌─────────────────┐     POST /api/v1/chat      ┌──────────────────────┐
│                 │ ─────────────────────────▶  │                      │
│   前端 (React)   │                            │   后端 (FastAPI)      │
│   ChatClient    │  ◀──── SSE data: {...} ──── │   MobileOrchestrator │
│   + zustand     │       text/event-stream     │   + ResponseHandler  │
│   + Timeline    │                            │   + QueueDomainEmitter│
└─────────────────┘                            └──────────┬───────────┘
                                                          │
                                                          │ astream(messages)
                                                          ▼
                                               ┌──────────────────────┐
                                               │  LangGraph Agent     │
                                               │  (test_agent)        │
                                               │  + LLM (OpenAI)      │
                                               │  + MCP Tools         │
                                               └──────────┬───────────┘
                                                          │
                                                          │ MCP Protocol
                                                          ▼
                                               ┌──────────────────────┐
                                               │  MCP Server          │
                                               │  (mobile_mcp)        │
                                               │  - mobile_launch_app │
                                               │  - mobile_wait       │
                                               │  - mobile_close_popup│
                                               │  - mobile_tap        │
                                               │  - mobile_screenshot │
                                               └──────────────────────┘
```

## 二、SSE 事件协议（StreamEvent 信封）

每条 SSE 帧格式：
```
data: {"v":1,"id":"evt_xxx","seq":1,"ts":1234567890,"conversation_id":"xxx","message_id":"xxx","type":"...","payload":{...}}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `v` | int | 协议版本，固定 1 |
| `id` | string | 事件唯一 ID |
| `seq` | int | 流内递增序号 |
| `ts` | int | 毫秒时间戳 |
| `conversation_id` | string | 会话 ID |
| `message_id` | string | 助手消息 ID |
| `type` | string | 事件类型 |
| `payload` | object | 事件载荷（按 type 变化） |

## 三、测试用例

```
测试任务名称：测试 App 登录流程
前置条件：App 处于关闭状态
测试步骤：
1. 打开App
2. 等待3秒
3. 关闭弹窗
4. 点击消息
5. 点击立即登录
验证点：显示"登录"或"注册"
com.im30.way
```

## 四、完整事件流时序图

```
前端 ChatClient                  后端 Orchestrator              LangGraph Agent              MCP Server
     │                                │                              │                          │
     │── POST /api/v1/chat ──────────▶│                              │                          │
     │   {message, conversation_id}   │                              │                          │
     │                                │                              │                          │
     │◀── seq:1 meta.start ──────────│                              │                          │
     │   {user_message_id,            │                              │                          │
     │    assistant_message_id}        │                              │                          │
     │                                │── astream(messages) ────────▶│                          │
     │                                │                              │                          │
     ╔══════════════════════════════════════════════════════════════════════════════════════════╗
     ║  第 1 轮 LLM 调用：分析测试用例，决定执行步骤 1（打开 App）                                  ║
     ╚══════════════════════════════════════════════════════════════════════════════════════════╝
     │                                │                              │                          │
     │◀── seq:2 llm.call.start ──────│◀── AIMessageChunk ──────────│                          │
     │   {message_count: 0}           │                              │                          │
     │                                │                              │                          │
     │◀── seq:3 assistant.reasoning  ─│◀── <think>分析步骤...</think>│                          │
     │   .delta {delta: "分析测试..."}  │                              │                          │
     │                                │                              │                          │
     │◀── seq:4 assistant.delta ─────│◀── "执行步骤1：打开App"       │                          │
     │   {delta: "执行步骤1..."}       │                              │                          │
     │                                │                              │                          │
     │◀── seq:5 tool.start ──────────│◀── AIMessageChunk            │                          │
     │   {tool_call_id: "tc_1",       │    .tool_calls[0]            │                          │
     │    name: "mobile_launch_app",  │                              │                          │
     │    input: {package: "com..."}} │                              │                          │
     │                                │                              │                          │
     │◀── seq:6 llm.call.end ────────│◀── ToolMessage ─────────────│── launch_app ───────────▶│
     │   {elapsed_ms: 2500}           │                              │                          │
     │                                │                              │◀── {success: true} ──────│
     │◀── seq:7 tool.end ────────────│◀── ToolMessage ─────────────│                          │
     │   {tool_call_id: "tc_1",       │    content: {success: true}  │                          │
     │    name: "mobile_launch_app",  │                              │                          │
     │    status: "success",           │                              │                          │
     │    output_preview: "..."}       │                              │                          │
     │                                │                              │                          │
     ╔══════════════════════════════════════════════════════════════════════════════════════════╗
     ║  第 2 轮 LLM 调用：步骤 1 成功，执行步骤 2（等待 3 秒）                                     ║
     ╚══════════════════════════════════════════════════════════════════════════════════════════╝
     │                                │                              │                          │
     │◀── seq:8 llm.call.start ──────│◀── AIMessageChunk ──────────│                          │
     │                                │                              │                          │
     │◀── seq:9 assistant.reasoning  ─│◀── <think>步骤1成功...</think>│                         │
     │   .delta                       │                              │                          │
     │                                │                              │                          │
     │◀── seq:10 tool.start ─────────│◀── AIMessageChunk            │                          │
     │   {tool_call_id: "tc_2",       │    .tool_calls[0]            │                          │
     │    name: "mobile_wait",        │                              │                          │
     │    input: {seconds: 3}}        │                              │                          │
     │                                │                              │                          │
     │◀── seq:11 llm.call.end ───────│◀── ToolMessage ─────────────│── wait(3s) ─────────────▶│
     │                                │                              │◀── {success: true} ──────│
     │◀── seq:12 tool.end ───────────│◀── ToolMessage               │                          │
     │   {status: "success"}          │                              │                          │
     │                                │                              │                          │
     ╔══════════════════════════════════════════════════════════════════════════════════════════╗
     ║  第 3 轮 LLM 调用：步骤 2 成功，执行步骤 3（关闭弹窗）                                      ║
     ╚══════════════════════════════════════════════════════════════════════════════════════════╝
     │                                │                              │                          │
     │◀── seq:13 llm.call.start ─────│◀── AIMessageChunk ──────────│                          │
     │                                │                              │                          │
     │◀── seq:14 assistant.reasoning ─│◀── <think>执行步骤3</think>  │                          │
     │   .delta                       │                              │                          │
     │                                │                              │                          │
     │◀── seq:15 tool.start ─────────│◀── AIMessageChunk            │                          │
     │   {tool_call_id: "tc_3",       │    .tool_calls[0]            │                          │
     │    name: "mobile_close_popup"} │                              │                          │
     │                                │                              │                          │
     │◀── seq:16 llm.call.end ───────│◀── ToolMessage ─────────────│── close_popup ──────────▶│
     │                                │                              │◀── {error / success} ────│
     │◀── seq:17 tool.end ───────────│◀── ToolMessage               │                          │
     │   {status: "success"|"error",  │                              │                          │
     │    error: "...（如有）"}        │                              │                          │
     │                                │                              │                          │
     ╔══════════════════════════════════════════════════════════════════════════════════════════╗
     ║  第 4 轮 LLM 调用：步骤 3 结果判断，执行步骤 4（点击消息）                                   ║
     ╚══════════════════════════════════════════════════════════════════════════════════════════╝
     │                                │                              │                          │
     │◀── seq:18 llm.call.start ─────│◀── AIMessageChunk ──────────│                          │
     │                                │                              │                          │
     │◀── seq:19 assistant.reasoning ─│                              │                          │
     │   .delta                       │                              │                          │
     │                                │                              │                          │
     │◀── seq:20 tool.start ─────────│◀── AIMessageChunk            │                          │
     │   {name: "mobile_tap",         │    .tool_calls[0]            │                          │
     │    input: {text: "消息"}}       │                              │                          │
     │                                │                              │                          │
     │◀── seq:21 llm.call.end ───────│◀── ToolMessage ─────────────│── tap("消息") ──────────▶│
     │                                │                              │◀── {error: "未找到"} ────│
     │◀── seq:22 tool.end ───────────│◀── ToolMessage               │                          │
     │   {status: "error",             │                              │                          │
     │    error: "未找到文本'消息'"}    │                              │                          │
     │                                │                              │                          │
     ╔══════════════════════════════════════════════════════════════════════════════════════════╗
     ║  第 5 轮 LLM 调用：步骤 4 失败，尝试截图分析 → 执行步骤 5（点击立即登录）                      ║
     ╚══════════════════════════════════════════════════════════════════════════════════════════╝
     │                                │                              │                          │
     │◀── seq:23 llm.call.start ─────│◀── AIMessageChunk ──────────│                          │
     │                                │                              │                          │
     │◀── seq:24 assistant.reasoning ─│◀── <think>截图分析...</think>│                          │
     │   .delta                       │                              │                          │
     │                                │                              │                          │
     │◀── seq:25 tool.start ─────────│◀── AIMessageChunk            │                          │
     │   {name: "mobile_screenshot"}  │    .tool_calls[0]            │                          │
     │                                │                              │                          │
     │◀── seq:26 llm.call.end ───────│◀── ToolMessage ─────────────│── screenshot ───────────▶│
     │                                │                              │◀── base64_data ──────────│
     │◀── seq:27 tool.end ───────────│◀── ToolMessage               │                          │
     │   {name: "mobile_screenshot",  │    截图 base64               │                          │
     │    screenshot_id: "ss_xxx",    │    → store_screenshot()      │                          │
     │    output_preview: "[截图]"}    │                              │                          │
     │                                │                              │                          │
     │  ... (可能还有 tap("立即登录") 等后续工具调用)                    │                          │
     │                                │                              │                          │
     ╔══════════════════════════════════════════════════════════════════════════════════════════╗
     ║  最终：生成测试报告                                                                       ║
     ╚══════════════════════════════════════════════════════════════════════════════════════════╝
     │                                │                              │                          │
     │◀── seq:N llm.call.start ──────│◀── AIMessageChunk ──────────│                          │
     │                                │                              │                          │
     │◀── seq:N+1 assistant.delta ───│◀── "测试报告：..."            │                          │
     │   {delta: "## 测试执行总结..."}│                              │                          │
     │                                │                              │                          │
     │◀── seq:N+2 llm.call.end ──────│◀── finalize() ──────────────│                          │
     │                                │                              │                          │
     │◀── seq:N+3 assistant.final ───│                              │                          │
     │   {content: "完整测试报告...",  │                              │                          │
     │    reasoning: "全部思考过程"}   │                              │                          │
     │                                │                              │                          │
     │◀── [SSE 流结束] ──────────────│◀── __end__ ─────────────────│                          │
     │                                │                              │                          │
```

## 五、每轮 LLM 调用的事件边界

一轮完整的工具调用循环产生以下事件序列（遵循 embedease-ai 协议）：

```
llm.call.start                    ← 新一轮 LLM 推理开始
  ├── assistant.reasoning.delta   ← <think>标签内的思考过程（前端折叠显示）
  ├── assistant.reasoning.delta   ← ...（多个增量）
  └── assistant.delta             ← </think>后的正文内容（前端正常显示）
llm.call.end                      ← 本轮推理结束（检测到 tool_calls 时触发）
tool.start                        ← 工具执行开始（紧跟 llm.call.end 之后）
tool.end                          ← 工具执行结果
```

## 六、前端 Timeline 状态管理

```
ChatClient.stream()
    │
    ▼
for await (event) ───────────────▶ timelineReducer(state, event)
    │                                      │
    │                                      ▼
    │                              TimelineState
    │                              ├── timeline: TimelineItem[]
    │                              │   ├── user.message       ← 用户消息
    │                              │   ├── llm.call.cluster   ← LLM 调用组
    │                              │   │   ├── reasoning      ←   思考过程（可折叠）
    │                              │   │   └── content        ←   正文内容
    │                              │   ├── tool.call          ← 工具调用
    │                              │   │   └── screenshot_id  ←   截图（自定义注入）
    │                              │   ├── llm.call.cluster   ← 下一轮 LLM 调用
    │                              │   ├── tool.call          ← 下一个工具调用
    │                              │   ├── ...                ← 重复
    │                              │   ├── error              ← 错误事件（如有）
    │                              │   └── final              ← 最终汇总
    │                              └── activeTurn
    │                                  ├── turnId
    │                                  ├── isStreaming
    │                                  ├── currentLlmCallId
    │                                  └── currentToolCallId
    │
    ▼ (tool.end 后处理)
inject screenshot_id ──────────▶ ToolCallItem.screenshot_id
```

## 七、关键修复点

### 修复前（问题）

```
AIMessageChunk(content="<think>分析步骤...</think>执行步骤1")
    │
    ▼ SDK 默认 v1 mode: parse_content_blocks()
    │
    ├── content = "<think>分析步骤...</think>执行步骤1"  ← 全部当作 text block
    │
    ▼ 发射 assistant.delta
    │
前端显示: "<think>分析步骤...</think>执行步骤1"  ← ❌ 思考内容混入正文

AIMessageChunk(tool_calls=[{name: "mobile_launch_app", ...}])
    │
    ▼ SDK 默认只解析 text/reasoning
    │
    ├── 没有发射 tool.start  ← ❌ 前端看不到工具开始状态
    │
ToolMessage(content="{success: true}")
    │
    ▼ _handle_tool_message (无 llm.call.end)
    │
    ├── 直接发射 tool.end  ← ❌ 多轮 LLM call 没有正确关闭
```

### 修复后（遵循 embedease-ai 协议）

```
AIMessageChunk(content="<think>分析步骤...</think>执行步骤1")
    │
    ▼ MobileResponseHandler._handle_ai_chunk()
    │
    ├── _split_think_tags() 分离
    │   ├── reasoning: "分析步骤..."     → assistant.reasoning.delta  ✅
    │   └── content: "执行步骤1"         → assistant.delta            ✅
    │
AIMessageChunk(tool_calls=[{name: "mobile_launch_app", ...}])
    │
    ▼ 检测 tool_calls → 按协议顺序发射
    │
    ├── 先发射 llm.call.end            ← 关闭当前 LLM call           ✅
    ├── 再发射 tool.start              ← 工具执行开始                 ✅
    │   {tool_call_id, name, input}
    │
ToolMessage(content="{success: true}")
    │
    ▼ _handle_tool_message
    │
    ├── 发射 tool.end                   ← 工具执行结果                ✅
    │   {screenshot_id（如有截图）}
```

## 八、事件顺序源码分析

### 8.1 LangGraph 消息序列（stream_mode="messages"）

LangGraph 在 `astream(stream_mode="messages")` 下，一轮工具调用产生的消息顺序：

```
AIMessageChunk(content="思考...")              ← 多个增量 chunk（流式）
AIMessageChunk(content="", tool_calls=[...])  ← 包含 tool_call 的最后 chunk
AIMessage(content="...", tool_calls=[...])     ← 完整消息（非流式兜底）
ToolMessage(content="工具结果")                ← LangGraph 执行工具后返回
```

### 8.2 embedease-ai 标准协议（events.py 定义）

embedease-ai 的 `StreamEventType` 明确定义了标准事件循环顺序：

```
[循环] llm.call.start → [reasoning.delta, delta...] → llm.call.end
          → tool.start → [products, todos...] → tool.end
```

**关键：`llm.call.end` 在 `tool.start` 之前。**

在 embedease-ai 中：
- **`tool.start` / `tool.end`** 由工具自身通过 `runtime.context.emitter.emit()` 发射
  （如 `search_products` 工具在执行开始/结束时自行发射）
- **`llm.call.start/end`** 由 `StreamingResponseHandler` 管理
- Agent 使用 `create_agent`（langchain factory.py）构建，支持多轮工具调用循环

### 8.3 SDK 基类事件发射（embedease-sdk StreamingResponseHandler）

| 方法 | 发射的事件 | 说明 |
|------|-----------|------|
| `_handle_ai_chunk` | `llm.call.start`（首次） | `_in_llm_call=False` 时触发 |
| `_handle_ai_chunk_v1` | `assistant.delta`, `assistant.reasoning.delta` | 通过 content_blocks 解析 |
| `_handle_ai_chunk` | —— | **不检测 tool_calls，不发 tool.start** |
| `_handle_tool_message` | —— | **仅去重，不发任何事件** |
| `finalize()` | `llm.call.end` + `assistant.final` | 整个流结束时关闭 LLM call |

SDK 基类不直接处理 `tool.start` / `tool.end`，因为 embedease-ai 的工具自行发射这些事件。
但 `llm.call.end` 在基类中只有 `finalize()` 发射一次 — 多轮场景下的中间轮次边界
依赖工具发射 `tool.start` 的时序自然分隔。

### 8.4 mobile-mcp 覆盖后的事件发射（MobileResponseHandler）

mobile-mcp 使用 MCP 远程工具，**工具自身不发射事件**，因此需要 handler 代劳。

| 方法 | 发射的事件 | 说明 |
|------|-----------|------|
| `_handle_ai_chunk` | `llm.call.start`（每轮首次） | `_in_llm_call=False` 时触发 |
| `_handle_ai_chunk` | `assistant.reasoning.delta` | `<think>` 标签内的内容 |
| `_handle_ai_chunk` | `assistant.delta` | `</think>` 后的正文 |
| `_handle_ai_chunk` | **`llm.call.end`** | 检测到 `tool_calls` 时**先**关闭 LLM call |
| `_handle_ai_chunk` | **`tool.start`** | 检测到 `tool_calls` 后**再**发射 tool.start |
| `_handle_tool_message` | **`tool.start`**（兜底） | 若 AIMessageChunk 中未检测到，补发 |
| `_handle_tool_message` | **`tool.end`** | 工具执行结果（含 screenshot_id） |
| `finalize()` | `llm.call.end` + `assistant.final` | 最后一轮 LLM call 的关闭 |

### 8.5 关键顺序结论：`llm.call.end` → `tool.start` → `tool.end`

```
时间线 ──────────────────────────────────────────────────▶

AIMessageChunk     AIMessageChunk        ToolMessage
(content chunk)    (tool_calls chunk)     (工具结果)
     │                   │                    │
     ▼                   ▼                    ▼
llm.call.start     llm.call.end → tool.start  tool.end
                        ↑            ↑            ↑
                        │            │            │
                   _handle_ai_chunk          _handle_tool_message
                   检测到 tool_calls:         发射 tool.end
                   1. 先关闭 LLM call
                   2. 再发射 tool.start
```

**为什么 `llm.call.end` 在 `tool.start` 之前？**

- 遵循 embedease-ai 协议：`llm.call.end` → `tool.start` → `tool.end`
- 语义：LLM 推理结束（做出工具调用决策）→ 工具执行开始 → 工具执行结束
- 在 embedease-ai 中，工具自行发射 `tool.start`，自然在 LLM 调用之后
- 在 mobile-mcp 中，handler 在检测到 `tool_calls` 时模拟相同顺序

**`_handle_tool_message` 中的兜底逻辑：**

- 如果 `_in_llm_call` 仍为 `True`（tool_calls 未在 chunk 中被检测到），
  先调用 `_close_llm_call()` 发射 `llm.call.end`
- 如果 `tool_call_id` 不在 `_emitted_tool_starts` 中，补发 `tool.start`
- 最终发射 `tool.end`
- 这确保即使 AIMessageChunk 未携带完整 tool_calls 信息，顺序仍然正确

### 8.6 前端 timelineReducer 兼容性验证

| 事件 | reducer 行为 | 是否依赖前序事件 |
|------|-------------|----------------|
| `llm.call.end` | 关闭当前 `LLMCallClusterItem`，清 `currentLlmCallId` | 依赖 `llm.call.start` |
| `tool.start` | 创建 `ToolCallItem`，设 `currentToolCallId` | 不依赖（独立 timeline item） |
| `tool.end` | 更新 `ToolCallItem` 状态，清 `currentToolCallId` | 依赖 `tool.start`（通过 `tool_call_id` 查找） |

→ `llm.call.end` → `tool.start` → `tool.end` 顺序与 reducer 完全兼容
→ 与 embedease-ai 协议保持一致
