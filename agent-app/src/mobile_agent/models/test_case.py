"""测试用例数据模型 + 解析器

将用户输入的结构化测试用例文本解析为 TestCase 对象，
供 TestExecutorMiddleware 驱动执行。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TestAction(str, Enum):
    """测试动作类型 → 对应 MCP 工具"""
    WAIT = "wait"                              # → mobile_wait
    CLOSE_POPUP = "close_popup"                # → mobile_close_popup
    CLOSE_AD = "close_ad"                      # → mobile_close_ad
    CLICK = "click"                            # → mobile_click_by_text
    CLICK_BY_ID = "click_by_id"                # → mobile_click_by_id
    INPUT_TEXT = "input_text"                   # → mobile_input_text
    SWIPE = "swipe"                            # → mobile_swipe
    SWIPE_UP = "swipe_up"                      # → mobile_swipe direction=up
    SWIPE_DOWN = "swipe_down"                  # → mobile_swipe direction=down
    START_TOAST_LISTENER = "start_toast_listener"  # → mobile_start_toast_listener
    VERIFY_TOAST = "verify_toast"              # → mobile_get_toast
    SCREENSHOT = "screenshot"                  # → mobile_take_screenshot
    LIST_ELEMENTS = "list_elements"            # → mobile_list_elements
    ASSERT_ELEMENT = "assert_element"          # 验证元素存在
    BACK = "back"                              # → mobile_press_back
    HOME = "home"                              # → mobile_press_home
    LAUNCH_APP = "launch_app"                  # → mobile_launch_app


# 工具配置已迁移至 tool_config.py，统一管理
from mobile_agent.models.tool_config import (  # noqa: E402
    get_all_priority_tools,
    get_tool_priority_chain,
)


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
    index: int                                  # 步骤序号 (1-based)
    action: TestAction                          # 动作类型
    raw_text: str = ""                          # 原始步骤文本
    target: str = ""                            # 操作目标 ("我的", "设置")
    params: dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: str = ""                            # 执行结果描述
    mcp_tool_hint: str = ""                     # 对应的 MCP 工具名提示
    tool_fallback_chain: list[list[str]] = field(default_factory=list)  # 工具优先级降级链

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "action": self.action.value,
            "raw_text": self.raw_text,
            "target": self.target,
            "params": self.params,
            "status": self.status.value,
            "result": self.result,
            "mcp_tool_hint": self.mcp_tool_hint,
        }


@dataclass
class TestCase:
    """测试用例"""
    name: str                                   # 测试任务名称
    preconditions: list[str]                    # 前置条件
    steps: list[TestStep]                       # 测试步骤列表
    verifications: list[str]                    # 验证点
    app_package: str = ""                       # com.qiyi.video.lite
    device_serial: str = ""                     # 4XWW6XFAA6OJIBJB

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "preconditions": self.preconditions,
            "steps": [s.to_dict() for s in self.steps],
            "verifications": self.verifications,
            "app_package": self.app_package,
            "device_serial": self.device_serial,
        }


# ── 步骤解析规则 ────────────────────────────────────────

# 引号字符集：匹配中英文引号
_QUOTE_OPEN = '[\'"“「]'
_QUOTE_CLOSE = '[\'"”」]'


def _re_quote_wrap(inner: str) -> str:
    """生成匹配引号包裹内容的正则"""
    return _QUOTE_OPEN + inner + _QUOTE_CLOSE


# (正则, TestAction, 提取参数的 lambda)
_STEP_PATTERNS: list[tuple[re.Pattern[str], TestAction, Any]] = [
    # 等待N秒
    (
        re.compile(r"等待\s*(\d+(?:\.\d+)?)\s*秒"),
        TestAction.WAIT,
        lambda m: {"target": "", "params": {"duration": float(m.group(1))}, "mcp_tool_hint": "mobile_wait"},
    ),
    # 关闭广告
    (
        re.compile(r"关闭广告"),
        TestAction.CLOSE_AD,
        lambda m: {"target": "", "params": {}, "mcp_tool_hint": "mobile_close_ad"},
    ),
    # 关闭弹窗
    (
        re.compile(r"关闭弹窗"),
        TestAction.CLOSE_POPUP,
        lambda m: {"target": "", "params": {}, "mcp_tool_hint": "mobile_close_popup"},
    ),
    # 开始监听Toast
    (
        re.compile(r"开始监听\s*[Tt]oast"),
        TestAction.START_TOAST_LISTENER,
        lambda m: {"target": "", "params": {}, "mcp_tool_hint": "mobile_start_toast_listener"},
    ),
    # 验证Toast包含"xxx"
    (
        re.compile(r"验证\s*[Tt]oast\s*包含\s*" + _QUOTE_OPEN + r"(.+?)" + _QUOTE_CLOSE),
        TestAction.VERIFY_TOAST,
        lambda m: {"target": "", "params": {"contains": m.group(1)}, "mcp_tool_hint": "mobile_get_toast"},
    ),
    # 截图 / 截屏
    (
        re.compile(r"截[图屏]"),
        TestAction.SCREENSHOT,
        lambda m: {"target": "", "params": {}, "mcp_tool_hint": "mobile_take_screenshot"},
    ),
    # 返回
    (
        re.compile(r"^返回$|按返回键|点击返回"),
        TestAction.BACK,
        lambda m: {"target": "", "params": {}, "mcp_tool_hint": "mobile_press_back"},
    ),
    # 回到桌面
    (
        re.compile(r"回到桌面|按Home键"),
        TestAction.HOME,
        lambda m: {"target": "", "params": {}, "mcp_tool_hint": "mobile_press_home"},
    ),
    # 上滑 / 下滑
    (
        re.compile(r"上滑|向上滑动"),
        TestAction.SWIPE_UP,
        lambda m: {"target": "", "params": {"direction": "up"}, "mcp_tool_hint": "mobile_swipe"},
    ),
    (
        re.compile(r"下滑|向下滑动"),
        TestAction.SWIPE_DOWN,
        lambda m: {"target": "", "params": {"direction": "down"}, "mcp_tool_hint": "mobile_swipe"},
    ),
    # 输入"xxx"
    (
        re.compile(r"输入\s*" + _QUOTE_OPEN + r"(.+?)" + _QUOTE_CLOSE),
        TestAction.INPUT_TEXT,
        lambda m: {"target": m.group(1), "params": {"text": m.group(1)}, "mcp_tool_hint": "mobile_input_text"},
    ),
    # 启动App / 打开App
    (
        re.compile(r"(?:启动|打开)\s*[Aa]pp"),
        TestAction.LAUNCH_APP,
        lambda m: {"target": "", "params": {}, "mcp_tool_hint": "mobile_launch_app"},
    ),
    # 查看元素 / 获取元素
    (
        re.compile(r"(?:查看|获取|列出)元素"),
        TestAction.LIST_ELEMENTS,
        lambda m: {"target": "", "params": {}, "mcp_tool_hint": "mobile_list_elements"},
    ),
    # 验证元素存在"xxx"
    (
        re.compile(r"验证.*?(?:存在|显示|出现)\s*" + _QUOTE_OPEN + r"(.+?)" + _QUOTE_CLOSE),
        TestAction.ASSERT_ELEMENT,
        lambda m: {"target": m.group(1), "params": {"element_text": m.group(1)}, "mcp_tool_hint": "mobile_list_elements"},
    ),
    # 通过ID点击
    (
        re.compile(r"(?:通过|使用)\s*[Ii][Dd]\s*点击\s*" + _QUOTE_OPEN + r"(.+?)" + _QUOTE_CLOSE),
        TestAction.CLICK_BY_ID,
        lambda m: {"target": m.group(1), "params": {"resource_id": m.group(1)}, "mcp_tool_hint": "mobile_click_by_id"},
    ),
    # 点击xxx（通用匹配，放最后）
    (
        re.compile(r"点击\s*(.+)"),
        TestAction.CLICK,
        lambda m: {"target": m.group(1).strip(), "params": {}, "mcp_tool_hint": "mobile_click_by_text"},
    ),
]


def _parse_step(index: int, raw_text: str) -> TestStep:
    """解析单个步骤文本为 TestStep"""
    text = raw_text.strip()

    for pattern, action, extractor in _STEP_PATTERNS:
        match = pattern.search(text)
        if match:
            info = extractor(match)
            return TestStep(
                index=index,
                action=action,
                raw_text=text,
                target=info.get("target", ""),
                params=info.get("params", {}),
                mcp_tool_hint=info.get("mcp_tool_hint", ""),
                tool_fallback_chain=get_tool_priority_chain(action.value),
            )

    # 未匹配到任何模式，默认作为点击操作
    return TestStep(
        index=index,
        action=TestAction.CLICK,
        raw_text=text,
        target=text,
        params={},
        mcp_tool_hint="mobile_click_by_text",
        tool_fallback_chain=get_tool_priority_chain("click"),
    )


def parse_test_case(raw_text: str) -> TestCase:
    """将用户输入文本解析为 TestCase

    支持的输入格式（tab 分隔）：
    ```
    测试任务名称：切换账号\t
    前置条件：App已安装,用户已登录\t
    测试步骤：
    1. 等待2秒
    2. 关闭弹窗
    3. 点击我的
    ...
    验证点：Toast提示"账号切换成功"\t是\t\tcom.qiyi.video.lite\t4XWW6XFAA6OJIBJB
    ```

    也支持纯文本逐行解析。
    """
    # 标准化换行
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    name = ""
    preconditions: list[str] = []
    step_texts: list[str] = []
    verifications: list[str] = []
    app_package = ""
    device_serial = ""

    # 尝试提取测试任务名称
    name_match = re.search(r"测试任务名称[：:]\s*(.+?)[\t\n]", text)
    if name_match:
        name = name_match.group(1).strip()

    # 提取前置条件
    pre_match = re.search(r"前置条件[：:]\s*(.+?)[\t\n]", text)
    if pre_match:
        raw_pre = pre_match.group(1).strip()
        preconditions = [p.strip() for p in re.split(r"[,，;；]", raw_pre) if p.strip()]

    # 提取测试步骤（行首数字编号，使用 MULTILINE 锚定行头防止匹配 com.im30.way 中的 30.way）
    step_pattern = re.compile(r"^\s*(\d+)\.\s*(.+)", re.MULTILINE)
    for match in step_pattern.finditer(text):
        step_texts.append(match.group(2).strip())

    # 提取验证点
    verify_match = re.search(r"验证点[：:]\s*(.+?)(?:\t|$)", text)
    if verify_match:
        raw_verify = verify_match.group(1).strip()
        verifications = [v.strip() for v in re.split(r"[,，;；]", raw_verify) if v.strip()]

    # 提取包名（com.xxx.xxx 格式）
    pkg_match = re.search(r"(com\.\S+?)(?:\t|\s|$)", text)
    if pkg_match:
        app_package = pkg_match.group(1).strip()

    # 提取设备序列号（tab 分隔的最后一个非空字段，或者明确的序列号模式）
    serial_match = re.search(r"\t([A-Z0-9]{10,})\s*$", text)
    if serial_match:
        device_serial = serial_match.group(1).strip()
    else:
        # 尝试匹配行末的设备序列号
        serial_match2 = re.search(r"([A-Z0-9]{10,})\s*$", text)
        if serial_match2:
            candidate = serial_match2.group(1).strip()
            # 排除包名
            if not candidate.startswith("com."):
                device_serial = candidate

    # 如果没有提取到步骤，尝试按行解析
    if not step_texts:
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = step_pattern.match(line)
            if m:
                step_texts.append(m.group(2).strip())

    # 解析每个步骤文本为 TestStep
    steps = [_parse_step(i + 1, t) for i, t in enumerate(step_texts)]

    # 如果验证点中有 Toast 相关的验证，补充解析
    parsed_verifications: list[str] = []
    for v in verifications:
        # 提取引号中的内容
        quote_match = re.search(_QUOTE_OPEN + r"(.+?)" + _QUOTE_CLOSE, v)
        if quote_match:
            parsed_verifications.append(quote_match.group(1))
        else:
            parsed_verifications.append(v)

    return TestCase(
        name=name or "未命名测试",
        preconditions=preconditions,
        steps=steps,
        verifications=parsed_verifications,
        app_package=app_package,
        device_serial=device_serial,
    )
