"""MCP 工具配置中心

集中管理所有工具的分类、优先级和阶段限制。
修改此文件即可调整工具策略，无需改动业务代码。

架构：按交互范式分组，每次 LLM 交互只注入一个范式的工具集 + 通用工具。
降级时切换到下一个范式组，而非同范式内的其他工具。
"""

from __future__ import annotations


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 交互范式工具组
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 每个组是一个完整的交互范式，组内工具配合使用。
# key: 组名
# value: 该组包含的 MCP 工具名列表
TOOL_GROUPS: dict[str, list[str]] = {
    # 元素定位范式：通过 list_elements 获取元素信息，再通过 text/id 操作
    # token 低、速度快、最稳定
    "elements": [
        "mobile_list_elements",
        "mobile_click_by_text",
        "mobile_click_by_id",
        "mobile_input_text_by_id",
        "mobile_long_press_by_text",
        "mobile_long_press_by_id",
    ],

    # SoM 视觉范式：先截图标注元素编号，再通过编号操作
    # 适合无文本/ID 的元素
    "som": [
        "mobile_screenshot_with_som",
        "mobile_click_by_som",
    ],

    # 坐标定位范式：通过网格截图确定坐标，再通过坐标/百分比操作
    # 最后手段
    "coordinate": [
        "mobile_screenshot_with_grid",
        "mobile_click_by_percent",
        "mobile_click_at_coords",
        "mobile_input_at_coords",
        "mobile_long_press_by_percent",
        "mobile_long_press_at_coords",
    ],
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 组降级优先级（从高到低）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 执行时先注入 index=0 的组，失败后降级到 index=1，以此类推。
GROUP_PRIORITY: list[str] = ["elements", "som", "coordinate"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 通用工具（始终注入）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 功能性工具，不属于任何交互范式，每次 LLM 交互都可用。
# 会根据当前步骤动作自动过滤（如 click 步骤不注入 swipe）。
UTILITY_TOOLS: set[str] = {
    "mobile_wait",
    "mobile_launch_app",
    "mobile_terminate_app",
    "mobile_swipe",
    "mobile_press_key",
    "mobile_hide_keyboard",
    "mobile_close_popup",
    "mobile_close_ad",
    "mobile_find_close_button",
    "mobile_template_close",
    "mobile_assert_text",
    "mobile_start_toast_watch",
    "mobile_get_toast",
    "mobile_assert_toast",
    "mobile_take_screenshot",
    "mobile_get_screen_size",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. SETUP 阶段允许的工具
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SETUP_ALLOWED_TOOLS: set[str] = {
    "mobile_list_elements",
    "mobile_list_devices",
    "mobile_list_apps",
    "mobile_terminate_app",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 动作 → 默认工具映射 (mcp_tool_hint)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTION_TOOL_HINT: dict[str, str] = {
    "wait":                 "mobile_wait",
    "close_popup":          "mobile_close_popup",
    "close_ad":             "mobile_close_ad",
    "click":                "mobile_click_by_text",
    "click_by_id":          "mobile_click_by_id",
    "input_text":           "mobile_input_text_by_id",
    "swipe":                "mobile_swipe",
    "swipe_up":             "mobile_swipe",
    "swipe_down":           "mobile_swipe",
    "start_toast_listener": "mobile_start_toast_watch",
    "verify_toast":         "mobile_get_toast",
    "screenshot":           "mobile_take_screenshot",
    "list_elements":        "mobile_list_elements",
    "assert_element":       "mobile_list_elements",
    "back":                 "mobile_press_key",
    "home":                 "mobile_press_key",
    "launch_app":           "mobile_launch_app",
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. 需要范式降级的动作（交互类动作）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 这些动作类型支持 elements → som → coordinate 降级。
# 不在此列的动作（如 wait, launch_app）只使用 mcp_tool_hint 对应的工具。
ACTIONS_WITH_GROUP_FALLBACK: set[str] = {
    "click",
    "click_by_id",
    "input_text",
    "long_press",
    "assert_element",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工具查询函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_group_tools(group_name: str) -> list[str]:
    """获取指定组的工具列表"""
    return TOOL_GROUPS.get(group_name, [])


def get_group_at_priority(priority_idx: int) -> str | None:
    """获取指定优先级索引对应的组名"""
    if 0 <= priority_idx < len(GROUP_PRIORITY):
        return GROUP_PRIORITY[priority_idx]
    return None


def get_tools_for_step(action: str, priority_idx: int) -> set[str]:
    """获取指定步骤在指定优先级下应注入的全部工具名

    返回: 范式组工具 + 通用工具（如果是交互类动作）
          或 mcp_tool_hint 对应工具 + 通用工具（如果是功能类动作）
    """
    if action in ACTIONS_WITH_GROUP_FALLBACK:
        group_name = get_group_at_priority(priority_idx)
        if group_name:
            tools = set(get_group_tools(group_name))
        else:
            tools = set(get_group_tools(GROUP_PRIORITY[-1]))
        tools |= UTILITY_TOOLS
        return tools

    hint = ACTION_TOOL_HINT.get(action, "")
    if hint:
        return {hint}
    return set()


def get_max_priority_for_action(action: str) -> int:
    """获取指定动作的最大优先级索引"""
    if action in ACTIONS_WITH_GROUP_FALLBACK:
        return len(GROUP_PRIORITY)
    return 1


# ── 向后兼容（test_case.py 使用）──────────────────────

def get_tool_priority_chain(action: str) -> list[list[str]]:
    """兼容旧接口：返回组名列表作为降级链"""
    if action in ACTIONS_WITH_GROUP_FALLBACK:
        return [get_group_tools(g) for g in GROUP_PRIORITY]
    return []


def get_all_priority_tools(action: str) -> set[str]:
    """获取指定动作的所有可能工具名"""
    if action in ACTIONS_WITH_GROUP_FALLBACK:
        tools: set[str] = set()
        for g in GROUP_PRIORITY:
            tools.update(get_group_tools(g))
        return tools
    hint = ACTION_TOOL_HINT.get(action, "")
    return {hint} if hint else set()


def get_tool_hint(action: str) -> str:
    """获取动作的默认工具提示"""
    return ACTION_TOOL_HINT.get(action, "")
