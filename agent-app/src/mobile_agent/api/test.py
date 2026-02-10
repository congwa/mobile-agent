"""测试执行端点 - 执行结构化测试用例"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mobile_agent.core.service import get_agent_service

router = APIRouter(prefix="/api/v1/test", tags=["test"])


# ── 请求/响应模型 ────────────────────────────────────────


class RunTestRequest(BaseModel):
    """执行测试用例请求"""

    test_case_text: str = Field(..., description="测试用例原始文本")
    conversation_id: str = Field(default="", description="会话 ID（为空则自动生成）")


class StepResultItem(BaseModel):
    """步骤执行结果"""

    index: int
    action: str
    target: str = ""
    raw_text: str = ""
    passed: bool


class RunTestResponse(BaseModel):
    """执行测试用例响应"""

    test_case: str = Field(..., description="测试用例名称")
    phase: str = Field(..., description="最终阶段: completed / failed")
    passed: bool = Field(..., description="测试是否通过")
    step_results: list[StepResultItem] = Field(default_factory=list)
    total_steps: int = 0
    conversation_id: str = ""


class ParseTestRequest(BaseModel):
    """解析测试用例请求（预览，不执行）"""

    test_case_text: str = Field(..., description="测试用例原始文本")


class ParsedStepItem(BaseModel):
    """解析后的步骤"""

    index: int
    action: str
    target: str = ""
    params: dict = Field(default_factory=dict)
    mcp_tool_hint: str = ""
    raw_text: str = ""


class ParseTestResponse(BaseModel):
    """解析测试用例响应"""

    name: str
    preconditions: list[str]
    steps: list[ParsedStepItem]
    verifications: list[str]
    app_package: str = ""
    device_serial: str = ""


# ── 端点 ─────────────────────────────────────────────────


@router.post("/parse", response_model=ParseTestResponse)
async def parse_test(request_data: ParseTestRequest):
    """解析测试用例（预览，不执行）

    将用户输入的测试用例文本解析为结构化数据，
    可用于前端预览和确认后再执行。
    """
    from mobile_agent.models.test_case import parse_test_case

    try:
        test_case = parse_test_case(request_data.test_case_text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"测试用例解析失败: {e}")

    return ParseTestResponse(
        name=test_case.name,
        preconditions=test_case.preconditions,
        steps=[
            ParsedStepItem(
                index=s.index,
                action=s.action.value,
                target=s.target,
                params=s.params,
                mcp_tool_hint=s.mcp_tool_hint,
                raw_text=s.raw_text,
            )
            for s in test_case.steps
        ],
        verifications=test_case.verifications,
        app_package=test_case.app_package,
        device_serial=test_case.device_serial,
    )


@router.post("/run", response_model=RunTestResponse)
async def run_test(request_data: RunTestRequest):
    """执行测试用例

    解析测试用例文本，构建测试 Agent，逐步执行每个步骤，
    返回最终测试结果。
    """
    service = get_agent_service()
    if not service.is_ready:
        raise HTTPException(status_code=503, detail="Agent 服务未就绪，请稍后重试")

    conversation_id = request_data.conversation_id or str(uuid.uuid4())

    try:
        result = await service.run_test_case(
            test_case_text=request_data.test_case_text,
            conversation_id=conversation_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试执行失败: {e}")

    return RunTestResponse(
        test_case=result["test_case"],
        phase=result.get("phase", "unknown"),
        passed=result.get("passed", False),
        step_results=[
            StepResultItem(**sr) for sr in result.get("step_results", [])
        ],
        total_steps=result.get("total_steps", 0),
        conversation_id=conversation_id,
    )
