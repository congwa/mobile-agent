# Mobile MCP AI

移动端自动化 MCP Server - 为 Cursor AI 提供移动设备控制能力，支持 Android/iOS

<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/mobile-mcp-ai.svg)](https://pypi.org/project/mobile-mcp-ai/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Gitee Stars](https://gitee.com/chang-xinping/mobile-automation-mcp-service/badge/star.svg?theme=white)](https://gitee.com/chang-xinping/mobile-automation-mcp-service)

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！⭐**

**🆕 v2.0.0 重大更新：AI 功能可选化！基础工具不需要配置 AI 密钥**

</div>

## ✨ v2.0.0 核心特性

### 🎯 AI 功能可选化（重大更新）
- **基础模式**：不需要配置 AI 密钥，Cursor AI 提供所有智能能力
- **智能模式**：可选配置 AI 密钥，适合构建自动化测试平台
- **零成本起步**：基础工具完全免费，无需额外 AI API 费用
- **灵活选择**：根据使用场景自由选择是否启用 AI 功能

### 📦 双层工具架构

#### 基础工具（9个，不需要 AI）
- `mobile_list_elements` - 列出所有可交互元素
- `mobile_click_by_id` - 通过 resource-id 精确点击
- `mobile_click_by_text` - 通过文本内容点击
- `mobile_click_at_coords` - 点击指定坐标
- `mobile_input_text_by_id` - 在输入框输入文本
- `mobile_find_elements_by_class` - 按类名查找元素
- `mobile_wait_for_element` - 等待元素出现
- `mobile_take_screenshot` - 截取屏幕（支持 Cursor AI 视觉识别）
- `mobile_take_screenshot_region` - 区域截图

#### 智能工具（4个，需要 AI，可选）
- `mobile_smart_click` - 自然语言智能点击
- `mobile_smart_input` - 自然语言智能输入
- `mobile_analyze_screenshot` - AI 视觉识别定位
- `mobile_get_ai_status` - 检查 AI 功能状态

#### 通用工具（4个）
- `mobile_snapshot` - 获取页面结构
- `mobile_launch_app` - 启动应用
- `mobile_swipe` - 滑动屏幕
- `mobile_press_key` - 按键操作

### 🌐 跨平台支持
- **双平台支持**：完美支持 Android 和 iOS
- **统一接口**：通过适配器模式实现代码复用
- **设备管理**：自动检测和管理连接的设备

### 🤖 与 Cursor AI 深度集成
- **MCP 协议**：基于 Model Context Protocol，无缝集成
- **17 个工具**：丰富的移动端操作工具
- **视觉识别**：Cursor AI 可以直接分析截图并操作

## 📦 安装

### 基础安装（推荐）
```bash
# 不需要 AI 密钥，完全免费
pip install mobile-mcp-ai
```

### 完整安装（可选）
```bash
# 如果需要智能工具或构建自动化平台
pip install mobile-mcp-ai[ai]
```

## 🚀 快速开始

### 1. 配置 Cursor MCP

编辑 `~/.cursor/mcp.json`（macOS/Linux）或 `%APPDATA%\Cursor\mcp.json`（Windows）：

**基础模式（推荐新手，不需要 AI 密钥）**：
```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "python", //当前项目python路径
      "args": ["-m", "mobile_mcp.mcp.mcp_server_simple"],
      "env": {}
    }
  }
}
```

**智能模式（可选，需要 AI 密钥）**：
```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "python",
      "args": ["-m", "mobile_mcp.mcp.mcp_server_simple"],
      "env": {
        "AI_PROVIDER": "qwen",
        "QWEN_API_KEY": "sk-your-api-key"
      }
    }
  }
}
```

> 💡 **提示**：基础模式下，Cursor AI 本身就能提供所有智能能力（包括视觉识别），无需额外配置 AI 密钥！

详细配置说明：[用户配置指南](docs/USER_CONFIGURATION_GUIDE.md)

### 2. 连接设备

```bash
# Android 设备
adb devices  # 确认设备可见

# iOS 设备（可选）
pip install mobile-mcp-ai[ios]
```

### 3. 重启 Cursor

配置完成后，**完全退出**并重新启动 Cursor。

### 4. 开始使用

#### 方式1：基础工具（明确指定元素）
```
@MCP 帮我测试登录：
1. 列出所有元素
2. 点击 resource-id 为 "com.app:id/login_btn"
3. 在 resource-id "com.app:id/username" 输入 "admin"
4. 截图保存
```

#### 方式2：让 Cursor AI 分析截图（推荐）
```
@MCP 帮我测试登录：
1. 先截图看看当前页面
2. 分析后点击"登录"按钮
3. 在"用户名"输入框输入 "admin"
4. 截图确认
```

Cursor AI 会自动截图、分析图片、找到元素坐标并操作！

## 💡 使用示例

### 场景1：基础工具测试（明确元素）
```
@MCP 执行以下操作：
1. 启动应用 com.example.app
2. 列出所有可点击元素
3. 点击 resource-id "com.example:id/login_btn"
4. 等待元素 "com.example:id/home" 出现
5. 截图保存
```

### 场景2：Cursor AI 视觉分析（智能推荐）
```
@MCP 帮我测试登录功能：
1. 截图看看当前页面
2. 找到并点击"登录"按钮
3. 再截图，找到"用户名"输入框并输入 "test123"
4. 找到"密码"输入框并输入 "pass123"
5. 点击"确定"按钮
6. 截图确认结果
```

### 场景3：智能工具（需要配置 AI）
```
@MCP 检查 AI 功能状态
@MCP 用智能方式点击"登录"按钮
@MCP 在"用户名"输入框输入 "test123"
```

## 🛠️ 工具列表

### 基础工具（不需要 AI，共 9 个）
| 工具 | 说明 | 示例 |
|------|------|------|
| `mobile_list_elements` | 列出所有可交互元素 | 显示 resource_id, text, bounds |
| `mobile_click_by_id` | 通过 resource-id 点击 | 精确可靠 |
| `mobile_click_by_text` | 通过文本点击 | 文本完全匹配 |
| `mobile_click_at_coords` | 点击坐标 | 配合截图分析使用 |
| `mobile_input_text_by_id` | 输入文本 | 通过 resource-id |
| `mobile_find_elements_by_class` | 按类名查找 | 如 EditText |
| `mobile_wait_for_element` | 等待元素出现 | 等待页面加载 |
| `mobile_take_screenshot` | 截屏 | 供 Cursor AI 视觉识别 |
| `mobile_take_screenshot_region` | 区域截屏 | 局部分析 |

### 智能工具（需要 AI，可选，共 4 个）
| 工具 | 说明 | 使用场景 |
|------|------|----------|
| `mobile_smart_click` | 自然语言点击 | 平台自动化 |
| `mobile_smart_input` | 自然语言输入 | 批量测试 |
| `mobile_analyze_screenshot` | AI 分析截图 | 复杂场景 |
| `mobile_get_ai_status` | 检查 AI 状态 | 调试配置 |

### 通用工具（共 4 个）
| 工具 | 说明 |
|------|------|
| `mobile_snapshot` | 获取页面结构 |
| `mobile_launch_app` | 启动应用 |
| `mobile_swipe` | 滑动屏幕 |
| `mobile_press_key` | 按键操作 |

**总计：17 个工具**

## 📚 文档

- [用户配置指南](docs/USER_CONFIGURATION_GUIDE.md) - AI 密钥配置、常见问题
- [启动指南](docs/START_GUIDE.md) - 完整的安装和配置步骤
- [测试脚本生成](docs/如何生成测试脚本.md) - 如何生成 pytest 测试脚本

## 🎯 使用场景选择

### 个人使用 Cursor（推荐新手）
- 只装基础版：`pip install mobile-mcp-ai`
- 不配置 AI key
- 通过 Cursor AI 使用（Cursor AI 自带视觉识别）
- 💰 **完全免费**

### 平台开发（推荐开发者）
- 装完整版：`pip install mobile-mcp-ai[ai]`
- 配置 AI key
- 可以脱离 Cursor 独立使用
- 适合做自动化测试平台、CI/CD 集成
- 💸 需要 AI API 费用

## 🆕 v2.0.0 更新日志

### 重大改进
- ✨ AI 功能可选化：基础工具不需要 AI 密钥
- 🚀 新增 3 个工具：截图、区域截图、AI 视觉识别
- 📦 依赖优化：核心依赖最小化
- 🏗️ 架构重构：分离基础工具和智能工具
- 🐛 修复 AI 响应解析问题
- 📝 完善用户文档

### 向后兼容
- ✅ 完全兼容之前的使用方式
- ✅ 已配置 AI 的用户无需修改
- ✅ 新用户可以选择不配置 AI

## 📊 技术栈

- **MCP 协议**：与 Cursor AI 无缝集成
- **UIAutomator2**：Android 自动化引擎
- **Appium**：iOS 自动化支持（可选）
- **多 AI 支持**：通义千问、OpenAI、Claude（可选）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

有问题或建议？欢迎在 Issues 中反馈。

## 📄 License

Apache License 2.0

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！⭐**

[![Gitee Stars](https://gitee.com/chang-xinping/mobile-automation-mcp-service/badge/star.svg?theme=dark)](https://gitee.com/chang-xinping/mobile-automation-mcp-service/stargazers)

[Gitee 仓库](https://gitee.com/chang-xinping/mobile-automation-mcp-service) | [GitHub 仓库](https://github.com/test111ddff-hash/mobile-mcp-ai) | [PyPI 发布](https://pypi.org/project/mobile-mcp-ai/)

**让移动端测试更简单！** 🚀

</div>
