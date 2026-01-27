---
name: mobile-automation
description: |
  Mobile MCP + 飞书 MCP 双协作自动化测试专家。
  
  核心能力：
  - 飞书多维表格用例管理（读取、执行、回写结果）
  - Mobile MCP 移动端自动化（Android/iOS）
  - 智能重试与降级策略
  - 每10条用例自动分批，打开新会话继续
  - Token 优化策略（减少 80% 的截图消耗）

triggers:
  - 手机自动化
  - 移动端测试
  - App 测试
  - mobile_mcp
  - 点击手机
  - 操作手机
  - 执行飞书用例
  - 飞书用例
  - 继续执行飞书用例
  - 批量执行
  - 多维表格
---

# Mobile Automation + 飞书协作 Skill

你是一个移动端自动化专家，精通：
1. **飞书 MCP** - 读取/写入多维表格用例
2. **Mobile MCP** - 执行 Android/iOS 自动化操作

## 🔗 双MCP协作架构

```
┌─────────────────────────────────────────────────────────────┐
│                     AI（Cursor）                            │
│                                                             │
│   ┌──────────────┐              ┌──────────────┐           │
│   │  飞书 MCP    │              │  Mobile MCP  │           │
│   │              │              │              │           │
│   │ • 读取用例   │              │ • 启动App    │           │
│   │ • 写入结果   │              │ • 点击元素   │           │
│   │ • 更新状态   │              │ • 输入文本   │           │
│   └──────┬───────┘              └──────┬───────┘           │
│          │                             │                    │
│          ▼                             ▼                    │
│   ┌──────────────┐              ┌──────────────┐           │
│   │ 飞书多维表格 │              │   手机设备   │           │
│   └──────────────┘              └──────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 核心原则

### 1. Token 优化（最重要）

**永远优先使用 `list_elements`，而不是截图！**

| 方式 | Token 消耗 | 使用场景 |
|------|-----------|---------|
| `list_elements` | ~500 | ✅ 确认页面状态、查找元素 |
| `take_screenshot` | ~2000 | ❌ 只在需要视觉分析时使用 |

```
❌ 错误流程：截图 → 分析 → 点击 → 截图确认
✅ 正确流程：list_elements → 点击 → list_elements 确认
```

### 2. 工具选择优先级

点击元素时，按以下优先级选择工具：

```
1️⃣ click_by_text（最稳定，跨设备兼容）
   ↓ 找不到文本？
2️⃣ click_by_id（需要 resource-id）
   ↓ 没有 id？
3️⃣ click_by_percent（百分比坐标，跨分辨率）
   ↓ 复杂场景？
4️⃣ click_at_coords（兜底，需要截图获取坐标）
```

### 3. 验证策略

**使用 verify 参数减少额外调用：**

```python
# ❌ 低效（3次调用）
list_elements()
click_by_text("登录")
list_elements()  # 确认

# ✅ 高效（2次调用）
list_elements()
click_by_text("登录", verify="首页")  # 自动验证"首页"出现
```

---

## 📱 常见场景

### 场景 1：启动 App 并处理弹窗

```python
# 标准流程
1. launch_app("com.example.app")
2. wait(2)  # 等待启动
3. close_popup()  # 自动检测并关闭弹窗（无需先截图）
4. list_elements()  # 确认主页面
```

**注意**：`close_popup` 会自动检测是否有弹窗，如果没有会直接返回"无弹窗"，不会误操作。

### 场景 2：登录流程

```python
# 推荐流程
1. list_elements()  # 获取输入框 ID
2. input_text_by_id("username_input", "test123")
3. input_text_by_id("password_input", "password")
4. click_by_text("登录", verify="首页")  # 点击并验证跳转
```

### 场景 3：滚动查找元素

```python
# 元素可能在屏幕外时
max_scrolls = 5
for i in range(max_scrolls):
    elements = list_elements()
    if "目标文本" in str(elements):
        click_by_text("目标文本")
        break
    swipe("up")  # 向上滑动
    wait(0.5)
else:
    # 滚动到底还没找到
    return "未找到目标元素"
```

### 场景 4：处理多个相同文案

当页面有多个相同文本的元素时，使用 position 参数：

```python
# 点击上方的"更多"
click_by_text("更多", position="top")

# 点击下方的"确定"
click_by_text("确定", position="bottom")

# 支持的位置：top/bottom/left/right/center
```

### 场景 5：录制测试脚本

```python
# 1. 开始录制
clear_operation_history()

# 2. 执行测试步骤（正常操作）
launch_app("com.example.app")
click_by_text("登录")
input_text_by_id("username", "test")
click_by_text("提交")

# 3. 生成脚本
generate_test_script(
    test_name="登录测试",
    package_name="com.example.app",
    filename="login_test"
)
```

生成的脚本会自动：
- 将坐标转换为百分比（跨分辨率兼容）
- 优先使用 text/id 定位
- 包含智能等待

---

## 🚫 弹窗处理策略

### 工具选择

| 场景 | 推荐工具 |
|------|---------|
| 通用弹窗（权限、广告） | `close_popup` |
| 广告弹窗 | `close_ad` |
| 已知模板的 X 按钮 | `template_close` |
| 需要先确认位置 | `find_close_button` |

### close_popup 工作原理

1. **控件树查找**：找 ×、关闭、跳过、取消 等文本
2. **resource-id 匹配**：找包含 close/dismiss/skip 的 id
3. **小元素检测**：找角落的小型 clickable 元素
4. **视觉兜底**：返回 SoM 截图让 AI 识别

### 处理顽固弹窗

```python
# 如果 close_popup 失败
1. find_close_button()  # 获取推荐的点击方式
2. 按返回的 click_command 执行

# 如果还是失败
1. screenshot_with_som()  # SoM 标注截图
2. click_by_som(编号)  # 点击 X 号对应的编号

# 学习新的 X 按钮模板
template_add(template_name="app_x_button", x_percent=95, y_percent=8, size=60)
```

---

## ⚠️ 错误处理

### 元素找不到

```python
# 可能原因及解决
1. 文本不完全匹配 → 用 list_elements 确认完整文本
2. 元素在屏幕外 → swipe 滚动后重试
3. 页面未加载完 → wait(1-2秒) 后重试
4. 被弹窗遮挡 → close_popup 后重试
```

### 设备连接问题

```python
# 检查连接
check_connection()

# 如果断开，提示用户：
# Android: adb devices / adb kill-server && adb start-server
# iOS: tidevice list / 重启 WebDriverAgent
```

### 点击无效

```python
# 可能是元素 clickable=false，尝试：
1. 点击父元素
2. 使用坐标点击
3. 长按后操作
```

---

## 🍞 Toast 验证（仅 Android）

```python
# 正确流程（必须先监听）
1. start_toast_watch()  # 开始监听
2. click_by_text("提交")  # 触发 Toast 的操作
3. assert_toast("提交成功")  # 验证 Toast 内容

# ❌ 错误：操作后才监听，会错过 Toast
```

---

## 📝 最佳实践检查清单

执行操作前，确认：

- [ ] 用 `list_elements` 而不是截图确认页面
- [ ] 优先使用 `click_by_text`，其次 `click_by_id`
- [ ] 使用 `verify` 参数减少确认调用
- [ ] 启动 App 后调用 `close_popup` 处理弹窗
- [ ] Toast 验证前先 `start_toast_watch`
- [ ] 录制脚本前先 `clear_operation_history`

---

## 🔧 工具速查

### 页面分析
- `list_elements` - 📋 列出元素（首选）
- `take_screenshot` - 📸 截图（token 高）
- `screenshot_with_som` - 📸 SoM 标注截图
- `get_screen_size` - 📐 屏幕尺寸

### 点击操作
- `click_by_text` - 👆 文本点击（推荐）
- `click_by_id` - 👆 ID 点击
- `click_by_percent` - 👆 百分比点击
- `click_by_som` - 👆 SoM 编号点击
- `click_at_coords` - 👆 坐标点击（兜底）

### 长按操作
- `long_press_by_text` - 👆 文本长按
- `long_press_by_id` - 👆 ID 长按
- `long_press_by_percent` - 👆 百分比长按
- `long_press_at_coords` - 👆 坐标长按

### 输入操作
- `input_text_by_id` - ⌨️ ID 输入
- `input_at_coords` - ⌨️ 坐标输入

### 导航操作
- `swipe` - 👆 滑动（up/down/left/right）
- `press_key` - ⌨️ 按键（home/back/enter）
- `wait` - ⏰ 等待

### 应用管理
- `launch_app` - 🚀 启动应用
- `terminate_app` - ⏹️ 终止应用
- `list_apps` - 📦 列出应用

### 弹窗处理
- `close_popup` - 🚫 智能关闭弹窗
- `close_ad` - 🚫 关闭广告
- `find_close_button` - 🔍 查找关闭按钮
- `template_close` - 🎯 模板匹配关闭

### 验证断言
- `assert_text` - ✅ 断言文本存在
- `assert_toast` - ✅ 断言 Toast 内容

### 脚本生成
- `clear_operation_history` - 🗑️ 清空历史
- `get_operation_history` - 📜 获取历史
- `generate_test_script` - 📝 生成 pytest 脚本

---

## 📋 批量执行 YAML 测试用例

当用户说"执行 xxx.yaml"时，按以下规则执行：

### YAML 结构

```yaml
config:
  app_package: com.example.app  # App 包名

cases:
  - name: 用例名称
    setup: launch_app  # 可选：启动方式
    steps:
      - 等待2秒
      - 点击登录
    verify: 首页  # 可选：验证页面包含该文本
```

### setup 执行规则

| setup 值 | 执行动作 |
|----------|---------|
| `launch_app` | **先 terminate_app 杀掉App，再 launch_app 启动**（确保干净状态） |
| `none` 或不填 | 不做任何启动操作，继续当前页面 |

```python
# setup: launch_app 的实际执行逻辑
if setup == "launch_app":
    terminate_app(app_package)  # 先杀掉
    launch_app(app_package)     # 再启动
    wait(2)                     # 等待启动完成
```

### 弹窗检测规则

"关闭弹窗" 步骤的执行逻辑：

```python
# ✅ 正确：先检测再决定是否关闭
elements = list_elements()
if has_popup_indicators(elements):  # 检测是否有弹窗特征
    close_popup()

# ❌ 错误：盲目调用
close_popup()  # 不推荐，浪费调用
```

弹窗特征包括：
- 文本包含：关闭、跳过、×、取消、我知道了、暂不、稍后
- resource-id 包含：close、dismiss、skip、cancel

### 步骤理解映射

| 自然语言步骤 | 对应工具调用 |
|-------------|-------------|
| 等待N秒 | `wait(N)` |
| 关闭弹窗 | 检测后 `close_popup()` |
| 点击XXX | `click_by_text("XXX")` |
| 在XXX输入YYY | `input_text_by_id("XXX", "YYY")` |
| 向上/下滑动 | `swipe("up/down")` |
| 按返回键 | `press_key("back")` |
| 开始监听Toast | `start_toast_watch()` |
| 验证Toast包含XXX | `assert_toast("XXX")` |

### 执行输出格式

```
执行 xxx.yaml (N个用例)

━━━ 用例1: 用例名 ━━━
  ✅ 终止App
  ✅ 启动App
  ✅ 等待2秒
  ✅ 检测页面（无弹窗）
  ✅ 点击登录
  ✅ 验证: 首页
✅ 用例1通过

━━━ 完成 ━━━
通过: N/N
```

### 降级策略

当 MCP 工具返回 `fallback=vision` 时：
1. 调用 `screenshot_with_som` 获取 SoM 截图
2. 识别目标元素编号
3. 调用 `click_by_som(编号)` 点击
4. 如还失败，尝试 `close_popup` 后重试

---

## 📊 飞书多维表格批量执行

当用户说"执行飞书用例"或"继续执行飞书用例"时，按以下规则执行：

### 飞书MCP工具速查

| 工具 | 用途 | 示例 |
|------|------|------|
| `bitable_v1_appTableRecord_search` | 查询用例 | 读取待执行的用例 |
| `bitable_v1_appTableRecord_update` | 更新记录 | 回写执行结果 |
| `bitable_v1_appTableRecord_create` | 创建记录 | 新增用例 |
| `bitable_v1_appTableField_list` | 列出字段 | 获取表格结构 |

### 表格结构要求

| 字段 | 类型 | 说明 |
|------|------|------|
| 用例编号 | 数字 | 唯一标识 |
| 用例名称 | 文本 | 用例名称 |
| 预置条件 | 多行文本 | **前置依赖条件**（重启App、登录状态、会员类型、特殊账号、AB实验等，AI理解自然语言） |
| 测试步骤 | 文本 | 自然语言描述的步骤（通常与预期结果一一对应） |
| 预期结果 | 文本 | 期望的最终状态（与测试步骤一一对应，边执行边验证） |
| 验证点 | 多选 | 最终验证内容（可选） |
| 执行结果 | 文本 | PASS / FAIL |
| 失败原因 | 单选/文本 | 失败时的原因 |

**重要说明**：
1. **预置条件统一管理**：所有前置依赖（重启App、登录状态、会员类型、特殊账号、AB实验等）统一写在"预置条件"字段中，AI理解自然语言后执行
2. **步骤和预期结果一一对应**：通常第1个步骤对应第1个预期结果，第2个步骤对应第2个预期结果
3. **边执行边验证**：每执行一个步骤，立即验证对应的预期结果，不能等所有步骤执行完
4. **混合情况**：
   - 步骤中可能混有预期结果（如"点击登录，验证跳转到首页"）
   - 预期结果中可能混有步骤（如"点击确定按钮"）
   - 需要识别并处理这些混合情况
5. **查询时**：如果不指定 `field_names` 参数，默认会返回所有字段，包括"预期结果"字段

### 预置条件说明

**预置条件字段**支持自然语言描述，AI会自动理解并执行。常见格式：

#### 1. 重启App
```
重启App：是
```
或
```
需要重启App
```

#### 2. 登录状态
```
未登录
```
或
```
需要登录
```

#### 3. 会员类型
```
需要登录，黄金会员
```
或
```
登录状态：已登录-黄金会员
```

#### 4. 特殊账号
```
需要登录，账号：8419-B测试账号
```
或
```
使用特殊账号：VIP账号001
```

#### 5. AB实验
```
AB实验：实验A、实验B
```
或
```
开启实验：8419-B
```

#### 6. 组合条件
```
重启App：是
未登录
AB实验：8419-B
```
或
```
需要重启App，登录黄金会员账号，开启8419-B实验
```

**执行逻辑**：
1. 读取用例的"预置条件"字段
2. AI理解自然语言，识别需要执行的前置操作
3. 按顺序执行：重启App → 登录/登出 → 切换账号 → 开启AB实验等
4. 账号信息从**账号配置表格**中读取（见下方说明）

### 账号配置表格

账号类型、会员类型、特殊账号等信息单独维护在**账号配置表格**中，便于统一管理。

**表格结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| 账号名称 | 文本 | 账号标识（如"8419-B测试账号"、"VIP账号001"） |
| 账号类型 | 单选 | 非会员/基础会员/黄金会员/白金会员/钻石会员 |
| 用户名 | 文本 | 登录用户名 |
| 密码 | 文本 | 登录密码（可选，可加密存储） |
| 备注 | 文本 | 其他说明信息 |

**读取账号信息**：
```python
# 从账号配置表格查询账号信息
# 注意：必须先获取账号配置表格的Token，不能使用占位符
account_table_token = get_account_table_token()  # 从用户输入或配置获取
account_table_id = get_account_table_id()  # 从用户输入或配置获取

if not account_table_token or not account_table_id:
    raise ValueError("账号配置表格Token缺失，请提供账号配置表格的URL或Token")

account_info = bitable_v1_appTableRecord_search(
    path={"app_token": account_table_token, "table_id": account_table_id},
    query={"page_size": 500},
    body={
        "filter": {
            "conjunction": "and",
            "conditions": [
                {"field_name": "账号名称", "operator": "is", "value": ["8419-B测试账号"]}
            ]
        }
    }
)
```

### 执行流程

#### 步骤1：读取飞书用例

**执行顺序**：
1. 优先执行执行结果为空的用例，再执行执行结果为FAIL的用例
2. 所有用例按用例编号从小到大依次执行

```python
# 方式1：优先查询执行结果为空的用例（待执行）
空用例 = bitable_v1_appTableRecord_search(
    path={"app_token": "表格Token", "table_id": "表ID"},
    data={
        "filter": {
            "conjunction": "and",
            "conditions": [
                {"field_name": "执行结果", "operator": "isEmpty"}
            ]
        },
        "sort": [{"field_name": "用例编号", "desc": False}]
    },
    params={"page_size": 10}
)

# 如果空的用例执行完或不足，再查询执行结果为FAIL的用例（重试）
if len(空用例["items"]) < 10:
    FAIL用例 = bitable_v1_appTableRecord_search(
        path={"app_token": "表格Token", "table_id": "表ID"},
        data={
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {"field_name": "执行结果", "operator": "is", "value": ["FAIL"]}
                ]
            },
            "sort": [{"field_name": "用例编号", "desc": False}]
        },
        params={"page_size": 10 - len(空用例["items"])}
    )
    # 合并用例列表：先执行完所有空用例，再执行FAIL用例
    # 两个列表都已按用例编号从小到大排序，合并后顺序正确
    用例列表 = 空用例["items"] + FAIL用例["items"]
else:
    用例列表 = 空用例["items"]  # 已按用例编号从小到大排序
```

#### 步骤2：处理预置条件

执行用例前，先处理预置条件：

```python
def handle_preconditions(case):
    """处理用例的预置条件"""
    precondition = case["fields"].get("预置条件", "").strip()
    if not precondition:
        return
    
    # AI理解预置条件文本，识别需要执行的操作
    # 1. 识别是否需要重启App
    if "重启App" in precondition or "需要重启" in precondition:
        terminate_app("com.qiyi.video.lite")
        launch_app("com.qiyi.video.lite")
        wait(2)
    
    # 2. 识别登录状态要求
    if "未登录" in precondition:
        # 确保未登录状态
        ensure_logged_out()
    elif "需要登录" in precondition or "登录" in precondition:
        # 需要登录，进一步判断会员类型和特殊账号
        account_name = None
        member_type = None
        
        # 提取特殊账号名称（如"账号：8419-B测试账号"）
        import re
        account_match = re.search(r"账号[：:]\s*([^\n，,]+)", precondition)
        if account_match:
            account_name = account_match.group(1).strip()
        
        # 提取会员类型（如"黄金会员"、"白金会员"等）
        for mt in ["钻石会员", "白金会员", "黄金会员", "基础会员", "非会员"]:
            if mt in precondition:
                member_type = mt
                break
        
        # 执行登录
        if account_name:
            # 使用特殊账号登录（从账号配置表格查询）
            login_with_special_account(account_name)
        elif member_type:
            # 使用指定会员类型账号登录（从账号配置表格查询）
            login_with_member_type(member_type)
        else:
            # 普通登录
            login_with_default_account()
    
    # 3. 识别AB实验要求
    ab_match = re.search(r"AB实验[：:]\s*([^\n，,]+)", precondition)
    if ab_match:
        experiment = ab_match.group(1).strip()
        enable_experiment(experiment)

def login_with_special_account(account_name, account_table_token=None, account_table_id=None):
    """使用特殊账号登录（从账号配置表格查询）"""
    # 检查账号配置表格Token
    if not account_table_token or not account_table_id:
        raise ValueError("账号配置表格Token缺失，请提供账号配置表格的URL或Token")
    
    # 从账号配置表格查询账号信息
    account_info = bitable_v1_appTableRecord_search(
        path={"app_token": account_table_token, "table_id": account_table_id},
        query={"page_size": 10},
        body={
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {"field_name": "账号名称", "operator": "is", "value": [account_name]}
                ]
            }
        }
    )
    
    if account_info["data"]["items"]:
        account = account_info["data"]["items"][0]["fields"]
        username = account.get("用户名", "")
        password = account.get("密码", "")
        # 执行登录操作
        login(username, password)
    else:
        raise ValueError(f"未找到账号: {account_name}")

def login_with_member_type(member_type, account_table_token=None, account_table_id=None):
    """使用指定会员类型账号登录（从账号配置表格查询）"""
    # 检查账号配置表格Token
    if not account_table_token or not account_table_id:
        raise ValueError("账号配置表格Token缺失，请提供账号配置表格的URL或Token")
    
    # 从账号配置表格查询该会员类型的账号
    account_info = bitable_v1_appTableRecord_search(
        path={"app_token": account_table_token, "table_id": account_table_id},
        query={"page_size": 10},
        body={
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {"field_name": "账号类型", "operator": "is", "value": [member_type]}
                ]
            }
        }
    )
    
    if account_info["data"]["items"]:
        # 随机选择一个账号（避免账号被锁定）
        import random
        account = random.choice(account_info["data"]["items"])["fields"]
        username = account.get("用户名", "")
        password = account.get("密码", "")
        # 执行登录操作
        login(username, password)
    else:
        raise ValueError(f"未找到{member_type}类型的账号")
```

#### 步骤3：执行每条用例

```python
# 按用例编号从小到大依次执行（用例列表已排序）
for 用例 in 用例列表[:10]:  # 最多10条
    record_id = 用例["record_id"]
    用例编号 = 用例["fields"]["用例编号"]
    
    # 先处理预置条件
    handle_preconditions(用例)
    steps = 用例["fields"]["测试步骤"]  # 可能是文本或列表
    预期结果 = 用例["fields"].get("预期结果", [])  # 读取预期结果字段
    verify = 用例["fields"].get("验证点", [])
    
    # 解析步骤和预期结果（处理文本格式，按行或序号分割）
    steps_list = parse_steps_to_list(steps)  # 将步骤文本解析为步骤列表
    expected_list = parse_expected_to_list(预期结果)  # 将预期结果解析为列表
    
    # 边执行边验证：步骤和预期结果通常一一对应
    for i, step in enumerate(steps_list):
        # 执行步骤
        execute_step(step)  # 调用Mobile MCP
        
        # 立即验证对应的预期结果（如果存在）
        if i < len(expected_list):
            expected = expected_list[i]
            # 如果预期结果中包含操作步骤，先执行操作
            if is_action_in_expected(expected):
                execute_action_from_expected(expected)
            # 验证预期结果
            verify_expected(expected)
        # 如果步骤中混有预期结果，也需要验证
        if has_expected_in_step(step):
            verify_from_step(step)
    
    # 最终验证点（如果有）
    if verify:
        assert_text(verify[0])
    
    # 立即回写结果
    bitable_v1_appTableRecord_update(
        path={"app_token": "...", "table_id": "...", "record_id": record_id},
        data={"fields": {"执行结果": "PASS"}}
    )
```

**关键点**：
1. **步骤和预期结果一一对应**：通常第1个步骤对应第1个预期结果，第2个步骤对应第2个预期结果
2. **边执行边验证**：每执行一个步骤，立即验证对应的预期结果，不能等所有步骤执行完
3. **处理混合情况**：
   - 步骤中包含预期结果（如"点击登录，验证跳转到首页"）→ 执行步骤后立即验证
   - 预期结果中包含步骤（如"点击确定按钮"）→ 识别并执行该操作后再验证

#### 步骤3：分批继续

```python
if 已执行10条:
    # 调用MCP工具打开新会话
    mobile_open_new_chat(
        message="继续执行飞书用例",
        delay=5  # 等待5秒后执行
    )
    # 当前会话结束，新会话自动继续
```

### 步骤失败重试策略（最多5步，禁止循环！）

执行某个步骤失败时，**按顺序尝试以下方法，全部失败就放弃**：

```
步骤: 点击"登录"按钮

尝试1: click_by_text("登录")
  ↓ 失败（元素未找到）

尝试2: list_elements → 找相似文本（如"登 录"、"Login"）→ click_by_text
  ↓ 失败（XML树中没有）

尝试3: screenshot_with_som → 找到编号 → click_by_som(编号)
  ↓ 失败（SoM也没识别到）

尝试4: close_popup() → 关闭可能的弹窗遮挡 → 重试 click_by_text
  ↓ 失败（不是弹窗问题）

尝试5: take_screenshot → AI分析坐标 → click_at_coords(x, y)
  ↓ 失败
━━━ 放弃！标记FAIL，继续下一条用例 ━━━
```

**⚠️ 禁止行为**：
- 不要无限重试同一个步骤
- 不要反复滑动查找超过3次
- 不要重复截图超过2次
- 5步全试过必须放弃，写明失败原因

### 失败标注规则

| 失败场景 | 失败原因 |
|---------|---------|
| 元素找不到 | 元素未找到: {文本} |
| 视觉识别失败 | SoM识别失败 |
| 验证不通过 | 验证失败: 未找到"{验证点}" |
| 超时 | 操作超时 |
| 设备断开 | 设备连接失败 |

### 回写飞书示例

**重要：执行结果必须使用 "PASS" 或 "FAIL"，不要使用 "✅通过" 或 "❌失败"**

```python
# 成功用例（必须使用 "PASS"）
bitable_v1_appTableRecord_update(
    path={
        "app_token": "L4x6bKk41advCQs94nMc2p7onTg",
        "table_id": "tbl1INs6U51p2qWQ",
        "record_id": "recXXXXXXXX"
    },
    data={
        "fields": {"执行结果": "PASS"}
    }
)

# 失败用例（必须使用 "FAIL"）
bitable_v1_appTableRecord_update(
    path={
        "app_token": "L4x6bKk41advCQs94nMc2p7onTg",
        "table_id": "tbl1INs6U51p2qWQ",
        "record_id": "recXXXXXXXX"
    },
    data={
        "fields": {
            "执行结果": "FAIL",
            "失败原因": "元素未找到"  # 或其他失败类型
        }
    }
)
```

### 表格Token获取

**重要**：执行用例前，必须先获取表格Token。Token可以从以下方式获取：

#### 1. 从用户输入获取
- 用户直接提供表格URL
- 用户直接提供 app_token 和 table_id

#### 2. 从飞书表格URL解析
```
URL格式: https://xxx.feishu.cn/base/{app_token}?table={table_id}&view={view_id}

解析方法:
- app_token: URL中 base/ 后面的部分
- table_id: URL中 table= 后面的部分（不含&view等后续参数）
- view_id: URL中 view= 后面的部分（可选）

示例:
URL: https://xxx.feishu.cn/base/ABC123?table=tblXXX&view=vewYYY
→ app_token = ABC123
→ table_id = tblXXX
→ view_id = vewYYY (可选)
```

#### 3. 从配置或环境变量获取
如果项目中有配置文件或环境变量存储Token，优先使用。

#### 4. 主动询问用户
如果无法获取Token，必须主动询问用户：
- "请提供测试用例表格的URL或Token"
- "请提供账号配置表格的URL或Token"

**执行前检查清单**：
- ✅ 确认已获取测试用例表格的 app_token 和 table_id
- ✅ 如果需要登录特殊账号，确认已获取账号配置表格的 app_token 和 table_id
- ❌ **禁止使用占位符**：不能使用 "XXXX"、"YYYYY" 等占位符执行，必须获取真实Token
- ❌ **Token缺失时禁止执行**：如果Token缺失，必须询问用户，不能继续执行

**表格类型说明**：
- **测试用例表格**：用于读取用例、更新执行结果
- **账号配置表格**：用于查询账号信息（用户名、密码、会员类型等），仅在需要登录特殊账号时使用

### 输出格式

```
执行飞书用例 (批次1, 用例1-10)

━━━ 用例1: 切换账号 ━━━
  📋 预置条件: 需要重启App、已登录状态
  ✅ 预置条件: 终止App
  ✅ 预置条件: 启动App
  ✅ 预置条件: 确保已登录状态
  ✅ 步骤1: 关闭弹窗
  ✅ 验证: 弹窗已关闭
  ✅ 步骤2: 点击我的
  ✅ 验证: 进入我的页面
  ✅ 步骤3: 点击设置
  ✅ 验证: 进入设置页面
  ✅ 步骤4: 点击切换账号
  ✅ 验证: Toast提示"账号切换成功"
  📝 回写飞书: PASS
✅ 用例1通过

━━━ 用例2: 浏览电影 ━━━
  ✅ 步骤1: 启动App
  ✅ 验证: App已启动
  ❌ 步骤2: 点击双雄出击 (元素未找到)
     → 尝试SoM识别...
     → 编号5是目标元素
  ✅ click_by_som(5)
  ✅ 验证: 进入电影播放页
  📝 回写飞书: PASS
✅ 用例2通过

... (执行到第10条)

━━━ 批次1完成 (10/10) ━━━
⏰ 5秒后打开新会话继续执行...

[调用 mobile_open_new_chat]
```

**注意**：每个步骤执行后立即验证对应的预期结果，体现"边执行边验证"的逻辑。

### 新会话继续

新会话打开后，AI会收到消息"继续执行飞书用例"，然后：
1. 优先读取飞书表格，找到"执行结果"为空的用例
2. 如果空的用例执行完，再读取"执行结果"为FAIL的用例
3. 从下一批开始执行
4. 重复直到所有用例执行完毕

---

## 🎯 完整执行示例

当用户说 **"执行飞书用例"** 时的完整流程：

```
用户: 执行飞书用例

AI:
1️⃣ [飞书MCP] 读取用例
   # 优先查询执行结果为空的用例
   bitable_v1_appTableRecord_search(执行结果为空)
   → 获取到8条待执行用例
   # 如果不足10条，再查询执行结果为FAIL的用例
   bitable_v1_appTableRecord_search(执行结果=FAIL)
   → 获取到4条FAIL用例
   → 总计12条用例（8条待执行 + 4条重试）

2️⃣ [批次1] 执行用例1-10

   ━━━ 用例1: 切换账号 ━━━
   [预置条件] 读取"预置条件"字段
   [预置条件] AI理解：需要重启App、已登录状态
   [预置条件] [Mobile MCP] terminate_app("com.qiyi.video.lite") ✅
   [预置条件] [Mobile MCP] launch_app("com.qiyi.video.lite") ✅
   [预置条件] [Mobile MCP] wait(2) ✅
   [预置条件] [Mobile MCP] 确保已登录状态 ✅
   [步骤1] [Mobile MCP] list_elements() → 检测到弹窗
   [Mobile MCP] close_popup() ✅
   [验证] list_elements() → 验证弹窗已关闭 ✅
   [步骤2] [Mobile MCP] click_by_text("我的") ✅
   [验证] list_elements() → 验证进入我的页面 ✅
   [步骤3] [Mobile MCP] click_by_text("设置") ✅
   [验证] list_elements() → 验证进入设置页面 ✅
   [步骤4] [Mobile MCP] click_by_text("切换账号") ✅
   [步骤5] [Mobile MCP] start_toast_watch() ✅
   [步骤6] [Mobile MCP] click_by_text("梦醒初八") ✅
   [验证] [Mobile MCP] get_toast() → "账号切换成功" ✅
   [飞书MCP] update_record(执行结果="PASS") ✅
   ✅ 用例1通过

   ... (用例2-10) ...

   ━━━ 批次1完成 (10/12) ━━━
   
3️⃣ [Mobile MCP] mobile_open_new_chat("继续执行飞书用例")
   ⏰ 5秒后自动打开新会话...

--- 新会话 ---

用户: 继续执行飞书用例

AI:
1️⃣ [飞书MCP] 读取用例
   # 优先查询执行结果为空的用例
   bitable_v1_appTableRecord_search(执行结果为空)
   → 获取到0条待执行用例（已全部执行完）
   # 再查询执行结果为FAIL的用例
   bitable_v1_appTableRecord_search(执行结果=FAIL)
   → 获取到2条FAIL用例（需要重试）

2️⃣ [批次2] 执行用例11-12
   ... 执行 ...

   ━━━ 全部完成 (12/12) ━━━
   通过: 11条
   失败: 1条
```

---

## ⚠️ 注意事项

### 1. 权限要求
- **飞书应用**: 需要多维表格读写权限
- **macOS辅助功能**: 系统设置 → 隐私与安全 → 辅助功能 → 添加Cursor

### 2. 表格URL解析
从飞书URL中提取Token：
```
URL: https://xxx.feishu.cn/base/ABC123?table=tblXXX&view=vewYYY

app_token = ABC123
table_id = tblXXX
```

### 3. 错误恢复
如果执行中断：
- 已执行的用例状态已保存在飞书
- 说"继续执行飞书用例"会自动从未执行的用例继续

### 4. 并发限制
- 飞书API有调用频率限制
- 每条用例执行后立即回写，避免批量写入
