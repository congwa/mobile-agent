# Design Document: Mobile MCP AI Product Documentation System

## Overview

本设计文档描述了 Mobile MCP AI 系统的完整产品文档系统的设计方案。该文档系统旨在为开发者、测试人员和用户提供清晰、全面的技术文档，包括流程图、用户手册、API 参考和部署指南。

文档系统将采用模块化设计，使用标准化的格式（Markdown 和 .drawio），确保文档易于维护、更新和扩展。所有流程图将保持与现有系统架构图一致的专业风格。

## Architecture

### 文档目录结构

```
docs/
├── diagrams/                          # 流程图目录
│   ├── user-operation-flow.drawio     # 用户操作流程图
│   ├── tool-call-sequence.drawio      # 工具调用序列图
│   ├── locator-strategy-tree.drawio   # 定位策略决策树
│   ├── popup-handling-flow.drawio     # 弹窗处理流程图
│   └── use-case-flow.drawio           # 用例流程图
│
├── user-manual/                       # 用户手册目录
│   ├── README.md                      # 用户手册主页
│   ├── quick-start.md                 # 快速入门指南
│   ├── features/                      # 功能详细说明
│   │   ├── screenshot-tools.md        # 截图工具
│   │   ├── interaction-tools.md       # 交互工具
│   │   ├── navigation-tools.md        # 导航工具
│   │   ├── app-management.md          # 应用管理
│   │   ├── popup-handling.md          # 弹窗处理
│   │   ├── assertion-tools.md         # 断言工具
│   │   └── script-generation.md       # 脚本生成
│   ├── best-practices.md              # 最佳实践
│   └── faq.md                         # 常见问题
│
├── api-reference/                     # API 参考目录
│   ├── README.md                      # API 参考主页
│   ├── screenshot-api.md              # 截图 API
│   ├── interaction-api.md             # 交互 API
│   ├── navigation-api.md              # 导航 API
│   ├── app-management-api.md          # 应用管理 API
│   ├── popup-handling-api.md          # 弹窗处理 API
│   ├── assertion-api.md               # 断言 API
│   └── script-generation-api.md       # 脚本生成 API
│
└── deployment-guide/                  # 部署指南目录
    ├── README.md                      # 部署指南主页
    ├── android-setup.md               # Android 环境配置
    ├── ios-setup.md                   # iOS 环境配置
    ├── cursor-configuration.md        # Cursor 配置
    └── troubleshooting.md             # 故障排查
```

### 文档组件关系

```
┌─────────────────────────────────────────────────────────┐
│                    Documentation System                  │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Diagrams   │  │ User Manual  │  │ API Reference│  │
│  │              │  │              │  │              │  │
│  │ • Flow       │  │ • Quick Start│  │ • Tool Specs │  │
│  │ • Sequence   │  │ • Features   │  │ • Parameters │  │
│  │ • Decision   │  │ • Best Prac. │  │ • Examples   │  │
│  │ • Use Cases  │  │ • FAQ        │  │ • Errors     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │           Deployment Guide                        │   │
│  │                                                    │   │
│  │  • Android Setup  • iOS Setup  • Cursor Config   │   │
│  │  • Troubleshooting                                │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. 流程图组件 (Diagrams Component)

#### 1.1 用户操作流程图 (User Operation Flow)

**目的**: 展示从用户输入自然语言到设备执行操作的完整流程

**关键元素**:
- 用户输入自然语言指令
- Cursor AI 解析和理解
- MCP 协议通信
- 工具选择和执行
- 设备操作
- 结果反馈

**流程层次**:
```
用户 → Cursor AI → MCP Server → Tool Implementation → Device Client → Device Manager → 物理设备
  ↑                                                                                        ↓
  └────────────────────────────── 截图/状态反馈 ←──────────────────────────────────────────┘
```

#### 1.2 工具调用序列图 (Tool Call Sequence)

**目的**: 详细展示 MCP 工具调用的时序和数据流

**关键元素**:
- Cursor AI 发起调用
- MCP Server 接收请求
- 参数验证和解析
- 工具路由
- 设备客户端调用
- 底层库执行
- 结果返回链路

**时序流程**:
```
Cursor → MCP Server → BasicTools → MobileClient → DeviceManager → uiautomator2/WDA
   ↓         ↓            ↓             ↓              ↓                ↓
  等待    路由工具     执行逻辑      设备操作      底层调用         实际执行
   ↑         ↑            ↑             ↑              ↑                ↑
   └─────────┴────────────┴─────────────┴──────────────┴────────────────┘
                            结果返回路径
```

#### 1.3 定位策略决策树 (Locator Strategy Decision Tree)

**目的**: 展示系统如何选择最佳的元素定位方法

**决策节点**:
1. 是否有控件树信息？
   - 是 → 使用控件树定位（resourceId, text, description）
   - 否 → 继续下一步
2. 是否有 SoM 标注？
   - 是 → 使用 SoM 编号定位
   - 否 → 继续下一步
3. 是否有百分比坐标？
   - 是 → 使用百分比坐标定位
   - 否 → 继续下一步
4. 是否有模板图片？
   - 是 → 使用模板匹配定位
   - 否 → 返回错误

**优先级**: 控件树 > SoM 编号 > 百分比坐标 > 模板匹配

#### 1.4 弹窗处理流程图 (Popup Handling Flow)

**目的**: 展示自动弹窗检测和处理的完整流程

**流程阶段**:
1. **触发检测**
   - 操作前截图
   - 操作后截图
   - 图像差异分析

2. **弹窗识别**
   - 控件树查找（包含"允许"、"确定"等关键词）
   - 模板匹配（预定义弹窗模板）
   - 位置推测（屏幕中央、底部等常见位置）

3. **处理动作**
   - 点击允许/确定按钮
   - 点击关闭按钮
   - 返回键
   - 记录处理历史

4. **验证结果**
   - 再次截图
   - 确认弹窗消失
   - 继续原操作

#### 1.5 用例流程图 (Use Case Flow)

**目的**: 展示常见测试场景的完整操作流程

**用例 1: 应用登录测试**
```
1. 启动应用 (launch_app)
2. 等待首页加载 (wait_for_element)
3. 点击登录按钮 (click)
4. 输入用户名 (type_text)
5. 输入密码 (type_text)
6. 点击提交 (click)
7. 处理权限弹窗 (handle_popup)
8. 验证登录成功 (assert_element_exists)
9. 截图保存 (screenshot)
```

**用例 2: 商品搜索测试**
```
1. 启动应用 (launch_app)
2. 点击搜索框 (click)
3. 输入商品名称 (type_text)
4. 点击搜索按钮 (click)
5. 等待结果加载 (wait_for_element)
6. 滚动查看更多 (swipe)
7. 点击商品详情 (click)
8. 验证详情页 (assert_text_contains)
9. 生成测试脚本 (generate_script)
```

**用例 3: 设置修改测试**
```
1. 启动应用 (launch_app)
2. 导航到设置页 (navigate_to)
3. 查找设置项 (find_element)
4. 修改设置 (click/type_text)
5. 保存设置 (click)
6. 返回首页 (press_back)
7. 验证设置生效 (assert_state)
8. 截图记录 (screenshot)
```

### 2. 用户手册组件 (User Manual Component)

#### 2.1 快速入门指南结构

```markdown
# 快速入门指南

## 前置要求
- 操作系统要求
- Python 版本
- 设备要求

## 安装步骤
1. 克隆仓库
2. 安装依赖
3. 配置环境变量
4. 连接设备

## 第一个测试
- 启动 MCP Server
- 配置 Cursor
- 执行简单命令
- 查看结果

## 下一步
- 深入学习功能
- 查看 API 文档
- 阅读最佳实践
```

#### 2.2 功能文档结构

每个功能文档包含：
- **功能概述**: 简要说明功能用途
- **使用场景**: 何时使用该功能
- **工具列表**: 该类别下的所有工具
- **使用示例**: 实际使用案例
- **注意事项**: 常见问题和限制
- **相关工具**: 关联的其他工具

#### 2.3 最佳实践内容

- **定位策略选择**: 何时使用哪种定位方法
- **等待策略**: 如何处理异步加载
- **错误处理**: 如何优雅地处理失败
- **性能优化**: 如何提高测试效率
- **跨平台兼容**: Android 和 iOS 差异处理
- **脚本组织**: 如何组织测试代码
- **调试技巧**: 如何排查问题

### 3. API 参考组件 (API Reference Component)

#### 3.1 API 文档模板

每个工具的文档包含：

```markdown
## tool_name

### 描述
[工具的详细描述]

### 参数
| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| param1 | str  | 是   | -      | ... |
| param2 | int  | 否   | 0      | ... |

### 返回值
| 字段名 | 类型 | 说明 |
|--------|------|------|
| field1 | str  | ... |
| field2 | bool | ... |

### 使用示例

#### 基本用法
```python
result = tool_name(param1="value")
```

#### 高级用法
```python
result = tool_name(
    param1="value",
    param2=10
)
```

### 错误处理
- `ErrorType1`: 错误说明和解决方法
- `ErrorType2`: 错误说明和解决方法

### 平台差异
- **Android**: 特定行为说明
- **iOS**: 特定行为说明

### 相关工具
- [related_tool_1](#related_tool_1)
- [related_tool_2](#related_tool_2)
```

#### 3.2 工具分类

**截图工具**:
- `screenshot`: 基础截图
- `screenshot_with_som`: SoM 标注截图
- `screenshot_compressed`: 压缩截图

**交互工具**:
- `click`: 点击元素
- `click_by_som`: 通过 SoM 编号点击
- `click_by_percent`: 通过百分比坐标点击
- `long_press`: 长按元素
- `type_text`: 输入文本
- `clear_text`: 清除文本

**导航工具**:
- `swipe`: 滑动
- `swipe_up`: 向上滑动
- `swipe_down`: 向下滑动
- `swipe_left`: 向左滑动
- `swipe_right`: 向右滑动
- `press_back`: 返回键
- `press_home`: Home 键

**应用管理**:
- `launch_app`: 启动应用
- `close_app`: 关闭应用
- `install_app`: 安装应用
- `uninstall_app`: 卸载应用
- `get_current_app`: 获取当前应用

**弹窗处理**:
- `handle_popup`: 自动处理弹窗
- `detect_popup`: 检测弹窗
- `dismiss_popup`: 关闭弹窗

**断言工具**:
- `assert_element_exists`: 断言元素存在
- `assert_text_contains`: 断言文本包含
- `assert_app_running`: 断言应用运行中

**脚本生成**:
- `start_recording`: 开始录制
- `stop_recording`: 停止录制
- `generate_script`: 生成脚本

### 4. 部署指南组件 (Deployment Guide Component)

#### 4.1 Android 环境配置

```markdown
# Android 环境配置

## 前置要求
- 操作系统: Windows/macOS/Linux
- Python: 3.8+
- ADB: 最新版本

## 安装步骤

### 1. 安装 ADB
[详细步骤]

### 2. 安装 Python 依赖
```bash
pip install uiautomator2 adbutils
```

### 3. 连接设备
[USB 连接 / 无线连接步骤]

### 4. 初始化 uiautomator2
```bash
python -m uiautomator2 init
```

### 5. 验证安装
```python
import uiautomator2 as u2
d = u2.connect()
print(d.info)
```

## 常见问题
[问题列表和解决方案]
```

#### 4.2 iOS 环境配置

```markdown
# iOS 环境配置

## 前置要求
- 操作系统: macOS only
- Python: 3.8+
- Xcode: 最新版本
- iOS 设备: iOS 10+

## 安装步骤

### 1. 安装 Xcode
[详细步骤]

### 2. 安装 tidevice
```bash
pip install tidevice
```

### 3. 安装 WebDriverAgent
[详细步骤]

### 4. 安装 facebook-wda
```bash
pip install facebook-wda
```

### 5. 连接设备
[USB 连接步骤]

### 6. 启动 WDA
```bash
tidevice wdaproxy -B <bundle_id>
```

### 7. 验证安装
```python
import wda
c = wda.Client()
print(c.status())
```

## 常见问题
[问题列表和解决方案]
```

#### 4.3 Cursor 配置

```markdown
# Cursor 配置

## 配置 MCP

### 1. 编辑 Cursor 配置文件
位置: `~/.cursor/config.json`

### 2. 添加 MCP Server 配置
```json
{
  "mcpServers": {
    "mobile-mcp": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "DEVICE_PLATFORM": "android"
      }
    }
  }
}
```

### 3. 重启 Cursor

### 4. 验证连接
[验证步骤]

## 使用示例
[示例命令]
```

## Data Models

### 文档元数据模型

```python
class DocumentMetadata:
    """文档元数据"""
    title: str              # 文档标题
    version: str            # 文档版本
    last_updated: str       # 最后更新时间
    author: str             # 作者
    category: str           # 分类
    tags: List[str]         # 标签
    language: str           # 语言 (zh/en)
```

### 流程图元素模型

```python
class DiagramElement:
    """流程图元素"""
    id: str                 # 元素 ID
    type: str               # 类型 (rectangle/ellipse/diamond/arrow)
    label: str              # 标签文本
    position: Position      # 位置坐标
    size: Size              # 尺寸
    style: Style            # 样式
    connections: List[str]  # 连接的其他元素 ID

class Position:
    x: int
    y: int

class Size:
    width: int
    height: int

class Style:
    fill_color: str         # 填充颜色
    stroke_color: str       # 边框颜色
    stroke_width: int       # 边框宽度
    font_size: int          # 字体大小
    font_style: str         # 字体样式
```

### API 文档模型

```python
class APIDocumentation:
    """API 文档"""
    tool_name: str                  # 工具名称
    description: str                # 描述
    category: str                   # 分类
    parameters: List[Parameter]     # 参数列表
    return_value: ReturnValue       # 返回值
    examples: List[Example]         # 示例列表
    errors: List[ErrorDoc]          # 错误文档
    platform_notes: PlatformNotes   # 平台差异说明
    related_tools: List[str]        # 相关工具

class Parameter:
    name: str                       # 参数名
    type: str                       # 类型
    required: bool                  # 是否必需
    default: Any                    # 默认值
    description: str                # 说明
    valid_values: Optional[List]    # 有效值列表

class ReturnValue:
    type: str                       # 返回类型
    fields: List[Field]             # 字段列表
    description: str                # 说明

class Field:
    name: str                       # 字段名
    type: str                       # 类型
    description: str                # 说明

class Example:
    title: str                      # 示例标题
    code: str                       # 代码
    description: str                # 说明
    output: Optional[str]           # 输出

class ErrorDoc:
    error_type: str                 # 错误类型
    description: str                # 错误说明
    solution: str                   # 解决方法

class PlatformNotes:
    android: Optional[str]          # Android 特定说明
    ios: Optional[str]              # iOS 特定说明
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: File Format Consistency

*For any* documentation file in the system, if it is a text document then it SHALL use Markdown format (.md extension), and if it is a diagram then it SHALL use .drawio format (.drawio extension).

**Validates: Requirements 1.6, 5.4**

### Property 2: Tool Documentation Completeness

*For any* MCP tool documented in the API reference, the documentation SHALL include tool name, description, complete parameter specifications (name, type, required/optional status, default value, valid values), return value specification, and usage examples.

**Validates: Requirements 3.1, 3.2, 3.4**

### Property 3: Tool Organization by Category

*For any* set of tool documentation, all 30+ tools SHALL be organized into the seven functional categories: screenshot, interaction, navigation, app management, popup handling, assertion, and script generation.

**Validates: Requirements 2.2, 3.3**

### Property 4: Example Completeness

*For any* tool's example section, it SHALL include both successful execution examples and error handling scenarios, and where platform-specific behavior exists, it SHALL include both Android and iOS guidance.

**Validates: Requirements 2.6, 3.5**

### Property 5: Setup Documentation Completeness

*For any* platform setup document (Android or iOS), it SHALL include prerequisite checks, installation steps, device connection instructions, verification steps, and clearly indicate OS requirements and limitations.

**Validates: Requirements 4.5, 4.6**

### Property 6: Directory Structure Compliance

*For any* documentation file created, it SHALL be placed in the correct directory according to its type: diagrams/ for .drawio files, user-manual/ for user guides, api-reference/ for API docs, and deployment-guide/ for setup instructions.

**Validates: Requirements 5.1**

### Property 7: File Naming Convention

*For any* documentation file, the filename SHALL follow kebab-case naming convention (lowercase words separated by hyphens).

**Validates: Requirements 5.2**

### Property 8: Visual Aid Inclusion

*For any* documentation file, it SHALL include at least one type of visual aid (diagram, screenshot, or code example) to enhance understanding.

**Validates: Requirements 6.3**

### Property 9: Code Example Validity

*For any* code example in the documentation, when executed in the appropriate environment, it SHALL run without syntax errors and produce the expected output.

**Validates: Requirements 6.4**

### Property 10: Bilingual Support

*For any* user-facing documentation file, where appropriate for international users, both Chinese and English versions SHALL exist.

**Validates: Requirements 6.5**

## Error Handling

### Documentation Generation Errors

**File Creation Failures**:
- **Cause**: Insufficient permissions, disk space, or invalid file paths
- **Handling**: Log error with specific file path, provide clear error message, suggest corrective actions
- **Recovery**: Retry with validated path, create parent directories if needed

**Content Validation Errors**:
- **Cause**: Missing required sections, invalid format, broken links
- **Handling**: Validate content against schema, report specific validation failures
- **Recovery**: Provide template with required sections, auto-fix common issues

**Diagram Generation Errors**:
- **Cause**: Invalid .drawio XML structure, missing required elements
- **Handling**: Validate XML against .drawio schema, report parsing errors
- **Recovery**: Use fallback template, regenerate from scratch

### Documentation Update Errors

**Merge Conflicts**:
- **Cause**: Concurrent updates to same documentation file
- **Handling**: Detect conflicts, preserve both versions, notify user
- **Recovery**: Manual merge with diff view, automated merge for non-conflicting sections

**Version Mismatch**:
- **Cause**: Documentation out of sync with code implementation
- **Handling**: Compare API signatures with documentation, flag mismatches
- **Recovery**: Auto-update parameter lists, prompt for description updates

**Link Validation Errors**:
- **Cause**: Broken internal links, missing referenced files
- **Handling**: Scan all links, report broken references with source location
- **Recovery**: Auto-fix relative paths, suggest alternative links

### User Input Errors

**Invalid Configuration**:
- **Cause**: Incorrect paths, missing environment variables
- **Handling**: Validate configuration against schema, provide specific error messages
- **Recovery**: Suggest correct format, provide examples, use defaults where safe

**Missing Prerequisites**:
- **Cause**: Required tools not installed (ADB, Xcode, etc.)
- **Handling**: Check for required tools, report missing dependencies
- **Recovery**: Provide installation instructions, link to official docs

## Testing Strategy

### Dual Testing Approach

本文档系统将采用单元测试和属性测试相结合的方式：

**单元测试**用于验证：
- 特定文档文件的存在性（如 quick-start.md, android-setup.md）
- 特定图表的内容完整性（如用户操作流程图包含所有必需元素）
- 特定配置示例的正确性
- 边界情况（空文件、特殊字符、超长内容）

**属性测试**用于验证：
- 所有文档文件的格式一致性（Property 1）
- 所有工具文档的完整性（Property 2, 3, 4）
- 所有文件的命名规范（Property 7）
- 所有代码示例的有效性（Property 9）

### Property-Based Testing Configuration

**测试库选择**: Python 的 `hypothesis` 库

**测试配置**:
- 每个属性测试最少运行 100 次迭代
- 使用随机生成的文档路径、文件名、内容进行测试
- 每个测试必须引用设计文档中的属性编号

**测试标签格式**:
```python
# Feature: product-documentation, Property 1: File Format Consistency
@given(st.sampled_from(['diagram', 'text']))
def test_file_format_consistency(file_type):
    # Test implementation
    pass
```

### Test Coverage

**文档结构测试**:
- 验证目录结构符合设计
- 验证所有必需文件存在
- 验证文件命名符合规范

**内容完整性测试**:
- 验证 API 文档包含所有必需字段
- 验证流程图包含所有必需元素
- 验证示例代码可执行

**格式一致性测试**:
- 验证 Markdown 格式正确
- 验证 .drawio XML 结构有效
- 验证代码块语法高亮正确

**链接有效性测试**:
- 验证所有内部链接有效
- 验证所有外部链接可访问
- 验证图片引用存在

**平台兼容性测试**:
- 验证 Android 和 iOS 文档都存在
- 验证平台特定说明清晰标注
- 验证跨平台示例正确

### Integration Testing

**端到端文档生成测试**:
1. 从空目录开始
2. 生成所有文档文件
3. 验证完整性和一致性
4. 验证所有链接有效

**文档更新测试**:
1. 修改源代码（添加新工具）
2. 更新文档
3. 验证新内容正确添加
4. 验证现有内容未破坏

**多语言测试**:
1. 生成中文文档
2. 生成英文文档
3. 验证内容对应
4. 验证格式一致

