# Mobile MCP AI

移动端自动化 MCP Server - 为 Cursor AI 提供移动设备控制能力，支持 Android/iOS

<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/mobile-mcp-ai.svg)](https://pypi.org/project/mobile-mcp-ai/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Gitee Stars](https://gitee.com/chang-xinping/mobile-automation-mcp-service/badge/star.svg?theme=white)](https://gitee.com/chang-xinping/mobile-automation-mcp-service)

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！⭐**

**🆕 v2.1.0 重大更新：智能验证系统 - 彻底解决"假成功"问题**

**✨ 核心改进：**
- ✅ **所有操作支持智能验证**：click、input、swipe、press_key 全部验证
- ✅ **实时检测操作结果**：页面变化、文本验证、内容变化检测
- ✅ **搜索键智能回退**：SEARCH 无效时自动尝试 ENTER
- ✅ **详细验证反馈**：返回验证状态、实际结果、警告信息
- ✅ **向后兼容**：默认启用验证，可选 `verify=False` 快速模式

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
- `mobile_press_key` - 按键操作（支持智能验证 ✨ 新增）

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

### 升级到最新版本

**⚠️ 重要：如果你已经安装了旧版本，强烈建议升级到 v2.1.0！**

```bash
# 升级到最新版本
pip install --upgrade mobile-mcp-ai

# 验证版本
pip show mobile-mcp-ai
```

## 🚀 快速开始

### 1. 配置 Cursor MCP

编辑 `~/.cursor/mcp.json`（macOS/Linux）或 `%APPDATA%\Cursor\mcp.json`（Windows）：

**⭐ 推荐配置（完整版，35 个工具）**：
```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "python",
      "args": ["-m", "mobile_mcp.mcp.mcp_server"],
      "cwd": "/path/to/your/project",
      "env": {}
    }
  }
}
```

> ✨ **完整版特性**（不需要 AI Key）：
> - ✅ 35 个自动化工具（比简化版多 5 个）
> - ✅ `mobile_generate_test_script` - 生成 pytest 测试脚本
> - ✅ `mobile_execute_test_case` - 执行 pytest 测试用例
> - ✅ `mobile_configure` - 动态调整等待时间、重试策略
> - ✅ `mobile_get_config` - 查看当前配置
> - ✅ `mobile_wait` - 明确等待指定秒数

<details>
<summary>📦 简化版配置（30 个工具，轻量场景）</summary>

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "python",
      "args": ["-m", "mobile_mcp.mcp.mcp_server_simple"],
      "cwd": "/path/to/your/project",
      "env": {}
    }
  }
}
```

> ⚠️ 简化版不包含测试脚本生成、动态配置等高级功能。

</details>

> 🎯 **默认行为**：
> - ✅ 在 Cursor 中运行时，**自动使用 Cursor AI**（免费，无需配置）
> - ✅ 智能定位、视觉识别等 AI 功能开箱即用
> - ✅ 不会消耗你的 API 额度，完全零成本
> 
> ⚙️ **工作区配置**（重要）：
> - `"cwd"`: 设置为你的项目根目录路径
> - 生成的测试脚本会保存到 `项目目录/tests/`
> - 如果不配置，脚本会生成到用户主目录（不推荐）

---

**智能模式配置（可选，使用其他 AI 平台）**：
```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "python",
      "args": ["-m", "mobile_mcp.mcp.mcp_server"],
      "cwd": "/path/to/your/project",
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
| `mobile_press_key` | 按键操作（支持智能验证 ✨ 新增）|

**总计：18 个工具**

## 🎯 智能验证功能详解

### `mobile_press_key` - 彻底解决"假成功"问题

**问题背景：**

传统按键操作只检查命令是否执行，不验证按键是否真的生效，导致：
- ✗ 命令执行成功 ≠ 按键生效
- ✗ 测试显示通过，实际操作失败
- ✗ 搜索键在某些应用/输入法中不起作用

**智能验证方案：**

```python
# 方式1: 验证模式（推荐，默认）
await press_key("search", verify=True)
# ✅ 自动检测页面变化
# ✅ 搜索键无效时自动尝试回车键
# ✅ 返回真实操作结果

# 方式2: 快速模式
await press_key("back", verify=False)
# ⚡ 执行后立即返回
# ⚠️  不保证按键效果
```

**工作原理：**

1. **操作前快照** - 记录当前页面状态
2. **执行按键** - 发送按键命令
3. **页面监测** - 等待并检测页面变化（最多2秒）
4. **智能判断** - 页面变化 > 5% 认为成功
5. **搜索键回退** - SEARCH 无效时自动尝试 ENTER

**使用示例：**

```
@MCP 帮我搜索：
1. 在搜索框输入 "测试内容"
2. 按搜索键（自动验证）
```

返回结果：
```json
{
  "success": true,
  "key": "search",
  "keycode": 84,
  "verified": true,
  "page_changed": true,
  "fallback_used": false,
  "message": "搜索键(SEARCH)生效"
}
```

如果 SEARCH 键无效：
```json
{
  "success": true,
  "key": "search",
  "keycode": 66,
  "verified": true,
  "page_changed": true,
  "fallback_used": true,
  "message": "搜索键(SEARCH)无效，已使用ENTER键替代并成功"
}
```

如果按键无效：
```json
{
  "success": false,
  "key": "search",
  "verified": true,
  "page_changed": false,
  "message": "按键命令执行成功但页面未变化，可能按键未生效"
}
```

**使用建议：**

| 场景 | 模式 | 原因 |
|------|------|------|
| 搜索、提交等关键操作 | `verify=True` | 确保操作真的成功 |
| 返回上一页 | `verify=True` | 确保页面跳转 |
| 连续快速导航 | `verify=False` | 提高执行速度 |
| 调试/测试 | `verify=True` | 发现潜在问题 |

**性能对比：**

- 快速模式：~0.05秒（不保证效果）
- 验证模式：~0.5-2秒（确保成功）
- 额外耗时：小于2秒，换来可靠性

**支持的按键：**

- `enter` / `回车` - Enter键 (keycode=66)
- `search` / `搜索` - 搜索键 (keycode=84, 自动回退到66)
- `back` / `返回` - 返回键 (keycode=4)
- `home` - Home键 (keycode=3)
- 直接使用keycode数字（如 `66`）

**演示脚本：**

运行 `python backend/mobile_mcp/examples/press_key_verification_demo.py` 查看完整演示

## 📚 文档

- [用户配置指南](docs/USER_CONFIGURATION_GUIDE.md) - AI 密钥配置、常见问题
- [启动指南](docs/START_GUIDE.md) - 完整的安装和配置步骤
- [测试脚本生成](docs/如何生成测试脚本.md) - 如何生成 pytest 测试脚本
- [自动化行为配置说明](docs/自动化行为配置说明.md) - 控制屏幕方向和自动关闭广告

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
