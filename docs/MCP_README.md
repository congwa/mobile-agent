# 📱 Mobile MCP — 移动端自动化 MCP 工具

> 39 个移动端自动化工具，配合 Cursor / Claude / Windsurf 等 AI IDE 使用

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/mobile-mcp-ai.svg?style=flat-square&color=blue)](https://pypi.org/project/mobile-mcp-ai/)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg?style=flat-square)](../LICENSE)

[English](MCP_README_EN.md) · [返回主项目](../README.md)

</div>

---

## 📖 这是什么？

Mobile MCP 是一个通过 MCP（Model Context Protocol）协议提供移动端自动化能力的工具集。安装后可在支持 MCP 的 AI IDE（如 Cursor、Claude Desktop、Windsurf）中直接控制手机。

**无需 Agent、无需 Electron 操控台**，一个 pip 命令即可使用。

---

## 🚀 快速开始

### 第一步：安装

```bash
pip install mobile-mcp-ai
```

升级到最新版：

```bash
pip install --upgrade mobile-mcp-ai
```

查看当前版本：

```bash
pip show mobile-mcp-ai
```

### 第二步：连接设备

**Android 用户：**

1. 手机开启「USB 调试」（设置 → 开发者选项 → USB 调试）
2. 用数据线连接电脑
3. 验证连接：

```bash
adb devices
```

看到设备列表即连接成功。

**iOS 用户：**

```bash
# 安装依赖
pip install tidevice facebook-wda
brew install libimobiledevice

# 检查连接
tidevice list
```

> 📖 iOS 需要额外配置 WebDriverAgent，详见 [iOS 配置指南](iOS_SETUP_GUIDE.md)

### 第三步：配置 AI IDE

#### Cursor 配置

编辑 `~/.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "mobile-mcp"
    }
  }
}
```

#### Claude Desktop 配置

编辑 Claude Desktop 配置文件：

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "mobile-mcp"
    }
  }
}
```

#### Windsurf 配置

编辑 `~/.windsurf/mcp.json`：

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "mobile-mcp"
    }
  }
}
```

> 💡 所有 IDE 配置后都需要**重启**使配置生效
>
> 💡 会自动检测 Android/iOS 设备，无需额外配置

### 第四步：开始使用

重启 IDE 后，在对话中输入：

```
@MCP 检查设备连接
```

```
@MCP 截图看看当前页面
```

```
@MCP 点击"登录"按钮
```

---

## ⚙️ 高级配置

### 源码方式运行

如果你从源码运行而非 pip 安装：

**Android 配置：**

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "mobile_mcp.mcp_tools.mcp_server"],
      "cwd": "/path/to/mobile_mcp",
      "env": {
        "MOBILE_PLATFORM": "android"
      }
    }
  }
}
```

**iOS 配置：**

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "mobile_mcp.mcp_tools.mcp_server"],
      "cwd": "/path/to/mobile_mcp",
      "env": {
        "MOBILE_PLATFORM": "ios"
      }
    }
  }
}
```

> ⚠️ 请将 `/path/to/` 替换为你的实际路径

### 环境变量配置

可在项目根目录创建 `.env` 文件进行更多配置，参考 `env.example`：

```bash
# 平台类型（不设置则自动检测）
# MOBILE_PLATFORM=android

# 调试模式
# MOBILE_MCP_DEBUG=0

# AI 提供商（可选，基础工具不需要）
# AI_PROVIDER=qwen
# QWEN_API_KEY=your-key

# 日志级别
# LOG_LEVEL=INFO
```

### 批量执行用例（飞书集成）

如果你需要从飞书多维表格批量执行用例，`mobile_open_new_chat` 功能会自动打开新会话继续执行。

**macOS 用户：** 需要开启辅助功能权限

| 步骤 | 操作 |
|:---:|------|
| 1 | 打开「系统设置」 |
| 2 | 点击「隐私与安全性」 |
| 3 | 点击「辅助功能」 |
| 4 | 点击 + 号，添加 **Cursor.app** |
| 5 | 确保开关已打开 ✅ |

> ⚠️ 没有此权限，无法自动打开新会话继续执行

**Windows 用户：** 需要安装额外依赖

```bash
pip install mobile-mcp-ai[windows]
```

或手动安装：

```bash
pip install pyautogui pyperclip pygetwindow
```

---

## 🚀 使用示例

在 AI IDE 中直接对话：

**基础操作**

```
@MCP 列出当前页面所有元素
```

```
@MCP 点击"登录"按钮
```

```
@MCP 在用户名输入框输入 test123
```

**应用控制**

```
@MCP 启动微信
```

```
@MCP 打开抖音，向上滑动 3 次
```

```
@MCP 列出手机上所有已安装的应用
```

**截图分析**

```
@MCP 截图看看当前页面
```

```
@MCP 截图，然后点击页面上的搜索图标
```

**测试脚本生成**

```
@MCP 帮我测试登录流程：输入用户名密码，点击登录
```

```
@MCP 把刚才的操作生成 pytest 测试脚本
```

**组合操作**

```
@MCP 打开设置，找到 WLAN，点进去截图
```

```
@MCP 打开微信，点击发现，再点击朋友圈
```

---

## 🛠️ 工具列表

| 类别 | 工具 | 说明 |
|:---:|------|------|
| 📋 | `mobile_list_elements` | 列出页面元素 |
| 📸 | `mobile_take_screenshot` | 截图 |
| 📸 | `mobile_screenshot_with_som` | Set-of-Mark 截图（智能标注） |
| 📸 | `mobile_screenshot_with_grid` | 带网格坐标的截图 |
| 📐 | `mobile_get_screen_size` | 屏幕尺寸 |
| 👆 | `mobile_click_by_text` | 文本点击 |
| 👆 | `mobile_click_by_id` | ID 点击 |
| 👆 | `mobile_click_at_coords` | 坐标点击 |
| 👆 | `mobile_click_by_percent` | 百分比点击 |
| 👆 | `mobile_click_by_som` | SoM 编号点击 |
| 👆 | `mobile_long_press_by_id` | ID 长按 |
| 👆 | `mobile_long_press_by_text` | 文本长按 |
| 👆 | `mobile_long_press_by_percent` | 百分比长按 |
| 👆 | `mobile_long_press_at_coords` | 坐标长按 |
| ⌨️ | `mobile_input_text_by_id` | ID 输入 |
| ⌨️ | `mobile_input_at_coords` | 坐标输入 |
| 👆 | `mobile_swipe` | 滑动 |
| ⌨️ | `mobile_press_key` | 按键 |
| ⏱️ | `mobile_wait` | 等待 |
| ⌨️ | `mobile_hide_keyboard` | 收起键盘（登录场景必备） |
| 📦 | `mobile_launch_app` | 启动应用 |
| 📦 | `mobile_terminate_app` | 终止应用 |
| 📦 | `mobile_list_apps` | 列出应用 |
| 📱 | `mobile_list_devices` | 列出设备 |
| 🔌 | `mobile_check_connection` | 检查连接 |
| 🔍 | `mobile_find_close_button` | 查找关闭按钮 |
| 🚫 | `mobile_close_popup` | 关闭弹窗 |
| 🚫 | `mobile_close_ad` | 智能关闭广告弹窗 |
| 🎯 | `mobile_template_close` | 模板匹配关闭弹窗 |
| ➕ | `mobile_template_add` | 添加 X 号模板 |
| ✅ | `mobile_assert_text` | 断言文本 |
| 📜 | `mobile_get_operation_history` | 操作历史 |
| 🗑️ | `mobile_clear_operation_history` | 清空历史 |
| 📝 | `mobile_generate_test_script` | 生成测试脚本 |

---

## ❓ 常见问题

### Q: 安装后 Cursor 里看不到 MCP 工具？

1. 确认 `~/.cursor/mcp.json` 配置正确
2. **重启 Cursor**（不是重新加载窗口，是完全退出再打开）
3. 在 Cursor 设置中检查 MCP 服务是否显示为已连接

### Q: 提示找不到设备？

- **Android**: 确认 `adb devices` 能看到设备
- **iOS**: 确认 `tidevice list` 能看到设备
- 确认手机已开启 USB 调试 / 信任电脑

### Q: 点击操作不生效？

1. 先用 `@MCP 截图` 确认当前页面状态
2. 用 `@MCP 列出页面元素` 查看可操作的元素
3. 尝试不同的点击方式（文本、ID、坐标）

### Q: iOS 连接失败？

请参考 [iOS 配置指南](iOS_SETUP_GUIDE.md)，确保 WebDriverAgent 已正确安装和运行。

---

## 📞 联系

<div align="center">

<img src="../images/qq.jpg" alt="QQ交流群" width="250"/>

*扫码加入 QQ 交流群（群号：1080722489）*

</div>

---

## 📄 License

Apache 2.0
