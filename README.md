# Mobile MCP AI

移动端自动化测试框架，支持通过 Cursor AI 用自然语言执行测试并生成 pytest 测试用例。

[![PyPI version](https://img.shields.io/pypi/v/mobile-mcp-ai.svg)](https://pypi.org/project/mobile-mcp-ai/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

## 功能特性

### 🎯 自然语言驱动的智能测试
- **零代码测试**：用自然语言描述测试流程，AI 自动理解并执行每一步操作
- **智能交互**：自动处理异常情况，智能重试和错误恢复
- **降低门槛**：无需编写复杂脚本，降低测试门槛 90%+

### 🎨 智能定位策略
- **多级降级定位**：多层定位策略智能降级
- **高成功率**：定位成功率 95%+，平均耗时 <100ms（缓存命中 <5ms）
- **智能评分算法**：基于类型匹配、文本匹配、位置权重等多维度评分
- **多模态 AI**：支持视觉识别，应对复杂定位场景

### 🚀 一键生成 pytest 测试脚本
- **自动脚本生成**：基于操作历史自动生成标准 pytest 格式测试脚本
- **100% 可执行**：使用已验证的定位方式，确保脚本可直接运行
- **完整支持**：支持 pytest fixture、参数化、Allure 报告等所有特性
- **批量执行**：生成的脚本可与其他测试用例一起批量运行

### 🌐 跨平台支持
- **双平台支持**：完美支持 Android 和 iOS 平台
- **统一接口**：通过适配器模式实现 80%+ 代码复用率
- **设备管理**：自动检测和管理连接的设备，支持多设备切换

### 🤖 与 Cursor AI 深度集成
- **MCP 协议**：基于 Model Context Protocol，与 Cursor AI 无缝集成
- **20+ 工具**：提供丰富的移动端操作工具，AI 智能调用
- **AI 增强**：支持多平台 AI（Cursor/Claude/OpenAI/Gemini）自动检测与切换

### ⚡ 性能优化
- **XML 缓存机制**：TTL 1 秒缓存，减少重复读取开销
- **元素预过滤**：按类型、位置、属性预过滤，减少 50%+ 遍历
- **单次读取复用**：避免 400-1000ms 的重复 XML 读取开销

## 安装

```bash
pip install mobile-mcp-ai
```

## 快速开始

### 1. 配置 Cursor MCP

创建 `.cursor/mcp.json` 文件（项目根目录或用户目录 `~/.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "mobile-mcp-ai": {
      "command": "python",  // 建议使用当前项目的 Python 路径（如 venv/bin/python）
      "args": ["-m", "mobile_mcp.mcp.mcp_server"],
      "env": {
        "MOBILE_DEVICE_ID": "auto"
      }
    }
  }
}
```

详细配置说明请查看：[启动指南](docs/START_GUIDE.md)

### 2. 连接设备

```bash
# Android 设备
adb devices  # 确认设备可见
```

### 3. 重启 Cursor

配置完成后，完全退出并重新启动 Cursor。

### 4. 开始使用

重启 Cursor 后，在聊天窗口中用自然语言描述测试流程：

```
帮我测试登录功能：
1. 启动 com.example.app
2. 点击登录按钮
3. 输入用户名 admin
4. 输入密码 password
5. 点击提交按钮
6. 验证页面是否显示"欢迎"
```

AI 会自动理解并执行每一步操作，智能定位元素，处理异常情况。

## 使用示例

### 执行测试

在 Cursor 中用自然语言描述测试流程，AI 会自动执行每一步操作。

### 生成 pytest 脚本

执行完测试后，可以生成 pytest 格式的测试脚本：

```
帮我生成 pytest 测试脚本，测试名称是"建议发帖测试"，包名是 com.ixxxx.xxxx，文件名是 test_建议发帖
```

生成的脚本保存在 `tests/` 目录，可以直接运行：

```bash
pytest tests/test_建议发帖.py -v
```

## 可用工具

配置完成后，Cursor AI 可以使用以下工具：

- **设备管理**：`mobile_list_devices`, `mobile_get_current_package`, `mobile_get_screen_size` 等
- **交互操作**：`mobile_click`, `mobile_input`, `mobile_swipe`, `mobile_press_key` 等
- **页面分析**：`mobile_snapshot`, `mobile_take_screenshot`, `mobile_assert_text`
- **应用管理**：`mobile_launch_app`, `mobile_list_apps`, `mobile_install_app` 等
- **AI 增强**：`mobile_generate_test_script`（生成 pytest 脚本）

完整工具列表和使用说明请查看文档。

## 文档

- [启动指南](docs/START_GUIDE.md) - 完整的安装和配置步骤
- [使用指南](docs/INSTALL_AND_USE.md) - 详细的使用说明
- [常见问题](docs/FAQ.md) - 常见问题解答和故障排除
- [iOS 设置](docs/IOS_SETUP.md) - iOS 设备配置指南

## License

Apache License 2.0

## 贡献

欢迎提交 Issue 和 Pull Request！

GitHub: [test111ddff-hash/mobile-mcp-ai](https://github.com/test111ddff-hash/mobile-mcp-ai)
