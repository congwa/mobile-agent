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

        if phase == TestPhase.SETUP.value:
            step_prompt = build_setup_prompt(self._test_case)
            combined = self._combine_system_message(request, step_prompt)
            updated = request.override(system_message=combined)
            logger.info("TestExecutor: [SETUP] 注入前置检查 prompt")
            return await handler(updated)

        if phase == TestPhase.EXECUTING.value and step_idx < len(self._test_case.steps):
            current_step = self._test_case.steps[step_idx]
            step_prompt = build_step_prompt(current_step, step_idx, self._test_case)
            combined = self._combine_system_message(request, step_prompt)
            updated = request.override(system_message=combined)
            logger.info(
                "TestExecutor: [EXECUTING] 步骤 %d/%d - %s %s",
                step_idx + 1,
                len(self._test_case.steps),
                current_step.action.value,
                current_step.target,
            )
            return await handler(updated)

        if phase in (TestPhase.COMPLETED.value, TestPhase.FAILED.value):
            step_prompt = build_report_prompt(self._test_case, dict(state))
            combined = self._combine_system_message(request, step_prompt)
            updated = request.override(system_message=combined)
            logger.info("TestExecutor: [%s] 注入报告生成 prompt", phase.upper())
            return await handler(updated)

        return await handler(request)

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

        # ── SETUP → EXECUTING ────────────────────────
        if phase == TestPhase.SETUP.value:
            first_step = self._test_case.steps[0]
            logger.info("TestExecutor: SETUP -> EXECUTING")
            return {
                "test_phase": TestPhase.EXECUTING.value,
                "current_step_index": 0,
                "jump_to": "model",
                "messages": [HumanMessage(content=(
                    f"前置检查完成。现在开始执行步骤 1: {first_step.raw_text}\n"
                    f"请立即调用 {first_step.mcp_tool_hint} 工具执行此操作。"
                ))],
            }

        # ── EXECUTING ────────────────────────────────
        if phase == TestPhase.EXECUTING.value:
            # 情况 1：LLM 刚发起了工具调用 → 让正常流程执行工具
            if last_ai and getattr(last_ai, "tool_calls", None):
                logger.info(
                    "TestExecutor: 步骤 %d - LLM 调用了工具 %s，等待执行",
                    step_idx + 1,
                    [tc.get("name") for tc in last_ai.tool_calls],
                )
                return None  # 正常流程：→ tools_node → 执行工具 → 回到 model

            # 情况 2：LLM 无 tool_calls
            # 可能是：(a) 工具已执行完的后续回合  (b) LLM 未调用工具
            if step_idx >= len(self._test_case.steps):
                return {
                    "test_phase": TestPhase.VERIFYING.value,
                    "jump_to": "model",
                    "messages": [HumanMessage(content="所有步骤已执行完毕。请进行验证。")],
                }

            step = self._test_case.steps[step_idx]
            has_tool_result = self._check_step_result(messages, step)
            retry_count = state.get("step_retry_count", 0)

            if not has_tool_result:
                # LLM 未调用工具，尝试重试
                if retry_count < self.MAX_STEP_RETRIES:
                    logger.warning(
                        "TestExecutor: 步骤 %d [%s] LLM 未调用工具，重试 %d/%d",
                        step_idx + 1, step.action.value,
                        retry_count + 1, self.MAX_STEP_RETRIES,
                    )
                    return {
                        "step_retry_count": retry_count + 1,
                        "jump_to": "model",
                        "messages": [HumanMessage(content=(
                            f"你没有调用工具。请立即调用 {step.mcp_tool_hint} 工具执行步骤 {step_idx + 1}: {step.raw_text}\n"
                            f"你必须发起实际的 tool_call，不能只用文字回复。"
                        ))],
                    }
                # 重试耗尽，失败
                logger.error(
                    "TestExecutor: 步骤 %d [%s] 重试 %d 次后仍未调用工具，失败",
                    step_idx + 1, step.action.value, self.MAX_STEP_RETRIES,
                )
                step_results = list(state.get("step_results", []))
                step_results.append({
                    "index": step_idx,
                    "action": step.action.value,
                    "target": step.target,
                    "raw_text": step.raw_text,
                    "passed": False,
                })
                return {
                    "test_phase": TestPhase.FAILED.value,
                    "step_results": step_results,
                    "jump_to": "end",
                }

            # 工具调用成功，记录结果
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
                    "jump_to": "model",
                    "messages": [HumanMessage(content="所有步骤已执行完毕。请进行最终验证。")],
                }

            # 推进到下一步
            next_step = self._test_case.steps[next_idx]
            return {
                "current_step_index": next_idx,
                "step_results": step_results,
                "step_retry_count": 0,
                "jump_to": "model",
                "messages": [HumanMessage(content=(
                    f"步骤 {step_idx + 1} 已完成。现在执行步骤 {next_idx + 1}: {next_step.raw_text}\n"
                    f"请立即调用 {next_step.mcp_tool_hint} 工具执行此操作。"
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
