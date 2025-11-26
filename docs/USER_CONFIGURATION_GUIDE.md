# Mobile MCP AI 用户配置指南

## 📦 安装说明

### 1. 安装 Mobile MCP AI 包

```bash
# 使用 pip 安装
pip install mobile-mcp-ai

# 或从 GitHub 安装最新版本
pip install git+https://github.com/your-repo/mobile-mcp-ai.git
```

### 2. 准备 Android 设备

- 打开手机的 **开发者选项**
- 启用 **USB 调试**
- 连接到电脑并授权
- 安装 **uiautomator2** 服务（首次使用会自动安装）

## ⚙️ Cursor 配置

### 1. 配置 MCP Server

在 Cursor 中打开 MCP 配置文件（`.cursor/mcp.json` 或全局配置）：

```json
{
  "mcpServers": {
    "mobile-mcp-ai": {
      "command": "python",
      "args": [
        "-m",
        "mobile_mcp.mcp.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "/path/to/your/project"
      }
    }
  }
}
```

### 2. 配置 AI 密钥 ⭐ **必需步骤**

**重要**：Mobile MCP AI 内部使用 AI 进行智能元素定位和分析，因此**必须配置 AI 密钥**才能使用完整功能。

#### 方式一：使用 `.env` 文件（推荐）

在项目根目录创建 `.env` 文件：

```bash
# AI 提供商配置（选择一个）

# 选项1: 使用通义千问（推荐，速度快）
AI_PROVIDER=qwen
QWEN_API_KEY=your-qwen-api-key-here
QWEN_MODEL=qwen-turbo  # 或 qwen-max

# 选项2: 使用 OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4  # 或 gpt-3.5-turbo

# 选项3: 使用 Claude (Anthropic)
AI_PROVIDER=claude
ANTHROPIC_API_KEY=your-anthropic-api-key-here
CLAUDE_MODEL=claude-3-sonnet-20240229

# 选项4: 使用本地 Ollama（免费，但速度较慢）
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

#### 方式二：使用环境变量

在系统环境变量中设置：

```bash
# macOS/Linux
export AI_PROVIDER=qwen
export QWEN_API_KEY=your-api-key

# Windows
set AI_PROVIDER=qwen
set QWEN_API_KEY=your-api-key
```

#### 方式三：在 Cursor MCP 配置中设置

```json
{
  "mcpServers": {
    "mobile-mcp-ai": {
      "command": "python",
      "args": ["-m", "mobile_mcp.mcp.mcp_server"],
      "env": {
        "AI_PROVIDER": "qwen",
        "QWEN_API_KEY": "your-api-key",
        "QWEN_MODEL": "qwen-turbo"
      }
    }
  }
}
```

## 🔑 获取 AI API 密钥

### 通义千问（推荐，国内速度快）

1. 访问：https://dashscope.aliyun.com/
2. 注册/登录阿里云账号
3. 创建 API Key
4. 复制密钥到 `.env` 文件

### OpenAI

1. 访问：https://platform.openai.com/
2. 注册/登录账号
3. 创建 API Key
4. 复制密钥到 `.env` 文件

### Claude (Anthropic)

1. 访问：https://console.anthropic.com/
2. 注册/登录账号
3. 创建 API Key
4. 复制密钥到 `.env` 文件

### Ollama（本地免费方案）

1. 安装 Ollama：https://ollama.ai/
2. 下载模型：`ollama pull llama2`
3. 启动服务：`ollama serve`
4. 配置 `.env`：
   ```bash
   AI_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2
   ```

## ✅ 验证配置

### 1. 检查 MCP Server 是否正常启动

重启 Cursor，查看 MCP 日志（`MCP: user-mobile-mcp-ai.log`）：

- ✅ 正确：`✅ AI增强功能已启用: qwen (qwen-turbo)`
- ❌ 错误：`⚠️ AI增强工具已禁用（未检测到可用的AI平台）`

### 2. 测试 AI 定位功能

在 Cursor 中测试：

```
@mobile-mcp-ai 列出设备

@mobile-mcp-ai 启动应用 com.android.settings

@mobile-mcp-ai 点击"设置"
```

如果看到以下日志，说明 AI 功能正常：
```
🤖 使用AI分析 (Provider: qwen, Model: qwen-turbo)
✅ AI分析成功: 设置 (置信度: 95%)
```

## 🚫 常见问题

### 问题1：AI 功能未启用

**错误日志**：
```
⚠️  AI增强工具已禁用（未检测到可用的AI平台）
```

**解决方案**：
1. 检查 `.env` 文件是否存在且配置正确
2. 检查 API Key 是否有效
3. 重启 Cursor MCP Server

### 问题2：AI 分析失败

**错误日志**：
```
❌ AI调用失败: 无法解析AI响应
```

**解决方案**：
1. 检查网络连接（特别是使用 OpenAI/Claude 时）
2. 检查 API Key 余额是否充足
3. 尝试切换其他 AI 提供商

### 问题3：元素定位失败

**错误日志**：
```
❌ text输入失败: 输入框不存在: search_box
```

**解决方案**：
1. 等待页面完全加载后再操作
2. 使用更精确的描述（如"顶部搜索框"而不是"搜索框"）
3. 尝试使用 `mobile_snapshot` 查看页面结构

## 📊 功能说明

### 无需 AI 的功能

以下功能不需要 AI，可以直接使用：

- `mobile_list_devices` - 列出设备
- `mobile_launch_app` - 启动应用
- `mobile_snapshot` - 获取页面快照
- `mobile_press_key` - 按键操作
- `mobile_swipe` - 滑动操作
- 使用 resource-id 或 bounds 坐标的精确定位

### 需要 AI 的功能

以下功能依赖 AI 进行智能分析：

- 自然语言描述的元素定位（如"点击右上角的设置按钮"）
- 复杂场景的元素识别
- 动态内容的智能匹配
- 测试脚本生成

## 💰 成本说明

### 通义千问（推荐）

- **qwen-turbo**：¥0.004/千tokens（超便宜）
- **qwen-max**：¥0.04/千tokens
- 典型单次定位：约 500-1000 tokens
- **预估成本**：每次定位 ¥0.002-0.004（不到1分钱）

### OpenAI

- **gpt-3.5-turbo**：$0.002/千tokens
- **gpt-4**：$0.03/千tokens
- **预估成本**：每次定位 $0.001-0.03

### Claude

- **claude-3-sonnet**：$0.003/千tokens
- **预估成本**：每次定位 $0.0015-0.003

### Ollama

- **完全免费**（本地运行）
- 需要足够的硬件资源（建议 16GB+ 内存）

## 🎯 最佳实践

1. **优先使用 XML 分析**：对于有明确 text/resource-id 的元素，系统会自动使用免费的 XML 分析
2. **AI 作为兜底**：只有在 XML 分析失败时才会调用 AI
3. **使用缓存**：相同的查询会使用缓存结果，不会重复调用 AI
4. **选择合适的模型**：
   - 简单场景：qwen-turbo（快速、便宜）
   - 复杂场景：qwen-max 或 gpt-4（准确但贵）
   - 开发测试：ollama（免费但慢）

## 📝 完整配置示例

`.env` 文件完整示例：

```bash
# ========== Mobile MCP AI 配置 ==========

# AI 提供商（必需）
AI_PROVIDER=qwen

# 通义千问配置
QWEN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
QWEN_MODEL=qwen-turbo

# 日志配置（可选）
LOG_LEVEL=INFO
ENABLE_DEBUG_LOG=false

# 设备配置（可选）
DEFAULT_DEVICE_ID=  # 留空自动选择第一个设备
SCREEN_ORIENTATION=portrait  # 或 landscape

# 性能配置（可选）
CACHE_TTL=300  # 缓存时间（秒）
MAX_WAIT_TIME=30  # 最大等待时间（秒）
```

## 🔄 更新和维护

### 更新 Mobile MCP AI

```bash
# 更新到最新版本
pip install --upgrade mobile-mcp-ai

# 从 GitHub 更新
pip install --upgrade git+https://github.com/your-repo/mobile-mcp-ai.git
```

### 查看版本

```python
import mobile_mcp
print(mobile_mcp.__version__)
```

## 📞 支持和反馈

- GitHub Issues: https://github.com/your-repo/mobile-mcp-ai/issues
- 文档: https://github.com/your-repo/mobile-mcp-ai/blob/main/README.md
- 示例: https://github.com/your-repo/mobile-mcp-ai/tree/main/examples

---

**重要提醒**：使用 Mobile MCP AI 必须配置 AI 密钥才能使用完整的智能定位功能！

