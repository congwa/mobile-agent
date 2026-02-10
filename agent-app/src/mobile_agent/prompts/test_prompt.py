"""测试执行专用 Prompt 模板

为每个测试步骤生成精确的 LLM 指令，引导 Agent 调用正确的 MCP 工具。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mobile_agent.models.test_case import TestAction, TestCase, TestStep


# 动作 → MCP 工具调用指令模板
# 模板中可用变量: {target}, {duration}, {text}, {direction}, {contains},
#                  {resource_id}, {element_text}
_ACTION_PROMPT_MAP: dict[str, str] = {
    "wait": (
        "请调用 mobile_wait 工具，等待 {duration} 秒。"
        "\n参数: seconds={duration}"
    ),
    "close_popup": (
        "请调用 mobile_close_popup 工具关闭当前页面的弹窗。"
        "\n如果没有弹窗，直接回复「无弹窗」即可。"
    ),
    "close_ad": (
        "请调用 mobile_close_ad 工具关闭当前页面的广告。"
    ),
    "click": (
        "请调用 mobile_click_by_text 工具，点击文本为「{target}」的元素。"
        '\n参数: text="{target}"'
    ),
    "click_by_id": (
        "请调用 mobile_click_by_id 工具，通过 resource-id 点击元素。"
        '\n参数: resource_id="{resource_id}"'
    ),
    "input_text": (
        "请调用 mobile_input_text 工具，在当前焦点输入框中输入文本。"
        '\n参数: text="{text}"'
    ),
    "swipe": (
        "请调用 mobile_swipe 工具进行滑动操作。"
        "\n参数: direction={direction}"
    ),
    "swipe_up": (
        "请调用 mobile_swipe 工具向上滑动。"
        '\n参数: direction="up"'
    ),
    "swipe_down": (
        "请调用 mobile_swipe 工具向下滑动。"
        '\n参数: direction="down"'
    ),
    "start_toast_listener": (
        "请调用 mobile_start_toast_listener 工具，开始监听 Toast 消息。"
        "\n这将在后台捕获后续的 Toast 弹窗内容。"
    ),
    "verify_toast": (
        "请调用 mobile_get_toast 工具获取最近的 Toast 内容。"
        "\n获取后验证其是否包含「{contains}」。"
        "\n如果包含，回复「验证通过」；如果不包含，回复「验证失败: 实际内容为 xxx」。"
    ),
    "screenshot": (
        "请调用 mobile_take_screenshot 工具截取当前屏幕截图。"
    ),
    "list_elements": (
        "请调用 mobile_list_elements 工具获取当前页面所有可交互元素。"
    ),
    "assert_element": (
        "请调用 mobile_list_elements 工具获取当前页面元素列表，"
        "然后验证是否存在包含「{element_text}」的元素。"
        "\n如果存在，回复「验证通过」；如果不存在，回复「验证失败: 未找到目标元素」。"
    ),
    "back": (
        "请调用 mobile_press_back 工具，按返回键。"
    ),
    "home": (
        "请调用 mobile_press_home 工具，回到桌面。"
    ),
    "launch_app": (
        "请调用 mobile_launch_app 工具启动应用。"
    ),
}


def build_step_prompt(
    step: TestStep,
    index: int,
    test_case: TestCase,
) -> str:
    """根据步骤类型生成精确的 MCP 工具调用指令

    Args:
        step: 当前测试步骤
        index: 步骤索引 (0-based)
        test_case: 完整测试用例

    Returns:
        构建好的 prompt 字符串
    """
    template = _ACTION_PROMPT_MAP.get(step.action.value, "请执行: {target}")

    # 合并所有可用的模板变量
    format_vars = {
        "target": step.target,
        **step.params,
    }

    try:
        instruction = template.format(**format_vars)
    except KeyError:
        # 模板变量缺失时，使用原始文本
        instruction = f"请执行操作: {step.raw_text}"

    total = len(test_case.steps)
    progress_bar = _build_progress_bar(index, total)

    return f"""你正在执行测试用例「{test_case.name}」。

## 进度: {progress_bar} ({index + 1}/{total})

## 当前步骤 (第 {index + 1} 步)
{step.raw_text}

## 具体指令
{instruction}

## 规则（必须严格遵守）
- **你必须调用上述指定的 MCP 工具**，不能只用文字描述操作，必须实际发起 tool_call
- 只执行当前步骤，不要跳步或提前执行后续步骤
- 只调用一次工具即可，不要重复调用
- 执行完后等待系统确认结果再继续
- 如果操作失败，如实报告错误原因，不要自行重试
- 禁止回复类似"我已完成"而不调用工具的情况"""


def build_test_system_prompt(test_case: TestCase) -> str:
    """构建测试执行专用的 system prompt

    Args:
        test_case: 完整测试用例

    Returns:
        system prompt 字符串
    """
    steps_desc = "\n".join(
        f"  {s.index}. {s.raw_text}" for s in test_case.steps
    )

    verifications_desc = "\n".join(
        f"  - {v}" for v in test_case.verifications
    )

    return f"""你是一个移动端自动化测试执行 Agent。你通过 MCP 工具控制真实的手机设备，按步骤执行测试用例。

## 测试用例信息
- 测试名称: {test_case.name}
- App包名: {test_case.app_package}
- 设备序列号: {test_case.device_serial}

## 测试步骤
{steps_desc}

## 验证点
{verifications_desc}

## 执行原则
1. **严格按步骤顺序执行** — 每次只执行系统指定的当前步骤
2. **每步只调用一次 MCP 工具** — 不要在一步中调用多个工具
3. **优先使用 mobile_click_by_text** — 通过文本精确匹配点击元素
4. **遇到弹窗优先关闭** — 调用 mobile_close_popup
5. **操作失败如实报告** — 不要盲目重试，等待系统决策

## 点击优先级
1. mobile_click_by_text — 最推荐，通过文本精确匹配
2. mobile_click_by_id — resource-id 精确匹配
3. mobile_click_by_som — 配合 SoM 截图，通过编号点击
4. mobile_click_by_percent — 百分比坐标，最后手段"""


def build_setup_prompt(test_case: TestCase) -> str:
    """构建前置检查 prompt

    Args:
        test_case: 完整测试用例

    Returns:
        前置检查 prompt 字符串
    """
    preconditions = "\n".join(
        f"  - {p}" for p in test_case.preconditions
    )

    return f"""你正在准备执行测试用例「{test_case.name}」。

## 前置条件
{preconditions}

## 设备信息
- App包名: {test_case.app_package}
- 设备序列号: {test_case.device_serial}

## 任务
请确认设备已连接，App 已安装并处于正确状态。
你可以调用 mobile_list_devices 检查设备状态。
确认就绪后，回复「前置检查完成」即可开始测试。"""


def build_report_prompt(
    test_case: TestCase,
    state: dict,
) -> str:
    """构建测试报告生成 prompt

    Args:
        test_case: 完整测试用例
        state: Agent 当前状态

    Returns:
        报告生成 prompt 字符串
    """
    phase = state.get("test_phase", "unknown")
    passed = state.get("verification_passed", False)
    step_results = state.get("step_results", [])

    results_desc = "\n".join(
        f"  - 步骤 {sr['index'] + 1}: {sr['action']} {sr.get('target', '')} → {'通过' if sr.get('passed') else '失败'}"
        for sr in step_results
    )

    return f"""测试已结束。请生成简洁的测试报告。

## 测试信息
- 测试用例: {test_case.name}
- 最终状态: {phase}
- 验证通过: {passed}

## 步骤执行结果
{results_desc}

## 要求
请用简洁格式输出测试报告，不需要调用任何工具。"""


def _build_progress_bar(current: int, total: int) -> str:
    """构建进度条字符串"""
    filled = current
    remaining = total - current - 1
    current_marker = 1
    return "[" + "=" * filled + ">" + "·" * remaining + "]"
