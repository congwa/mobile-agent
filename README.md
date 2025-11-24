# 🚀 Mobile MCP AI - 让 AI 帮你写移动端测试代码

> **🤖 用自然语言描述测试流程，AI 自动执行并生成 pytest 测试用例！**

## ✨ 核心亮点

### 🎯 **零代码编写，自然语言测试**
- 在 Cursor 中直接用自然语言描述测试流程
- AI 自动理解并执行每一步操作
- **执行完成后，一键生成 pytest 格式的测试脚本**

### 🧠 **智能定位，自动重试**
- 找不到元素？AI 自动截图分析
- 定位失败？自动尝试多种定位策略
- 操作失败？AI 智能重试并调整策略

### 📝 **操作即代码，自动生成测试用例**
- 执行完测试流程后，AI 自动生成 pytest 测试脚本
- 使用已验证的定位方式（坐标、bounds 等）
- **生成的脚本 100% 可执行，支持 pytest 批量运行和 Allure 报告**

---

## 🎉 已发布到 PyPI！

```bash
pip install mobile-mcp-ai
```

**PyPI 页面**：https://pypi.org/project/mobile-mcp-ai/  
**GitHub 仓库**：https://github.com/test111ddff-hash/mobile-mcp-ai

---

## 🚀 5 分钟快速开始

### 1️⃣ 安装包

```bash
pip install mobile-mcp-ai
```

### 2️⃣ 配置 Cursor

创建 `.cursor/mcp.json`（项目根目录或用户目录 `~/.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "mobile-mcp-ai": {
      "command": "python",
      "args": ["-m", "mobile_mcp.mcp.mcp_server"],
      "env": {
        "MOBILE_DEVICE_ID": "auto"
      }
    }
  }
}
```

### 3️⃣ 连接 Android 设备

```bash
# USB 连接手机，启用 USB 调试
adb devices  # 确认设备可见
```

### 4️⃣ 重启 Cursor 并开始使用

重启 Cursor 后，直接在聊天窗口说：

```
帮我测试登录功能：
1. 启动 com.example.app
2. 点击登录按钮
3. 输入用户名 admin
4. 输入密码 password
5. 点击提交按钮
6. 验证页面是否显示"欢迎"
```

**AI 会自动执行每一步操作！** ✨

---

## 🎯 核心功能演示

### 📱 场景 1：自然语言执行测试

**你说：**
```
帮我测试发帖功能：
1. 启动 com.im30.way
2. 点击底部第三个图标
3. 点击黄色+号按钮
4. 点击建议
5. 输入内容"这是一条测试内容"
6. 点击提交按钮
7. 验证页面出现FAQ
```

**AI 自动：**
- ✅ 启动应用
- ✅ 智能定位并点击每个元素
- ✅ 自动处理弹窗、等待页面加载
- ✅ 验证操作结果

### 📝 场景 2：执行后自动生成 pytest 用例

**执行完测试后，你说：**
```
帮我生成 pytest 测试脚本，测试名称是"建议发帖测试"，包名是 com.im30.way，文件名是 test_建议发帖
```

**AI 自动：**
- ✅ 分析刚才执行的所有操作
- ✅ 提取已验证的定位方式（坐标、bounds、resource-id 等）
- ✅ 生成标准的 pytest 格式测试脚本
- ✅ 脚本保存在 `tests/` 目录，可直接运行

**生成的脚本示例：**
```python
import pytest
import asyncio
from mobile_mcp.core.mobile_client import MobileClient

PACKAGE_NAME = "com.im30.way"

@pytest.fixture(scope='function')
async def mobile_client():
    """pytest fixture: 创建并返回MobileClient实例"""
    client = MobileClient(device_id=None)
    await client.launch_app(PACKAGE_NAME, wait_time=5)
    yield client
    client.device_manager.disconnect()

@pytest.mark.asyncio
async def test_建议发帖(mobile_client):
    """测试用例: 建议发帖测试"""
    client = mobile_client
    # 使用已验证的定位方式执行测试步骤
    # ...
```

**运行生成的测试：**
```bash
# 运行单个测试
pytest tests/test_建议发帖.py -v

# 生成 Allure 报告
pytest tests/test_建议发帖.py --alluredir=./allure-results
allure serve ./allure-results
```

### 🧠 场景 3：智能调试和重试

**你说：**
```
为什么点击"云文档"失败了？
```

**AI 自动：**
1. 📸 调用 `mobile_snapshot` 查看当前页面结构
2. 🔍 分析为什么找不到"云文档"元素
3. 💡 发现可能是弹窗场景，建议使用视觉识别
4. 🎯 自动调用视觉识别并重新定位
5. ✅ 成功点击并继续执行

---

## 🎨 完整工作流程

```
┌─────────────────────────────────────────────────────────┐
│  1. 在 Cursor 中用自然语言描述测试流程                  │
└─────────────────┬───────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  2. AI 自动执行每一步操作                               │
│     - 智能定位元素（规则匹配、XML分析、视觉识别）        │
│     - 自动处理弹窗、等待页面加载                        │
│     - 失败时自动重试和调整策略                          │
└─────────────────┬───────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  3. 执行完成后，AI 自动生成 pytest 测试脚本            │
│     - 使用已验证的定位方式（坐标、bounds等）            │
│     - 100% 可执行的 pytest 格式                        │
│     - 支持批量运行和 Allure 报告                        │
└─────────────────┬───────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  4. 直接运行生成的测试脚本                              │
│     pytest tests/test_xxx.py -v                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ 可用的 MCP 工具

配置完成后，Cursor AI 可以使用以下 23 个工具：

### 📱 设备管理
- `mobile_list_devices` - 列出所有连接的设备
- `mobile_get_current_package` - 获取当前应用包名
- `mobile_get_screen_size` - 获取屏幕尺寸
- `mobile_get_orientation` / `mobile_set_orientation` - 获取/设置屏幕方向

### 🎯 交互操作
- `mobile_click` - 点击元素（支持自然语言描述）
- `mobile_double_click` - 双击
- `mobile_long_press` - 长按
- `mobile_input` - 输入文本
- `mobile_swipe` - 滑动屏幕
- `mobile_press_key` - 按键操作

### 📸 页面分析
- `mobile_snapshot` - 获取页面结构（XML树）
- `mobile_take_screenshot` - 截图
- `mobile_assert_text` - 断言文本存在

### 📦 应用管理
- `mobile_launch_app` - 启动应用
- `mobile_list_apps` - 列出已安装应用
- `mobile_install_app` / `mobile_uninstall_app` - 安装/卸载应用
- `mobile_terminate_app` - 终止应用

### 🧠 AI 增强功能（需要 AI 平台支持）
- `mobile_analyze_screenshot` - AI 分析截图并返回坐标
- `mobile_execute_test_case` - 智能执行测试用例
- **`mobile_generate_test_script`** - ⭐ **生成 pytest 测试脚本**

### 🌐 其他
- `mobile_open_url` - 在浏览器中打开 URL

---

## 💡 使用技巧

### 技巧 1：生成测试脚本的最佳时机

**推荐流程：**
1. 先用自然语言执行一遍完整的测试流程
2. 确保所有操作都成功执行
3. 然后让 AI 生成 pytest 脚本

**示例：**
```
# 第一步：执行测试
帮我测试登录功能：
1. 启动 com.example.app
2. 点击登录按钮
...（执行完成）

# 第二步：生成脚本
帮我生成 pytest 测试脚本，测试名称是"登录测试"，包名是 com.example.app，文件名是 test_登录
```

### 技巧 2：智能定位失败时的处理

如果 AI 找不到元素，会自动：
1. 📸 截图并创建分析请求
2. 🧠 调用 Cursor AI 视觉识别
3. 📍 获取坐标并点击
4. ✅ 继续执行后续步骤

你也可以手动触发：
```
帮我分析截图，找到"设置按钮"的位置
```

### 技巧 3：批量生成测试脚本

执行多个测试流程后，可以批量生成：
```
帮我生成 pytest 测试脚本：
- 测试名称：登录测试，包名：com.example.app，文件名：test_登录
- 测试名称：发帖测试，包名：com.example.app，文件名：test_发帖
```

---

## 📚 详细文档

- **[📘 安装和使用指南](docs/INSTALL_AND_USE.md)** - 完整的安装和配置说明
- **[🚀 快速开始](docs/QUICK_START.md)** - 5分钟快速上手
- **[❓ 常见问题](docs/FAQ.md)** - FAQ 和故障排除
- **[🍎 iOS 设置](docs/IOS_SETUP.md)** - iOS 设备配置指南
- **[📦 发布指南](docs/PACKAGE_PUBLISH.md)** - 如何发布到 PyPI

---

## 🎯 为什么选择 Mobile MCP AI？

| 特性 | 传统方式 | Mobile MCP AI |
|------|---------|---------------|
| **编写测试** | 需要写代码 | 自然语言描述 ✨ |
| **定位元素** | 手动写定位器 | AI 智能定位 ✨ |
| **调试失败** | 手动分析日志 | AI 自动分析 ✨ |
| **生成脚本** | 手动编写 | AI 自动生成 ✨ |
| **代码复用** | 需要手动提取 | 自动生成 pytest ✨ |
| **学习曲线** | 需要学习 API | 自然语言即可 ✨ |

---

## 🌟 核心优势

### 1. **零代码编写**
- 不需要学习任何 API
- 直接用自然语言描述测试流程
- AI 自动理解并执行

### 2. **智能定位系统**
- 规则匹配（85%）
- XML 深度分析（5%）
- 位置分析（5%）
- **Cursor AI 视觉识别（免费，1%）** ⭐

### 3. **操作即代码**
- 执行完测试后，一键生成 pytest 脚本
- 使用已验证的定位方式
- 100% 可执行的测试代码

### 4. **智能调试**
- 失败时自动截图分析
- AI 自动调整策略
- 自动重试和错误处理

---

## 🚀 开始使用

```bash
# 1. 安装
pip install mobile-mcp-ai

# 2. 配置 Cursor（创建 .cursor/mcp.json）
# 3. 连接设备（adb devices）
# 4. 重启 Cursor
# 5. 开始用自然语言测试！
```

**现在就试试吧！** 🎉

---

## 📄 License

Apache License 2.0

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

**GitHub 仓库**：https://github.com/test111ddff-hash/mobile-mcp-ai

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！⭐**

Made with ❤️ by [douzi](https://github.com/test111ddff-hash)

</div>
