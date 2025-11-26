# Mobile MCP AI

移动端自动化 MCP Server - 为 Cursor AI 提供移动设备控制能力，支持 Android/iOS

<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/mobile-mcp-ai.svg)](https://pypi.org/project/mobile-mcp-ai/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Gitee Stars](https://gitee.com/chang-xinping/mobile-automation-mcp-service/badge/star.svg?theme=white)](https://gitee.com/chang-xinping/mobile-automation-mcp-service)

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！⭐**

**🆕 v2.0.3 更新：智能等待 + 测试脚本生成！基础工具不需要配置 AI 密钥**

</div>

## ✨ 核心特性

### 🎯 AI 功能可选化
- **基础模式**：不需要配置 AI 密钥，Cursor AI 提供所有智能能力
- **智能模式**：可选配置 AI 密钥，适合构建自动化测试平台
- **零成本起步**：基础工具完全免费，无需额外 AI API 费用
- **灵活选择**：根据使用场景自由选择是否启用 AI 功能

### 🧪 智能测试脚本生成（v2.0.3 新增）
- **操作录制**：AI 操作手机时自动记录所有步骤
- **一键生成**：生成独立的 pytest 测试脚本
- **智能等待**：自动添加页面加载、跳转等待逻辑
- **弹窗处理**：智能检测和跳过可选弹窗
- **开箱即用**：生成的脚本只依赖 uiautomator2，无需 mobile-mcp-ai

### 📦 工具架构

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

#### 测试工具（1个，不需要 AI）✨ 新增
- `mobile_generate_test_script` - 生成 pytest 测试脚本

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
- **18 个工具**：丰富的移动端操作工具
- **视觉识别**：Cursor AI 可以直接分析截图并操作
- **测试生成**：AI 操作后一键生成 pytest 脚本

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

**基础模式（推荐，默认使用 Cursor AI，完全免费）**：
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

> 🎯 **默认行为**：
> - ✅ 在 Cursor 中运行时，**自动使用 Cursor AI**（免费，无需配置）
> - ✅ 智能定位、视觉识别等 AI 功能开箱即用
> - ✅ 不会消耗你的 API 额度，完全零成本

**智能模式（可选，使用其他 AI 平台）**：
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

> 💡 **提示**：只有在以下情况才需要配置 AI 密钥：
> - 想使用通义千问、Claude、OpenAI 等其他 AI 平台
> - 构建独立的自动化测试平台（非 Cursor 环境）
> - 需要离线运行或集成到 CI/CD

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

### 场景4：生成测试脚本（推荐）✨ 新增
```
@MCP 帮我测试登录功能：
1. 启动应用 com.example.app
2. 截图，找到"登录"按钮并点击
3. 在"用户名"输入 "test123"
4. 在"密码"输入 "pass123"
5. 点击"提交"按钮

@MCP 生成刚才操作的测试脚本
```

AI 会自动生成一个完整的 pytest 测试脚本：
- ✅ 保存到你的项目 `tests/` 目录
- ✅ 包含智能等待逻辑（页面加载、跳转、输入）
- ✅ 自动处理弹窗（存在则点击，不存在跳过）
- ✅ 支持多设备（自动检测设备ID）
- ✅ 独立运行（只需要 `pip install uiautomator2 pytest`）

生成的脚本示例：
```python
def test_登录(device):
    d = device
    
    # 步骤1: 点击"登录"
    d.click(540, 338)
    time.sleep(2.0)  # 智能等待页面跳转
    
    # 步骤2: 输入用户名
    d(resourceId="com.example:id/username").set_text("test123")
    time.sleep(1.5)
    
    # 步骤3: 点击提交
    d.click(972, 1200)
    time.sleep(2.0)
    
    assert d(text="首页").exists()
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

### 测试工具（不需要 AI，共 1 个）✨ 新增
| 工具 | 说明 | 特点 |
|------|------|------|
| `mobile_generate_test_script` | 生成 pytest 测试脚本 | 智能等待、弹窗处理、独立运行 |

### 通用工具（共 4 个）
| 工具 | 说明 |
|------|------|
| `mobile_snapshot` | 获取页面结构 |
| `mobile_launch_app` | 启动应用 |
| `mobile_swipe` | 滑动屏幕 |
| `mobile_press_key` | 按键操作 |

**总计：18 个工具**

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

## 🆕 更新日志

### v2.0.3 (最新)
- ✨ **测试脚本生成**：AI 操作后一键生成 pytest 脚本
- ⏱️ **智能等待优化**：从固定 3 秒改为智能检测页面稳定（2-8秒）
- 🎯 **弹窗智能处理**：自动检测和跳过可选弹窗，避免测试失败
- 📱 **设备ID自动检测**：支持多设备环境
- 📂 **路径自动修复**：测试脚本保存到用户项目目录
- 🚀 **超时优化**：MCP 操作超时从 25.9秒降至 8秒（69% 提升）
- 🔧 **等待时间优化**：根据操作类型智能调整（页面跳转 2秒，搜索 2.5秒）

### v2.0.2
- 🐛 修复独立测试脚本生成问题
- 📦 优化依赖管理

### v2.0.1
- 🐛 修复测试脚本 `append()` 语法错误
- 📝 更新文档

### v2.0.0
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
