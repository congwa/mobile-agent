# 测试用例执行 Agent 编码规划

## 一、现有架构分析

### 1. langchain `factory.py` 核心模式

`create_agent()` 构建 `StateGraph`，支持以下中间件钩子：

| 钩子 | 时机 | 用途 |
|------|------|------|
| `before_agent` | Agent 启动时（仅一次） | 初始化状态 |
| `before_model` | 每轮 LLM 调用前 | 注入上下文 |
| `wrap_model_call` | 包裹 LLM 调用 | 动态修改 tools/prompt |
| `after_model` | LLM 调用后 | 状态转换、步骤推进 |
| `wrap_tool_call` | 包裹工具调用 | 日志/重试 |
| `after_agent` | Agent 结束时（仅一次） | 汇总结果 |

关键能力：

- 中间件通过 `state_schema` 属性扩展 Agent 状态
- `aafter_model` 可以返回 `dict` 更新 state
- `awrap_model_call` 可以通过 `request.override(tools=..., system_message=...)` 动态修改请求

### 2. Skill-Know 的 `StatefulToolMiddleware` 模式（要学习的核心）

```python
class SkillPhase(str, Enum):
    INIT = "init"
    INTENT_ANALYSIS = "intent_analysis"
    SKILL_RETRIEVAL = "skill_retrieval"
    TOOL_PREPARATION = "tool_preparation"
    EXECUTION = "execution"

class SkillSearchState(AgentState[Any]):
    phase: Annotated[NotRequired[...], OmitFromInput]
    keywords: Annotated[NotRequired[list[str]], OmitFromInput]
    skill_ids: Annotated[NotRequired[list[str]], OmitFromInput]
```

**关键设计点：**

- 用 `Enum` 定义阶段，state 中保存 `phase` 字段
- `awrap_model_call` 根据 phase 动态注入工具
- `aafter_model` 根据 LLM 工具调用结果推进阶段

### 3. mobile-mcp agent-app 现有架构

- 使用 `create_agent()` + 3 个中间件（OperationLogger / ScreenshotOptimizer / Retry）
- MCP 工具通过 `MCPConnectionManager` 获取（mobile_click_by_text, mobile_wait, mobile_close_popup 等）
- Service 是单例模式，管理 Agent 生命周期

---

## 二、整体方案

### 核心思路

学习 Skill-Know 的 `StatefulToolMiddleware` 状态机模式，在 `mobile-mcp/agent-app` 中新增一个 **`TestExecutorMiddleware`**，将用户提供的测试步骤编排为 state 中的状态序列，Agent 每执行完一步就自动推进到下一步，直到验证点通过或失败。

### 状态机流转图

```
START
  │
  ▼
[SETUP] ─── 检查前置条件（App 已安装、设备连接）
  │
  ▼
[STEP_1] ── 等待2秒        → awrap_model_call 注入: "请调用 mobile_wait(2)"
  │                          aafter_model 检查: mobile_wait 调用成功 → 推进
  ▼
[STEP_2] ── 关闭弹窗       → awrap_model_call 注入: "请调用 mobile_close_popup"
  │                          aafter_model 检查: 结果不含 error → 推进
  ▼
[STEP_3] ── 点击我的        → awrap_model_call 注入: "请调用 mobile_click_by_text('我的')"
  │                          aafter_model 检查 → 推进
  ▼
  ... (每步同理)
  ▼
[STEP_8] ── 验证Toast包含"账号切换成功"
  │
  ▼
[COMPLETED / FAILED] ── 输出测试报告
```

---

## 三、文件结构规划

```
mobile-mcp/agent-app/src/mobile_agent/
├── models/                          # 【新增目录】
│   ├── __init__.py
│   └── test_case.py                 # 测试用例数据模型 + 解析器
│
├── middleware/
│   ├── __init__.py                  # 【修改】导出新中间件
│   ├── test_executor.py             # 【新增】核心：测试执行状态机中间件
│   ├── operation_logger.py          # 不变
│   ├── retry.py                     # 不变
│   └── screenshot_optimizer.py      # 不变
│
├── prompts/
│   ├── system_prompt.py             # 不变
│   └── test_prompt.py               # 【新增】测试执行专用 prompt 模板
│
├── core/
│   ├── agent_builder.py             # 【修改】新增 build_test_agent() 工厂方法
│   ├── service.py                   # 【修改】新增 run_test_case() 入口
│   ├── config.py                    # 不变
│   ├── mcp_connection.py            # 不变
│   └── storage.py                   # 不变
│
└── api/
    └── routes.py (或类似)            # 【修改】新增测试执行 API 路由
```

---

## 四、详细编码步骤

### Step 1: `models/test_case.py` — 测试用例数据模型

**职责：** 将用户输入的文本解析为结构化测试用例

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TestAction(str, Enum):
    """测试动作类型 → 对应 MCP 工具"""
    WAIT = "wait"                              # → mobile_wait
    CLOSE_POPUP = "close_popup"                # → mobile_close_popup
    CLICK = "click"                            # → mobile_click_by_text
    INPUT_TEXT = "input_text"                   # → mobile_input_text
    SWIPE = "swipe"                            # → mobile_swipe
    START_TOAST_LISTENER = "start_toast_listener"  # → mobile_start_toast_listener
    VERIFY_TOAST = "verify_toast"              # → mobile_get_toast
    SCREENSHOT = "screenshot"                  # → mobile_take_screenshot
    ASSERT_ELEMENT = "assert_element"          # 验证元素存在


class StepStatus(str, Enum):
    """步骤执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestStep:
    """单个测试步骤"""
    index: int                          # 步骤序号 (1-based)
    action: TestAction                  # 动作类型
    target: str = ""                    # 操作目标 ("我的", "设置")
    params: dict[str, Any] = field(default_factory=dict)  # 额外参数
    status: StepStatus = StepStatus.PENDING
    result: str = ""                    # 执行结果描述
    mcp_tool_hint: str = ""             # 对应的 MCP 工具名提示

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "action": self.action.value,
            "target": self.target,
            "params": self.params,
            "status": self.status.value,
            "result": self.result,
            "mcp_tool_hint": self.mcp_tool_hint,
        }


@dataclass
class TestCase:
    """测试用例"""
    name: str                            # 测试任务名称
    preconditions: list[str]             # 前置条件
    steps: list[TestStep]                # 测试步骤列表
    verifications: list[str]             # 验证点
    app_package: str = ""                # com.qiyi.video.lite
    device_serial: str = ""              # 4XWW6XFAA6OJIBJB

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "preconditions": self.preconditions,
            "steps": [s.to_dict() for s in self.steps],
            "verifications": self.verifications,
            "app_package": self.app_package,
            "device_serial": self.device_serial,
        }


def parse_test_case(raw_text: str) -> TestCase:
    """将用户输入文本解析为 TestCase

    解析规则：
    - "等待2秒"              → TestAction.WAIT, params={"duration": 2}
    - "关闭弹窗"             → TestAction.CLOSE_POPUP
    - "点击我的"             → TestAction.CLICK, target="我的"
    - "点击设置"             → TestAction.CLICK, target="设置"
    - "开始监听Toast"        → TestAction.START_TOAST_LISTENER
    - "点击梦醒初八"         → TestAction.CLICK, target="梦醒初八"
    - "验证Toast包含'xxx'"   → TestAction.VERIFY_TOAST, params={"contains": "xxx"}
    """
    # TODO: 实现解析逻辑
    ...
```

### Step 2: `middleware/test_executor.py` — 核心状态机中间件

**职责：** 管理测试执行的完整生命周期，逐步引导 Agent 执行每个步骤

```python
from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Annotated, Any, Literal

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    OmitFromInput,
)
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.runtime import Runtime
from typing_extensions import NotRequired

from mobile_agent.models.test_case import TestCase, StepStatus
from mobile_agent.prompts.test_prompt import build_step_prompt, build_test_system_prompt


class TestPhase(str, Enum):
    """测试执行阶段"""
    IDLE = "idle"                # 未开始
    SETUP = "setup"              # 前置检查
    EXECUTING = "executing"      # 执行步骤中
    VERIFYING = "verifying"      # 验证断言
    COMPLETED = "completed"      # 测试通过
    FAILED = "failed"            # 测试失败


class TestExecutionState(AgentState[Any]):
    """测试执行状态 Schema — 扩展 AgentState"""

    test_phase: Annotated[NotRequired[Literal[
        "idle", "setup", "executing", "verifying", "completed", "failed"
    ]], OmitFromInput]
    """当前测试阶段"""

    current_step_index: Annotated[NotRequired[int], OmitFromInput]
    """当前步骤索引 (0-based)"""

    total_steps: Annotated[NotRequired[int], OmitFromInput]
    """总步骤数"""

    step_results: Annotated[NotRequired[list[dict]], OmitFromInput]
    """每步执行结果"""

    test_case_data: Annotated[NotRequired[dict], OmitFromInput]
    """测试用例数据 (TestCase.to_dict())"""

    verification_passed: Annotated[NotRequired[bool], OmitFromInput]
    """验证是否通过"""


class TestExecutorMiddleware(AgentMiddleware):
    """测试执行状态机中间件

    学习 Skill-Know 的 StatefulToolMiddleware 模式：
    - abefore_agent: 初始化测试状态
    - awrap_model_call: 根据当前步骤构建精确 prompt
    - aafter_model: 检查结果、推进步骤
    - aafter_agent: 生成测试报告
    """

    state_schema = TestExecutionState

    def __init__(self, test_case: TestCase) -> None:
        super().__init__()
        self._test_case = test_case

    # ── abefore_agent: 初始化 ────────────────────────

    async def abefore_agent(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any]:
        """Agent 启动时初始化测试状态"""
        return {
            "test_phase": TestPhase.SETUP.value,
            "current_step_index": 0,
            "total_steps": len(self._test_case.steps),
            "step_results": [],
            "test_case_data": self._test_case.to_dict(),
            "verification_passed": False,
        }

    # ── awrap_model_call: 步骤级 prompt 注入 ─────────

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """每轮 LLM 调用前：根据当前步骤构建精确的指令 prompt"""
        state = request.state
        phase = state.get("test_phase", "idle")
        step_idx = state.get("current_step_index", 0)

        if phase == "setup":
            # 前置检查 prompt
            setup_prompt = self._build_setup_prompt()
            updated = request.override(
                system_message=SystemMessage(content=setup_prompt)
            )
            return await handler(updated)

        if phase == "executing" and step_idx < len(self._test_case.steps):
            current_step = self._test_case.steps[step_idx]
            step_prompt = build_step_prompt(
                current_step, step_idx, self._test_case
            )
            updated = request.override(
                system_message=SystemMessage(content=step_prompt)
            )
            return await handler(updated)

        if phase in ("completed", "failed"):
            # 测试结束，生成报告 prompt
            report_prompt = self._build_report_prompt(state)
            updated = request.override(
                system_message=SystemMessage(content=report_prompt)
            )
            return await handler(updated)

        return await handler(request)

    # ── aafter_model: 步骤推进 ───────────────────────

    async def aafter_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        """LLM 调用后：检查工具调用结果，推进步骤"""
        phase = state.get("test_phase")
        step_idx = state.get("current_step_index", 0)
        messages = state.get("messages", [])

        if phase == "setup":
            # 前置检查完成 → 进入执行
            return {
                "test_phase": TestPhase.EXECUTING.value,
                "current_step_index": 0,
            }

        if phase == "executing":
            step = self._test_case.steps[step_idx]
            success = self._check_step_result(messages, step)

            step_results = list(state.get("step_results", []))
            step_results.append({
                "index": step_idx,
                "action": step.action.value,
                "target": step.target,
                "passed": success,
            })

            if not success:
                return {
                    "test_phase": TestPhase.FAILED.value,
                    "step_results": step_results,
                }

            next_idx = step_idx + 1
            if next_idx >= len(self._test_case.steps):
                return {
                    "test_phase": TestPhase.VERIFYING.value,
                    "step_results": step_results,
                    "current_step_index": next_idx,
                }

            return {
                "current_step_index": next_idx,
                "step_results": step_results,
            }

        if phase == "verifying":
            passed = self._check_verification(messages)
            return {
                "test_phase": (
                    TestPhase.COMPLETED.value if passed
                    else TestPhase.FAILED.value
                ),
                "verification_passed": passed,
            }

        return None

    # ── aafter_agent: 测试报告 ───────────────────────

    async def aafter_agent(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        """Agent 结束时：生成测试报告"""
        report = self._generate_report(state)
        return {"messages": [AIMessage(content=report)]}

    # ── 内部辅助方法 ─────────────────────────────────

    def _build_setup_prompt(self) -> str:
        """构建前置检查 prompt"""
        preconditions = "\n".join(
            f"- {p}" for p in self._test_case.preconditions
        )
        return f"""你正在准备执行测试用例「{self._test_case.name}」。

前置条件:
{preconditions}

App包名: {self._test_case.app_package}
设备序列号: {self._test_case.device_serial}

请确认设备已连接，App 已安装。如果需要，可以调用 mobile_list_devices 检查设备状态。
确认就绪后，回复"前置检查完成"即可。"""

    def _build_report_prompt(self, state: dict) -> str:
        """构建报告生成 prompt"""
        phase = state.get("test_phase", "unknown")
        passed = state.get("verification_passed", False)
        step_results = state.get("step_results", [])
        return f"""测试已结束。请生成测试报告。

测试用例: {self._test_case.name}
最终状态: {phase}
验证通过: {passed}
步骤结果: {step_results}

请用简洁的格式输出测试报告，不需要调用任何工具。"""

    def _check_step_result(self, messages: list, step: Any) -> bool:
        """检查最后的工具调用结果是否表示成功

        基本逻辑：检查最后一条 ToolMessage，如果内容不包含 error 关键词则认为成功。
        """
        from langchain_core.messages import ToolMessage

        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                content = str(msg.content).lower()
                error_keywords = ["error", "失败", "not found", "exception", "timeout"]
                return not any(kw in content for kw in error_keywords)
        # 没有 ToolMessage（比如 LLM 直接回复），视为成功
        return True

    def _check_verification(self, messages: list) -> bool:
        """检查验证点是否通过

        对于 "验证Toast包含xxx" 类型，检查 Toast 内容是否包含目标文本。
        """
        from langchain_core.messages import ToolMessage

        for verification in self._test_case.verifications:
            # 简单匹配：在最后的 ToolMessage 中查找验证文本
            for msg in reversed(messages):
                if isinstance(msg, ToolMessage):
                    if verification in str(msg.content):
                        return True
        return False

    def _generate_report(self, state: dict) -> str:
        """生成测试报告"""
        phase = state.get("test_phase", "unknown")
        passed = state.get("verification_passed", False)
        step_results = state.get("step_results", [])
        total = state.get("total_steps", 0)

        status = "✅ 通过" if passed else "❌ 失败"
        passed_count = sum(1 for s in step_results if s.get("passed"))

        lines = [
            f"# 测试报告: {self._test_case.name}",
            f"",
            f"**状态:** {status}",
            f"**通过步骤:** {passed_count}/{total}",
            f"",
            f"## 步骤详情",
        ]

        for sr in step_results:
            icon = "✅" if sr.get("passed") else "❌"
            lines.append(
                f"- {icon} 步骤 {sr['index'] + 1}: "
                f"{sr['action']} {sr.get('target', '')}"
            )

        if self._test_case.verifications:
            lines.append("")
            lines.append("## 验证点")
            for v in self._test_case.verifications:
                icon = "✅" if passed else "❌"
                lines.append(f"- {icon} {v}")

        return "\n".join(lines)
```

### Step 3: `prompts/test_prompt.py` — 步骤级 Prompt 模板

**职责：** 为每个测试步骤生成精确的 LLM 指令

```python
from __future__ import annotations

from mobile_agent.models.test_case import TestAction, TestCase, TestStep

# 动作 → MCP 工具调用指令模板
ACTION_PROMPT_MAP: dict[TestAction, str] = {
    TestAction.WAIT:
        "请调用 mobile_wait 工具，等待 {duration} 秒。参数: seconds={duration}",
    TestAction.CLOSE_POPUP:
        "请调用 mobile_close_popup 工具关闭当前页面的弹窗",
    TestAction.CLICK:
        "请调用 mobile_click_by_text 工具，点击文本为「{target}」的元素。参数: text=\"{target}\"",
    TestAction.INPUT_TEXT:
        "请调用 mobile_input_text 工具，在当前焦点输入框中输入「{text}」",
    TestAction.SWIPE:
        "请调用 mobile_swipe 工具，方向: {direction}",
    TestAction.START_TOAST_LISTENER:
        "请调用 mobile_start_toast_listener 工具，开始监听 Toast 消息",
    TestAction.VERIFY_TOAST:
        "请调用 mobile_get_toast 工具获取最近的 Toast 内容，然后验证其是否包含「{contains}」",
    TestAction.SCREENSHOT:
        "请调用 mobile_take_screenshot 工具截取当前屏幕",
    TestAction.ASSERT_ELEMENT:
        "请调用 mobile_list_elements 工具，验证页面中是否存在包含「{target}」的元素",
}


def build_step_prompt(
    step: TestStep,
    index: int,
    test_case: TestCase,
) -> str:
    """根据步骤类型生成精确的 MCP 工具调用指令"""
    template = ACTION_PROMPT_MAP.get(step.action, "请执行: {target}")
    instruction = template.format(
        target=step.target,
        **step.params,
    )

    return f"""你正在执行测试用例「{test_case.name}」。

## 当前进度: 第 {index + 1}/{len(test_case.steps)} 步

## 当前步骤
{step.action.value}: {step.target}

## 具体指令
{instruction}

## 规则
- 只执行当前步骤，不要跳步或提前执行后续步骤
- 只调用一次工具即可，不要重复调用
- 执行完后等待系统确认结果再继续
- 如果操作失败，报告错误原因"""


def build_test_system_prompt(test_case: TestCase) -> str:
    """构建测试执行专用的 system prompt"""
    steps_desc = "\n".join(
        f"  {s.index}. {s.action.value} {s.target}"
        for s in test_case.steps
    )

    return f"""你是一个移动端自动化测试执行 Agent。你正在执行以下测试用例：

测试名称: {test_case.name}
App包名: {test_case.app_package}
设备序列号: {test_case.device_serial}

测试步骤:
{steps_desc}

验证点: {', '.join(test_case.verifications)}

## 执行原则
1. 严格按步骤顺序执行，每次只执行系统指定的当前步骤
2. 每步只调用一次 MCP 工具
3. 优先使用 mobile_click_by_text 点击元素
4. 遇到弹窗优先调用 mobile_close_popup
5. 操作失败时如实报告，不要盲目重试"""
```

### Step 4: 修改 `core/agent_builder.py` — 新增测试 Agent 工厂方法

```python
# 在现有文件末尾新增

def build_test_agent(
    tools: list[BaseTool],
    llm_config: LLMConfig,
    test_case: TestCase,
    *,
    checkpointer: Any | None = None,
) -> Any:
    """构建测试执行专用 Agent

    Args:
        tools: MCP 工具列表
        llm_config: LLM 配置
        test_case: 解析后的测试用例
        checkpointer: 检查点保存器

    Returns:
        编译好的 Agent 实例
    """
    from mobile_agent.middleware.test_executor import TestExecutorMiddleware
    from mobile_agent.prompts.test_prompt import build_test_system_prompt

    # 测试专用中间件链
    middlewares = [
        TestExecutorMiddleware(test_case),   # 核心：状态机
        OperationLoggerMiddleware(),          # 操作日志
        RetryMiddleware(max_retries=1),       # 重试（测试场景减少次数）
    ]

    # 测试专用 system prompt
    system_prompt = build_test_system_prompt(test_case)

    if checkpointer is None:
        msg = "checkpointer 不能为 None"
        raise ValueError(msg)

    model_instance = _create_model_instance(llm_config)

    return create_agent(
        model=model_instance,
        tools=tools,
        system_prompt=system_prompt,
        middleware=middlewares,
        checkpointer=checkpointer,
    )
```

### Step 5: 修改 `core/service.py` — 新增测试执行入口

```python
# 在 MobileAgentService 类中新增方法

async def run_test_case(
    self,
    *,
    test_case_text: str,
    conversation_id: str,
) -> dict[str, Any]:
    """执行测试用例

    Args:
        test_case_text: 用户原始输入的测试用例文本
        conversation_id: 会话 ID

    Returns:
        测试结果字典
    """
    from mobile_agent.models.test_case import parse_test_case
    from mobile_agent.core.agent_builder import build_test_agent

    # 1. 解析测试用例
    test_case = parse_test_case(test_case_text)

    # 2. 构建测试 Agent
    tools = self._mcp_manager.tools if self._mcp_manager else []
    test_agent = build_test_agent(
        tools=tools,
        llm_config=self._settings.llm,
        test_case=test_case,
        checkpointer=self._checkpointer,
    )

    # 3. 执行
    initial_message = f"开始执行测试用例: {test_case.name}"
    config = {"configurable": {"thread_id": conversation_id}}
    result = await test_agent.ainvoke(
        {"messages": [HumanMessage(content=initial_message)]},
        config=config,
    )

    # 4. 提取测试结果
    return {
        "test_case": test_case.name,
        "phase": result.get("test_phase"),
        "passed": result.get("verification_passed", False),
        "step_results": result.get("step_results", []),
        "total_steps": len(test_case.steps),
    }
```

### Step 6: API 路由

```python
from pydantic import BaseModel

class RunTestRequest(BaseModel):
    test_case_text: str
    conversation_id: str | None = None

@router.post("/test/run")
async def run_test(request: RunTestRequest):
    """执行测试用例 API"""
    from uuid import uuid4

    service = get_agent_service()
    result = await service.run_test_case(
        test_case_text=request.test_case_text,
        conversation_id=request.conversation_id or str(uuid4()),
    )
    return result
```

---

## 五、关键设计决策

### 为什么用 `TestExecutorMiddleware` 而不是直接让 LLM 自由执行？

| 对比 | 自由执行 | 状态机中间件 |
|------|---------|-------------|
| **可控性** | LLM 可能跳步、重复 | 严格按步骤顺序 |
| **可观测性** | 难以追踪进度 | state 中有 step_index |
| **错误处理** | LLM 自行判断 | 中间件统一判断 pass/fail |
| **可复现性** | 不稳定 | 相同用例相同流程 |
| **Token 消耗** | 每轮需要完整上下文 | 只注入当前步骤 prompt |

### 中间件钩子分工

```
┌─────────────────────────────────────────────────────────┐
│  abefore_agent: 初始化 test_phase / current_step_index  │
│                 只执行一次                                │
├─────────────────────────────────────────────────────────┤
│  ┌─── Agent Loop ──────────────────────────────────┐    │
│  │  awrap_model_call:                               │    │
│  │    读取 current_step → 构建步骤 prompt           │    │
│  │    override system_message 精确引导 LLM          │    │
│  │                                                   │    │
│  │  [LLM 调用 → 生成工具调用]                       │    │
│  │                                                   │    │
│  │  wrap_tool_call (OperationLogger):               │    │
│  │    记录工具调用日志、发射 SSE 事件               │    │
│  │                                                   │    │
│  │  wrap_tool_call (Retry):                         │    │
│  │    工具失败时重试                                 │    │
│  │                                                   │    │
│  │  aafter_model (TestExecutor):                    │    │
│  │    检查工具结果 → 更新 step_results              │    │
│  │    推进 current_step_index                        │    │
│  │    判断是否进入 verifying / completed / failed    │    │
│  └──────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────┤
│  aafter_agent: 生成测试报告                              │
│                只执行一次                                │
└─────────────────────────────────────────────────────────┘
```

### Agent 退出条件

`aafter_model` 返回 `test_phase = "completed"` 或 `"failed"` 后，LLM 下一轮不会再有工具调用（因为 prompt 会告诉它测试已结束），自然走到 `END` 节点。

---

## 六、实施优先级

| 优先级 | 任务 | 文件 | 复杂度 |
|--------|------|------|--------|
| **P0** | 测试用例数据模型 + 解析器 | `models/test_case.py` | 中 |
| **P0** | 测试执行中间件（状态机核心） | `middleware/test_executor.py` | 高 |
| **P0** | 步骤级 Prompt 模板 | `prompts/test_prompt.py` | 中 |
| **P1** | 测试 Agent 工厂方法 | `core/agent_builder.py` | 低 |
| **P1** | Service 层测试执行入口 | `core/service.py` | 低 |
| **P2** | API 路由 | `api/routes.py` | 低 |
| **P2** | 前端测试执行 UI | `frontend/` | 中 |

建议按 P0 → P1 → P2 顺序实施。
