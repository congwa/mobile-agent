# Issue 标题

基于 mobile-mcp 构建的完整移动端 AI 自动化测试平台（Agent + 可视化操控台）

---

# Issue 内容（复制以下内容）

你好！👋

我基于您的 [mobile-mcp](https://gitee.com/chang-xinping/mobile-mcp) 项目进行了扩展开发，在 MCP 工具的基础上构建了一个完整的移动端 AI 自动化测试平台，特来分享交流。

## 📖 项目简介

在 mobile-mcp 的 39 个 MCP 工具基础上，新增了两个层次：

| 层次 | 说明 | 技术栈 |
|:---:|------|------|
| **MCP Server** | 基于 mobile-mcp 的工具集（有优化和新增工具） | Python · MCP 协议 · PyPI |
| **AI Agent** ⭐ 新增 | 智能测试执行引擎，自动编排工具调用、三范式自动降级、结果验证 | LangChain · LangGraph · FastAPI |
| **Electron 操控台** ⭐ 新增 | 可视化界面，设备实时预览、聊天交互、测试流程编排、操作日志时间轴 | Electron · React · TailwindCSS |

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────┐
│          Electron 操控台 (可视化界面)              │
│     React · TailwindCSS · Shadcn UI · oRPC       │
└──────────────────┬───────────────────────────────┘
                   │ HTTP / SSE
┌──────────────────▼───────────────────────────────┐
│          AI Agent (智能测试引擎)                    │
│   LangChain · LangGraph · FastAPI · SSE Stream    │
└──────────────────┬───────────────────────────────┘
                   │ MCP 协议 (stdio)
┌──────────────────▼───────────────────────────────┐
│      MCP Server (基于 mobile-mcp 的工具集)         │
│        39+ 移动端自动化工具 · Android + iOS        │
└──────────────────┬───────────────────────────────┘
                   │ ADB / WebDriverAgent
              📱 移动设备
```

## ✨ 新增的核心特性

- **AI Agent 智能执行**：基于 LangChain + LangGraph，自动编排工具调用，按步骤执行测试用例
- **三范式自动降级**：元素交互 → SoM 视觉 → 坐标定位，逐级降级确保操作成功率
- **可视化操控台**：Electron 桌面应用，设备实时预览、聊天交互、操作日志时间轴
- **MCP Server 增强**：新增 `mobile_hide_keyboard` 等工具、SSE 模式支持、工具范式分组注入

## 🎬 效果展示

![演示动图](https://gitee.com/cong_wa/mobile-mcp/raw/master/docs/videos/demo.gif)

![操控台截图](https://gitee.com/cong_wa/mobile-mcp/raw/master/images/agent1.png)

## 🔗 项目地址

- **Gitee**: https://gitee.com/cong_wa/mobile-mcp
- **GitHub**: https://github.com/congwa/mobile-agent
- **PyPI**: https://pypi.org/project/mobile-mcp-ai/

## 🙏 致谢

非常感谢您开源的 mobile-mcp 项目，为移动端 MCP 工具奠定了坚实的基础！我们在项目 README 中也明确标注了 fork 来源和致谢信息。

如果您有兴趣，欢迎交流合作！
