"""测试用例解析端点 - 预览结构化测试用例

测试执行通过 /api/v1/chat SSE 端点进行，
此模块仅提供解析预览功能。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/test", tags=["test"])


# ── 请求/响应模型 ────────────────────────────────────────


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
