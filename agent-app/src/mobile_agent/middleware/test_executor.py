"""测试执行状态机中间件

学习 Skill-Know 的 StatefulToolMiddleware 模式，
将用户提供的测试步骤编排为 state 中的状态序列。
Agent 每执行完一步就自动推进到下一步，直到验证点通过或失败。

状态机流转:
  SETUP → EXECUTING (step 0..N-1) → VERIFYING → COMPLETED / FAILED
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Annotated, Any, Literal

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    OmitFromInput,
    hook_config,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.runtime import Runtime
from typing_extensions import NotRequired

from mobile_agent.models.test_case import TestCase
from mobile_agent.models.tool_config import (
    ACTIONS_WITH_GROUP_FALLBACK,
    GROUP_PRIORITY,
    SETUP_ALLOWED_TOOLS,
    get_group_at_priority,
    get_max_priority_for_action,
    get_tools_for_step,
)
from mobile_agent.prompts.test_prompt import (
    build_report_prompt,
    build_setup_prompt,
    build_step_prompt,
)

logger = logging.getLogger(__name__)


# ── 测试阶段枚举 ────────────────────────────────────────

class TestPhase(str, Enum):
    """测试执行阶段"""
    IDLE = "idle"
    SETUP = "setup"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


# ── 状态 Schema ──────────────────────────────────────────

class TestExecutionState(AgentState[Any]):
    """测试执行状态 Schema -- 扩展 AgentState"""

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

    step_retry_count: Annotated[NotRequired[int], OmitFromInput]
    """当前步骤重试次数"""

    current_tool_priority_idx: Annotated[NotRequired[int], OmitFromInput]
    """当前步骤的工具优先级索引（0=最高优先级）"""


# ── 错误关键词 ───────────────────────────────────────────

_ERROR_KEYWORDS = ["error", "exception", "timeout", "not found"]


def _is_error_content(content: str) -> bool:
    """判断工具结果内容是否包含错误"""
    lower = content.lower()
    return any(kw in lower for kw in _ERROR_KEYWORDS)


# ── 中间件实现 ───────────────────────────────────────────

class TestExecutorMiddleware(AgentMiddleware):
    """测试执行状态机中间件

    钩子分工:
    - abefore_agent: 初始化测试状态（只执行一次）
    - awrap_model_call: 根据当前步骤构建精确 prompt
    - aafter_model: 检查工具结果、推进步骤
    - aafter_agent: 生成测试报告（只执行一次）
    """

    state_schema = TestExecutionState

    MAX_STEP_RETRIES = 2

    def __init__(self, test_case: TestCase) -> None:
        super().__init__()
        self._test_case = test_case

    # ── abefore_agent: 初始化 ────────────────────────

    async def abefore_agent(
        self, state: AgentState, runtime: Runtime,
    ) -> dict[str, Any]:
        """Agent 启动时初始化测试状态"""
        logger.info(
            "TestExecutor: 初始化测试 [%s], 共 %d 步",
            self._test_case.name,
            len(self._test_case.steps),
        )
        return {
            "test_phase": TestPhase.SETUP.value,
            "current_step_index": 0,
            "total_steps": len(self._test_case.steps),
            "step_results": [],
            "test_case_data": self._test_case.to_dict(),
            "verification_passed": False,
            "step_retry_count": 0,
        }

    # ── awrap_model_call: 步骤级 prompt 注入 ─────────

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """每轮 LLM 调用前：将步骤指令追加到原始 system prompt

        重要：不能替换原始 system_message，否则 LLM 会丢失工具使用上下文。
        使用 _combine_system_message 将步骤 prompt 追加到原始 prompt 后面。
        """
        state = request.state
        phase = state.get("test_phase", "idle")
        step_idx = state.get("current_step_index", 0)

        # 强制每轮只允许一个 tool_call（API 层面限制）
        no_parallel = {**request.model_settings, "parallel_tool_calls": False}

        if phase == TestPhase.SETUP.value:
            step_prompt = build_setup_prompt(self._test_case)
            combined = self._combine_system_message(request, step_prompt)

            # SETUP 工具集：从 tool_config.py 统一配置
            setup_tools = [
                t for t in request.tools
                if (getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else "")) in SETUP_ALLOWED_TOOLS
            ]

            overrides: dict[str, Any] = {
                "system_message": combined,
                "model_settings": no_parallel,
            }
            if setup_tools:
                overrides["tools"] = setup_tools

            updated = request.override(**overrides)
            final_names = [
                getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else "?")
                for t in updated.tools
            ]
            logger.info(
                "TestExecutor: [SETUP] 注入前置检查 prompt (工具: %s, 原始: %d)",
                final_names, len(request.tools),
            )
            return await handler(updated)

        if phase == TestPhase.EXECUTING.value and step_idx < len(self._test_case.steps):
            current_step = self._test_case.steps[step_idx]
            step_prompt = build_step_prompt(current_step, step_idx, self._test_case)
            combined = self._combine_system_message(request, step_prompt)

            # 基于交互范式的工具注入
            tool_priority_idx = state.get("current_tool_priority_idx", 0)
            action = current_step.action.value
            allowed_names = get_tools_for_step(action, tool_priority_idx)

            # 从 request.tools 中筛选允许的工具
            filtered_tools = [
                t for t in request.tools
                if (getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else "")) in allowed_names
            ]

            overrides_exec: dict[str, Any] = {
                "system_message": combined,
                "model_settings": no_parallel,
            }
            if filtered_tools:
                overrides_exec["tools"] = filtered_tools

            updated = request.override(**overrides_exec)

            # 日志
            group_name = get_group_at_priority(tool_priority_idx) if action in ACTIONS_WITH_GROUP_FALLBACK else "hint"
            injected_names = [
                getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else "?")
                for t in updated.tools
            ]
            logger.info(
                "TestExecutor: [EXECUTING] 步骤 %d/%d - %s「%s」\n"
                "  范式组: %s (优先级 %d/%d)\n"
                "  注入工具: %s (共 %d 个, 原始 %d 个)",
                step_idx + 1,
                len(self._test_case.steps),
                action,
                current_step.target or current_step.raw_text,
                group_name,
                tool_priority_idx,
                get_max_priority_for_action(action),
                injected_names,
                len(updated.tools),
                len(request.tools),
            )
            return await handler(updated)

        if phase == TestPhase.VERIFYING.value:
            # 验证阶段：LLM 只需分析已有工具结果，不允许调用新工具
            updated = request.override(
                tools=[], model_settings=no_parallel,
            )
            logger.info("TestExecutor: [VERIFYING] 工具清空，仅分析已有结果")
            return await handler(updated)

        if phase in (TestPhase.COMPLETED.value, TestPhase.FAILED.value):
            step_prompt = build_report_prompt(self._test_case, dict(state))
            combined = self._combine_system_message(request, step_prompt)
            updated = request.override(
                system_message=combined, tools=[], model_settings=no_parallel,
            )
            logger.info("TestExecutor: [%s] 注入报告生成 prompt (工具清空，仅生成文本)", phase.upper())
            return await handler(updated)

        return await handler(request.override(model_settings=no_parallel))

    def _combine_system_message(
        self, request: ModelRequest, step_prompt: str,
    ) -> SystemMessage:
        """将步骤 prompt 追加到原始 system prompt，保留工具使用上下文"""
        original = ""
        if hasattr(request, "system_message") and request.system_message:
            original = str(request.system_message.content)

        combined_content = f"{original}\n\n---\n\n# 当前执行指令\n\n{step_prompt}"
        return SystemMessage(content=combined_content)

    # ── aafter_model: 步骤推进 ───────────────────────

    @hook_config(can_jump_to=["model", "end"])
    async def aafter_model(
        self, state: AgentState, runtime: Runtime,
    ) -> dict[str, Any] | None:
        """LLM 调用后：检查工具调用结果，推进步骤

        关键理解：aafter_model 在工具执行**之前**运行。
        LangGraph 流程: model → aafter_model → tools_node → model

        策略：
        - LLM 产生 tool_calls → return None（让正常流程去 tools_node 执行工具）
        - LLM 无 tool_calls（工具已执行完的回合）→ 检查 ToolMessage，推进步骤
        """
        phase = state.get("test_phase")
        step_idx = state.get("current_step_index", 0)
        messages = state.get("messages", [])

        # 获取最后一条 AIMessage
        last_ai = self._get_last_ai_message(messages)

        # ── 同工具去重：LLM 可能对同一个工具发起多次并行调用，只保留每个工具的第一次
        if last_ai and getattr(last_ai, "tool_calls", None) and len(last_ai.tool_calls) > 1:
            seen: set[str] = set()
            deduped: list[dict] = []
            for tc in last_ai.tool_calls:
                name = tc.get("name", "")
                if name not in seen:
                    seen.add(name)
                    deduped.append(tc)
            if len(deduped) < len(last_ai.tool_calls):
                removed_count = len(last_ai.tool_calls) - len(deduped)
                logger.info(
                    "TestExecutor: 同工具去重: %d → %d (移除 %d 个重复调用, 保留: %s)",
                    len(last_ai.tool_calls), len(deduped), removed_count,
                    [tc.get("name") for tc in deduped],
                )
                last_ai.tool_calls = deduped
                if hasattr(last_ai, "additional_kwargs") and last_ai.additional_kwargs:
                    ak = last_ai.additional_kwargs
                    if "tool_calls" in ak:
                        ak_seen: set[str] = set()
                        ak_deduped = []
                        for tc in ak["tool_calls"]:
                            fname = tc.get("function", {}).get("name", "")
                            if fname not in ak_seen:
                                ak_seen.add(fname)
                                ak_deduped.append(tc)
                        ak["tool_calls"] = ak_deduped

        # ── SETUP: 前置条件检查（严格模式）────────────
        #
        # 策略：让 LLM 检查前置条件是否满足。
        # - 满足 → 进入 EXECUTING
        # - 不满足 → 直接 FAILED，不尝试修复
        if phase == TestPhase.SETUP.value:
            logger.info(
                "TestExecutor: [SETUP] 进入 aafter_model, 消息数: %d, "
                "last_ai: %s, has_tool_calls: %s",
                len(messages),
                type(last_ai).__name__ if last_ai else None,
                bool(last_ai and getattr(last_ai, "tool_calls", None)),
            )

            # 情况 1：LLM 发起了工具调用（检查设备状态等）→ 让工具执行
            if last_ai and getattr(last_ai, "tool_calls", None):
                logger.info(
                    "TestExecutor: [SETUP] LLM 调用了工具 %s，让工具执行",
                    [tc.get("name") for tc in last_ai.tool_calls],
                )
                return None  # → tools_node → 执行工具 → 回到 model

            # 情况 2：LLM 无 tool_calls → 检查工具结果判断前置条件
            # 在最近消息中查找 ToolMessage 和 AIMessage 的内容
            recent_types = [
                (type(m).__name__, str(getattr(m, 'content', ''))[:100])
                for m in messages[-10:]
            ]
            has_tool_msg = any(isinstance(m, ToolMessage) for m in messages[-10:])
            logger.info(
                "TestExecutor: [SETUP] 检查工具结果, has_tool_msg: %s\n"
                "  最近 %d 条消息类型: %s",
                has_tool_msg,
                min(10, len(messages)),
                recent_types,
            )

            if has_tool_msg:
                # 检查工具结果 + LLM 回复中是否明确表示前置条件不满足
                precondition_failed = self._check_precondition_failed(messages)
                logger.info(
                    "TestExecutor: [SETUP] _check_precondition_failed 结果: %s",
                    precondition_failed,
                )
                if precondition_failed:
                    logger.error(
                        "TestExecutor: 前置条件不满足 -> FAILED: %s",
                        precondition_failed,
                    )
                    return {
                        "test_phase": TestPhase.FAILED.value,
                        "step_results": [{
                            "index": -1,
                            "action": "precondition_check",
                            "target": "",
                            "raw_text": precondition_failed,
                            "passed": False,
                        }],
                        "jump_to": "end",
                    }

                # 前置条件满足，进入 EXECUTING
                first_step = self._test_case.steps[0]
                logger.info(
                    "TestExecutor: SETUP -> EXECUTING（前置条件已验证）\n"
                    "  前置条件: %s\n"
                    "  第一步: %s (工具: %s)",
                    self._test_case.preconditions,
                    first_step.raw_text,
                    first_step.mcp_tool_hint,
                )
                return {
                    "test_phase": TestPhase.EXECUTING.value,
                    "current_step_index": 0,
                    "step_retry_count": 0,
                    "jump_to": "model",
                    "messages": [HumanMessage(content=(
                        f"前置条件已满足。现在开始执行步骤 1: {first_step.raw_text}\n"
                        f"请立即调用 {first_step.mcp_tool_hint} 工具执行此操作。"
                    ))],
                }

            # 情况 3：LLM 既没调用工具也没有 ToolMessage
            setup_retry = state.get("step_retry_count", 0)
            if setup_retry >= self.MAX_STEP_RETRIES:
                # 重试耗尽，LLM 始终未调用工具检查 -> FAILED
                logger.error("TestExecutor: SETUP 重试耗尽，LLM 未执行前置检查 -> FAILED")
                return {
                    "test_phase": TestPhase.FAILED.value,
                    "step_results": [{
                        "index": -1,
                        "action": "precondition_check",
                        "target": "",
                        "raw_text": "无法执行前置条件检查（LLM 未调用工具）",
                        "passed": False,
                    }],
                    "jump_to": "end",
                }

            logger.info(
                "TestExecutor: [SETUP] LLM 未调用工具，提醒检查前置条件 (%d/%d)",
                setup_retry + 1, self.MAX_STEP_RETRIES,
            )
            return {
                "step_retry_count": setup_retry + 1,
                "jump_to": "model",
                "messages": [HumanMessage(content=(
                    "你必须调用 MCP 工具检查前置条件是否满足，不能只用文字回复。\n"
                    "请调用相应的 MCP 工具检查前置条件。"
                ))],
            }

        # ── EXECUTING ────────────────────────────────
        if phase == TestPhase.EXECUTING.value:
            if step_idx >= len(self._test_case.steps):
                return {
                    "test_phase": TestPhase.VERIFYING.value,
                    "jump_to": "model",
                    "messages": [HumanMessage(content="所有步骤已执行完毕。请进行验证。")],
                }

            step = self._test_case.steps[step_idx]
            action = step.action.value
            tool_priority_idx = state.get("current_tool_priority_idx", 0)
            max_priority = get_max_priority_for_action(action)

            # ── 情况 1：LLM 发起了工具调用 ──────────────
            if last_ai and getattr(last_ai, "tool_calls", None):
                group_name = get_group_at_priority(tool_priority_idx) if action in ACTIONS_WITH_GROUP_FALLBACK else "hint"
                logger.info(
                    "TestExecutor: 步骤 %d - LLM 调用工具 %s (范式: %s, 优先级 %d)，等待执行",
                    step_idx + 1,
                    [tc.get("name") for tc in last_ai.tool_calls],
                    group_name,
                    tool_priority_idx,
                )
                return None  # → tools_node → 执行工具 → 回到 model

            # ── 情况 2：LLM 无 tool_calls（工具已执行完的回合）──
            has_tool_result = self._check_step_result(messages, step)
            retry_count = state.get("step_retry_count", 0)

            if not has_tool_result:
                tool_error = self._get_last_tool_error(messages)

                if tool_error:
                    # 工具执行失败 → 尝试降级到下一交互范式组
                    if action in ACTIONS_WITH_GROUP_FALLBACK and tool_priority_idx + 1 < max_priority:
                        next_priority = tool_priority_idx + 1
                        current_group = get_group_at_priority(tool_priority_idx) or "?"
                        next_group = get_group_at_priority(next_priority) or "?"
                        logger.warning(
                            "TestExecutor: 步骤 %d [%s] 工具执行失败，范式降级\n"
                            "  错误: %s\n"
                            "  %s (优先级 %d) → %s (优先级 %d)",
                            step_idx + 1, action,
                            tool_error[:300],
                            current_group, tool_priority_idx,
                            next_group, next_priority,
                        )

                        if next_group == "som":
                            fallback_instruction = (
                                f"上一个工具执行失败: {tool_error[:200]}\n"
                                f"请改用 SoM 方式：先调用 mobile_screenshot_with_som 获取标注截图，"
                                f"然后根据截图中的编号调用 mobile_click_by_som 点击目标。\n"
                                f"目标: {step.raw_text}"
                            )
                        elif next_group == "coordinate":
                            fallback_instruction = (
                                f"上一个工具执行失败: {tool_error[:200]}\n"
                                f"请改用坐标方式：先调用 mobile_screenshot_with_grid 获取网格截图，"
                                f"然后通过坐标工具操作。\n"
                                f"目标: {step.raw_text}"
                            )
                        else:
                            fallback_instruction = (
                                f"上一个工具执行失败: {tool_error[:200]}\n"
                                f"请使用其他方式执行步骤 {step_idx + 1}: {step.raw_text}"
                            )
                        return {
                            "current_tool_priority_idx": next_priority,
                            "step_retry_count": 0,
                            "jump_to": "model",
                            "messages": [HumanMessage(content=fallback_instruction)],
                        }

                    # 无更多降级选项 → FAILED
                    logger.error(
                        "TestExecutor: 步骤 %d [%s] 所有范式组用尽 -> FAILED: %s",
                        step_idx + 1, action, tool_error[:200],
                    )
                    step_results = list(state.get("step_results", []))
                    step_results.append({
                        "index": step_idx,
                        "action": action,
                        "target": step.target,
                        "raw_text": step.raw_text,
                        "passed": False,
                    })
                    return {
                        "test_phase": TestPhase.FAILED.value,
                        "step_results": step_results,
                        "jump_to": "end",
                    }

                # LLM 未调用工具，尝试重试
                if retry_count < self.MAX_STEP_RETRIES:
                    logger.warning(
                        "TestExecutor: 步骤 %d [%s] LLM 未调用工具，重试 %d/%d",
                        step_idx + 1, action,
                        retry_count + 1, self.MAX_STEP_RETRIES,
                    )
                    return {
                        "step_retry_count": retry_count + 1,
                        "jump_to": "model",
                        "messages": [HumanMessage(content=(
                            f"你没有调用工具。请立即调用工具执行步骤 {step_idx + 1}: {step.raw_text}\n"
                            f"你必须发起实际的 tool_call，不能只用文字回复。只调用一个工具。"
                        ))],
                    }
                # 重试耗尽，失败
                logger.error(
                    "TestExecutor: 步骤 %d [%s] 重试 %d 次后仍未调用工具，失败",
                    step_idx + 1, action, self.MAX_STEP_RETRIES,
                )
                step_results = list(state.get("step_results", []))
                step_results.append({
                    "index": step_idx,
                    "action": action,
                    "target": step.target,
                    "raw_text": step.raw_text,
                    "passed": False,
                })
                return {
                    "test_phase": TestPhase.FAILED.value,
                    "step_results": step_results,
                    "jump_to": "end",
                }

            # ── 工具调用成功 → 推进步骤 ──────────────────
            step_results = list(state.get("step_results", []))
            step_results.append({
                "index": step_idx,
                "action": step.action.value,
                "target": step.target,
                "raw_text": step.raw_text,
                "passed": True,
            })

            logger.info(
                "TestExecutor: 步骤 %d [%s %s] -> PASSED",
                step_idx + 1, step.action.value, step.target,
            )

            next_idx = step_idx + 1
            if next_idx >= len(self._test_case.steps):
                logger.info("TestExecutor: 所有步骤执行完毕 -> VERIFYING")
                return {
                    "test_phase": TestPhase.VERIFYING.value,
                    "step_results": step_results,
                    "current_step_index": next_idx,
                    "step_retry_count": 0,
                    "current_tool_priority_idx": 0,
                    "jump_to": "model",
                    "messages": [HumanMessage(content="所有步骤已执行完毕。请进行最终验证。")],
                }

            # 推进到下一步（重置优先级索引）
            next_step = self._test_case.steps[next_idx]
            return {
                "current_step_index": next_idx,
                "step_results": step_results,
                "step_retry_count": 0,
                "current_tool_priority_idx": 0,
                "jump_to": "model",
                "messages": [HumanMessage(content=(
                    f"步骤 {step_idx + 1} 已完成。现在执行步骤 {next_idx + 1}: {next_step.raw_text}\n"
                    f"请立即调用 {next_step.mcp_tool_hint} 工具执行此操作。只调用一个工具。"
                ))],
            }

        # ── VERIFYING: 检查验证点 ───────────────────
        if phase == TestPhase.VERIFYING.value:
            passed = self._check_verification(messages)
            final_phase = (
                TestPhase.COMPLETED.value if passed
                else TestPhase.FAILED.value
            )
            logger.info(
                "TestExecutor: 验证 -> %s (passed=%s)",
                final_phase, passed,
            )
            return {
                "test_phase": final_phase,
                "verification_passed": passed,
                "jump_to": "end",
            }

        # COMPLETED / FAILED — 结束
        if phase in (TestPhase.COMPLETED.value, TestPhase.FAILED.value):
            return {"jump_to": "end"}

        return None

    @staticmethod
    def _get_last_ai_message(messages: list) -> AIMessage | None:
        """获取最后一条 AIMessage"""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return msg
        return None


    # ── aafter_agent: 测试报告 ───────────────────────

    async def aafter_agent(
        self, state: AgentState, runtime: Runtime,
    ) -> dict[str, Any] | None:
        """Agent 结束时：生成测试报告摘要"""
        report = self._generate_report(state)
        logger.info("TestExecutor: 生成测试报告")
        return {"messages": [AIMessage(content=report)]}

    # ── 内部辅助方法 ─────────────────────────────────

    def _check_step_result(self, messages: list, step: Any) -> bool:
        """检查最近的工具调用结果是否表示成功

        流程：model → tools_node(ToolMessage) → model(AIMessage)
        在 post-tool 的 aafter_model 中调用此方法时，消息顺序为：
          ... AIMessage(tool_calls) → ToolMessage → AIMessage(无 tool_calls)
        所以需要在最近消息中搜索 ToolMessage，不能被最新的 AIMessage 截断。

        规则：
        1. 最近 10 条消息中必须有 ToolMessage
        2. ToolMessage 内容不包含 error 关键词
        """
        recent = messages[-10:] if len(messages) > 10 else messages

        found_tool_message = False
        for msg in reversed(recent):
            if isinstance(msg, ToolMessage):
                content = str(msg.content)
                if _is_error_content(content):
                    logger.warning(
                        "TestExecutor: 工具返回错误: %s",
                        content[:200],
                    )
                    return False
                found_tool_message = True
                break

        if not found_tool_message:
            logger.warning(
                "TestExecutor: 步骤 %d [%s] 失败 - 未找到工具调用结果",
                step.index, step.action.value,
            )
            return False

        return True

    def _check_precondition_failed(self, messages: list) -> str | None:
        """检查前置条件是否不满足

        分析最近的 ToolMessage 和 AIMessage 内容，判断前置条件是否未满足。

        Returns:
            失败原因字符串（如果不满足），None 如果满足
        """
        recent = messages[-10:] if len(messages) > 10 else messages

        # 收集工具结果和 LLM 回复
        tool_contents: list[str] = []
        ai_contents: list[str] = []

        for msg in recent:
            if isinstance(msg, ToolMessage):
                tool_contents.append(str(msg.content))
            elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                ai_contents.append(str(msg.content))

        all_content = " ".join(tool_contents + ai_contents).lower()

        logger.info(
            "TestExecutor: [_check_precondition_failed] 分析数据:\n"
            "  前置条件列表: %s\n"
            "  App包名: %s\n"
            "  ToolMessage 数: %d, 内容摘要: %s\n"
            "  AIMessage 数: %d, 内容摘要: %s",
            self._test_case.preconditions,
            self._test_case.app_package,
            len(tool_contents),
            [c[:150] for c in tool_contents],
            len(ai_contents),
            [c[:150] for c in ai_contents],
        )

        # ── 优先级 1：LLM 明确判断 ────────────────────
        # SETUP prompt 要求 LLM 输出 "前置条件满足" 或 "前置条件不满足：原因"
        ai_text = " ".join(ai_contents).lower()

        fail_keywords = [
            "前置条件不满足", "不满足", "未满足", "not met",
            "precondition failed", "前置条件失败",
        ]
        matched_fail = [kw for kw in fail_keywords if kw in ai_text]
        if matched_fail:
            # 提取原因（取 LLM 最后一条消息的完整内容）
            reason = ai_contents[-1][:300] if ai_contents else str(matched_fail)
            logger.info(
                "TestExecutor: [_check_precondition_failed] LLM 明确判断不满足: %s",
                matched_fail,
            )
            return f"前置条件不满足（LLM 判断）: {reason}"

        pass_keywords = ["前置条件满足", "precondition met", "preconditions met"]
        if any(kw in ai_text for kw in pass_keywords):
            # LLM 明确说满足 → 检查是否有"不"字在前面（避免误判）
            if not matched_fail:
                logger.info("TestExecutor: [_check_precondition_failed] LLM 明确判断满足")
                return None

        # ── 优先级 2：工具结果关键词检测（兜底）────────
        tool_combined = " ".join(c.lower() for c in tool_contents)

        for precondition in self._test_case.preconditions:
            pre_lower = precondition.lower()

            # 「App 处于关闭状态」
            if "关闭" in pre_lower or "关闭状态" in pre_lower:
                # 检查 1：包名出现在工具输出中
                pkg = self._test_case.app_package.lower()
                pkg_found = pkg and pkg in tool_combined
                logger.info(
                    "TestExecutor: [_check_precondition_failed] 检查「%s」:\n"
                    "  包名检查: pkg='%s', found_in_tool_output=%s",
                    precondition, pkg, pkg_found,
                )
                if pkg_found:
                    return f"前置条件「{precondition}」不满足：检测到 {self._test_case.app_package} 正在前台运行"

                # 检查 2：运行状态关键词
                running_indicators = [
                    "running", "foreground", "正在运行", "已启动",
                    "is running", "already running", "活动中",
                ]
                matched_indicators = [ind for ind in running_indicators if ind in all_content]
                if matched_indicators:
                    logger.info(
                        "TestExecutor: [_check_precondition_failed] 运行关键词匹配: %s",
                        matched_indicators,
                    )
                    return f"前置条件「{precondition}」不满足：App 正在运行 (匹配: {matched_indicators})"

            # 「App 已打开」
            if "已打开" in pre_lower or "打开状态" in pre_lower:
                not_running_indicators = [
                    "not running", "not found", "未运行", "未启动",
                    "stopped", "已停止",
                ]
                matched = [ind for ind in not_running_indicators if ind in all_content]
                if matched:
                    logger.info(
                        "TestExecutor: [_check_precondition_failed] 未运行关键词匹配: %s",
                        matched,
                    )
                    return f"前置条件「{precondition}」不满足：App 未运行 (匹配: {matched})"

        logger.info("TestExecutor: [_check_precondition_failed] 所有检查通过（关键词兜底未命中）")
        return None

    def _get_last_tool_error(self, messages: list) -> str | None:
        """获取最近一条 ToolMessage 中的错误内容

        Returns:
            错误描述字符串（如果有错误），None 如果无错误
        """
        recent = messages[-10:] if len(messages) > 10 else messages

        for msg in reversed(recent):
            if isinstance(msg, ToolMessage):
                content = str(msg.content)
                if _is_error_content(content):
                    return content[:500]
                break  # 只检查最近一条 ToolMessage

        return None

    def _check_verification(self, messages: list) -> bool:
        """检查验证点是否通过

        对于 "验证Toast包含xxx" 类型，在最后的消息中查找验证文本。
        """
        if not self._test_case.verifications:
            # 没有验证点，直接通过
            return True

        # 收集最近的消息内容（包括 ToolMessage 和 AIMessage）
        recent_contents: list[str] = []
        for msg in messages[-10:]:
            if isinstance(msg, (ToolMessage, AIMessage)):
                recent_contents.append(str(getattr(msg, "content", "")))

        combined = " ".join(recent_contents)

        for verification_text in self._test_case.verifications:
            if verification_text in combined:
                return True

        return False

    def _generate_report(self, state: dict) -> str:
        """生成测试报告"""
        phase = state.get("test_phase", "unknown")
        passed = state.get("verification_passed", False)
        step_results = state.get("step_results", [])
        total = state.get("total_steps", 0)

        status_icon = "PASS" if passed else "FAIL"
        passed_count = sum(1 for s in step_results if s.get("passed"))

        lines = [
            f"# 测试报告: {self._test_case.name}",
            "",
            f"**状态:** {status_icon}",
            f"**通过步骤:** {passed_count}/{total}",
            "",
            "## 步骤详情",
        ]

        for sr in step_results:
            icon = "PASS" if sr.get("passed") else "FAIL"
            lines.append(
                f"- [{icon}] 步骤 {sr['index'] + 1}: "
                f"{sr.get('raw_text', sr['action'] + ' ' + sr.get('target', ''))}"
            )

        if self._test_case.verifications:
            lines.append("")
            lines.append("## 验证点")
            for v in self._test_case.verifications:
                icon = "PASS" if passed else "FAIL"
                lines.append(f"- [{icon}] {v}")

        return "\n".join(lines)
