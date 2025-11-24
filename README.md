# Mobile MCP AI

移动端自动化测试框架，支持通过 Cursor AI 用自然语言执行测试并生成 pytest 测试用例。

[![PyPI version](https://img.shields.io/pypi/v/mobile-mcp-ai.svg)](https://pypi.org/project/mobile-mcp-ai/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

## 功能特性

- **自然语言测试**：在 Cursor 中用自然语言描述测试流程，AI 自动执行
- **智能定位**：支持多种定位策略，自动选择最优方案
- **自动生成脚本**：执行完成后可自动生成 pytest 格式的测试脚本
- **支持 Android 和 iOS**：通过 MCP 协议集成到 Cursor

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
      "command": "python",
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
帮我生成 pytest 测试脚本，测试名称是"建议发帖测试"，包名是 com.im30.way，文件名是 test_建议发帖
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
