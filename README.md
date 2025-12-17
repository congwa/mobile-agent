# 📱 Mobile MCP AI

> 让 Cursor 直接控制手机的 MCP 工具

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/mobile-mcp-ai.svg?style=flat-square&color=blue)](https://pypi.org/project/mobile-mcp-ai/)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg?style=flat-square)](LICENSE)
[![Android](https://img.shields.io/badge/Android-支持-brightgreen.svg?style=flat-square&logo=android)](https://developer.android.com/)
[![iOS](https://img.shields.io/badge/iOS-支持-black.svg?style=flat-square&logo=apple)](docs/iOS_SETUP_GUIDE.md)

**⭐ 觉得有用？给个 Star 支持一下！**

**📱 支持 Android 和 iOS 双平台**

</div>

---

## 🎬 演示

<div align="center">

![演示动图](docs/videos/demo.gif)

*[查看高清视频 →](docs/videos/demo.mp4)*

</div>

---

## ✨ 核心特性

<table>
<tr>
<td width="50%">

### 🧠 AI 原生驱动

基于 MCP 协议与 Cursor AI 深度集成，自然语言直接操控手机，告别繁琐的脚本编写

</td>
<td width="50%">

### 👁️ 视觉智能识别

Cursor AI 自动分析截图，精准定位 UI 元素，游戏、原生应用通吃

</td>
</tr>
<tr>
<td width="50%">

### ⚡ 零配置启动

`pip install` 一行命令，开箱即用，无需额外 AI 密钥

</td>
<td width="50%">

### 🔄 一键生成脚本

操作即录制，自动生成可复用的 pytest 测试脚本

</td>
</tr>
<tr>
<td width="50%">

### 🎯 双模式定位

元素树 + 视觉坐标双引擎，普通 App 秒定位，游戏场景不迷路

</td>
<td width="50%">

### 🛡️ 智能验证机制

按键操作自动验证生效，告别"假成功"

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
| 📐 | `mobile_get_screen_size` | 屏幕尺寸 |
| 👆 | `mobile_click_by_text` | 文本点击 |
| 👆 | `mobile_click_by_id` | ID 点击 |
| 👆 | `mobile_click_at_coords` | 坐标点击 |
| ⌨️ | `mobile_input_text_by_id` | ID 输入 |
| ⌨️ | `mobile_input_at_coords` | 坐标输入 |
| 👆 | `mobile_swipe` | 滑动 |
| ⌨️ | `mobile_press_key` | 按键 |
| ⏱️ | `mobile_wait` | 等待 |
| 📦 | `mobile_launch_app` | 启动应用 |
| 📦 | `mobile_terminate_app` | 终止应用 |
| 📦 | `mobile_list_apps` | 列出应用 |
| 📱 | `mobile_list_devices` | 列出设备 |
| 🔌 | `mobile_check_connection` | 检查连接 |
| ✅ | `mobile_assert_text` | 断言文本 |
| 📜 | `mobile_get_operation_history` | 操作历史 |
| 🗑️ | `mobile_clear_operation_history` | 清空历史 |
| 📝 | `mobile_generate_test_script` | 生成测试脚本 |

---

## 📞 联系作者

<div align="center">

<img src="docs/images/wechat-qr.jpg" alt="微信" width="250"/>

*添加微信交流（备注：mobile-mcp）*

</div>

---

## 📄 License

Apache 2.0

---

<div align="center">

[Gitee](https://gitee.com/chang-xinping/mobile-automation-mcp-service) · [GitHub](https://github.com/test111ddff-hash/mobile-mcp-ai) · [PyPI](https://pypi.org/project/mobile-mcp-ai/)

**🚀 让移动端测试更简单**

</div>
