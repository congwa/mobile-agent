# 📱 Mobile MCP Agent

> 移动端 AI 自动化测试平台 —— MCP 工具 + AI Agent + 可视化操控台

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/mobile-mcp-ai.svg?style=flat-square&color=blue)](https://pypi.org/project/mobile-mcp-ai/)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg?style=flat-square)](LICENSE)
[![Android](https://img.shields.io/badge/Android-支持-brightgreen.svg?style=flat-square&logo=android)](https://developer.android.com/)
[![iOS](https://img.shields.io/badge/iOS-支持-black.svg?style=flat-square&logo=apple)](docs/iOS_SETUP_GUIDE.md)

**⭐ 觉得有用？给个 Star 支持一下！**

**📱 支持 Android 和 iOS 双平台**

</div>

### 项目包含三个层次

| 层次 | 说明 | 技术栈 |
|:---:|------|------|
| **MCP Server** | 39 个移动端自动化工具，可独立配合 Cursor / Claude 使用 | Python · MCP 协议 · PyPI 发布 |
| **AI Agent** | 智能测试执行引擎，自动编排工具调用、范式降级、结果验证 | LangChain · LangGraph |
| **Electron 操控台** | 可视化界面，设备预览、测试流程编排、实时操作日志 | Electron · React · TailwindCSS |

---

## 🎬 演示

<div align="center">

![演示动图](docs/videos/demo.gif)

*[查看高清视频 →](docs/videos/demo.mp4)*

</div>

<div align="center">

![软件运行效果](images/agent1.png)

*Agent 自动化测试执行效果*

</div>

---

## ✨ 核心特性

<table>
<tr>
<td width="50%">

### 🧠 AI Agent 智能执行

基于 LangChain + LangGraph 的测试 Agent，自动编排工具调用，按步骤执行测试用例

</td>
<td width="50%">

### � 三范式自动降级

元素交互 → SoM 视觉 → 坐标定位，逐级降级，确保操作成功率

</td>
</tr>
<tr>
<td width="50%">

### 🖥️ 可视化操控台

Electron 桌面应用，设备实时预览、测试流程编排、操作日志时间轴

</td>
<td width="50%">

### � MCP 工具独立可用

39 个工具通过 `pip install mobile-mcp-ai` 安装，可直接配合 Cursor / Claude 使用

</td>
</tr>
<tr>
<td width="50%">

### 🎯 双平台支持

Android + iOS 双平台，元素树 + 视觉坐标双引擎

</td>
<td width="50%">

### 🛡️ 智能验证机制

操作结果自动验证，前置条件检查，测试报告自动生成

</td>
</tr>
</table>

---

## 📱 平台支持

| 平台 | 支持状态 | 系统要求 | 配置指南 |
|:---:|:---:|:---:|:---:|
| **Android** | ✅ 完整支持 | Windows / macOS / Linux | 开箱即用 |
| **iOS** | ✅ 完整支持 | macOS（必须） | [iOS 配置指南 →](docs/iOS_SETUP_GUIDE.md) |

---

## 📦 安装

```bash
pip install mobile-mcp-ai
```

**升级到最新版**

```bash
pip install --upgrade mobile-mcp-ai
```

**查看当前版本**

```bash
pip show mobile-mcp-ai
```

---

## 📱 连接设备

### Android 设备

确保手机已开启 USB 调试，然后：

```bash
adb devices
```

看到设备列表即表示连接成功。

### iOS 设备（macOS）

iOS 自动化需要额外配置 WebDriverAgent，请参考：

📖 **[iOS 配置指南 →](docs/iOS_SETUP_GUIDE.md)**

快速检查连接：
```bash
tidevice list
```

---

## 🎯 新用户快速入门

### 第一步：安装

```bash
pip install mobile-mcp-ai
```

### 第二步：连接设备

**Android 用户：**
```bash
# 开启手机 USB 调试，连接电脑
adb devices
```

**iOS 用户：**
```bash
# 安装依赖
pip install tidevice facebook-wda
brew install libimobiledevice

# 检查连接
tidevice list
```

> 📖 iOS 需要额外配置 WebDriverAgent，详见 **[iOS 配置指南](docs/iOS_SETUP_GUIDE.md)**

### 第三步：配置 Cursor

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

> 💡 提示：会自动检测 Android/iOS 设备，无需额外配置

### 第四步：重启 Cursor

保存配置后，**重启 Cursor** 使配置生效。

### 第五步：开始使用

在 Cursor 中输入：

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

### 方式一：pip 安装后配置（推荐）

先安装：`pip install mobile-mcp-ai`

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "mobile-mcp"
    }
  }
}
```

### 方式二：源码方式配置

如果你是从源码运行：

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
> 
> 📖 iOS 需要先配置 WebDriverAgent，详见 **[iOS 配置指南](docs/iOS_SETUP_GUIDE.md)**

保存后**重启 Cursor**。

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

在 Cursor 中直接对话：

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

## 📞 联系作者

<div align="center">

<img src="images/qq.jpg" alt="QQ交流群" width="250"/>

*扫码加入 QQ 交流群（群号：1080722489）*

</div>

---

## � 致谢

本项目的 MCP 工具部分 fork 自 [mobile-mcp](https://gitee.com/chang-xinping/mobile-mcp) 项目，感谢原作者的开源贡献！

## �� License

Apache 2.0

---

<div align="center">

[Gitee](https://gitee.com/cong_wa/mobile-mcp) · [GitHub](https://github.com/congwa/mobile-agent) · [PyPI](https://pypi.org/project/mobile-mcp-ai/)

**🚀 让移动端测试更简单**

</div>
