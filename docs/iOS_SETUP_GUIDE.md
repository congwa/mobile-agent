# iOS 自动化配置指南

本文档详细介绍如何配置 Mobile MCP 支持 iOS 设备自动化。

## 📋 环境要求

| 要求 | 说明 |
|------|------|
| 操作系统 | **macOS**（必须，Windows/Linux 不支持） |
| Xcode | 15.0+ （建议 16.0+，支持最新 iOS） |
| Apple ID | 免费账号即可（限制安装 3 个 App） |
| iOS 设备 | iPhone/iPad，通过 **USB 数据线**连接 |
| Python | 3.9 或更高版本 |
| Homebrew | 用于安装 libimobiledevice |

## 🚀 快速开始

### 第一步：安装依赖

```bash
# 安装 tidevice 和 facebook-wda
pip3 install tidevice facebook-wda

# 安装 libimobiledevice（用于 iproxy）
brew install libimobiledevice
```

### 第二步：连接 iOS 设备

1. 用 USB 数据线连接 iPhone 到 Mac
2. iPhone 上点击"信任此电脑"
3. 验证连接：

```bash
tidevice list
```

应该看到类似输出：
```
UDID                       SerialNumber    NAME            MarketName      ProductVersion  ConnType
00008110-000C31D426D9801E  XXXXXX          我的iPhone      iPhone 13       18.5            USB
```

## 🔧 WebDriverAgent 编译安装

WebDriverAgent (WDA) 是 iOS 自动化的核心组件，需要用 Xcode 编译安装到设备上。

### 步骤 1：克隆 WebDriverAgent 项目

```bash
git clone https://github.com/appium/WebDriverAgent.git
cd WebDriverAgent
open WebDriverAgent.xcodeproj
```

### 步骤 2：配置签名

在 Xcode 中：

1. 左侧选择 **WebDriverAgent** 项目（蓝色图标）
2. 中间 TARGETS 选择 **WebDriverAgentRunner**
3. 点击 **Signing & Capabilities** 标签
4. ✅ 勾选 **Automatically manage signing**
5. **Team** 选择你的 Apple ID
6. **Bundle Identifier** 改成唯一的，例如：
   ```
   com.facebook.WebDriverAgentRunner.你的名字
   ```

> ⚠️ Bundle Identifier 必须唯一，建议加上你的名字或公司名

### 步骤 3：配置 IntegrationApp（可选但推荐）

重复上面的签名配置，选择 **IntegrationApp** target。

### 步骤 4：选择设备并编译

1. Xcode 顶部 Scheme 选择器 → 选择 **WebDriverAgentRunner**
2. 设备选择器 → 选择你的 iPhone
3. 按 **⌘ + U**（或菜单 Product → Test）

### 步骤 5：信任开发者（首次安装）

首次安装会提示"不受信任的开发者"，需要在 iPhone 上操作：

**设置 → 通用 → VPN与设备管理 → 点击你的开发者账号 → 信任**

然后回到 Xcode 再按一次 ⌘ + U

### 步骤 6：验证安装成功

Xcode 控制台会显示类似：
```
ServerURLHere->http://192.168.x.x:8100<-ServerURLHere
```

## 🌐 端口转发

WDA 在设备上运行后，需要通过 iproxy 将端口转发到本地：

```bash
iproxy 8100 8100
```

验证连接：
```bash
curl http://localhost:8100/status
```

成功响应：
```json
{
  "value": {
    "message": "WebDriverAgent is ready to accept commands",
    "state": "success",
    "ready": true
  }
}
```

## ⚙️ 配置 Mobile MCP

### 方式 1：Cursor MCP 配置（推荐）

编辑 `~/.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "mobile_mcp.mcp_server"],
      "cwd": "/path/to/mobile_mcp",
      "env": {
        "MOBILE_DEVICE_ID": "auto",
        "DEFAULT_PLATFORM": "ios",
        "IOS_SUPPORT_ENABLED": "true"
      }
    }
  }
}
```

### 方式 2：.env 文件

在项目根目录创建 `.env` 文件：

```bash
# 平台配置
DEFAULT_PLATFORM=ios

# iOS 支持
IOS_SUPPORT_ENABLED=true

# 设备 ID（auto=自动选择）
MOBILE_DEVICE_ID=auto

# 日志级别
LOG_LEVEL=INFO
```

### 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `DEFAULT_PLATFORM` | 默认平台 (`ios` 或 `android`) | `android` |
| `IOS_SUPPORT_ENABLED` | 是否启用 iOS 支持 | `true` |
| `MOBILE_DEVICE_ID` | 设备 ID，`auto` 自动选择 | `auto` |

## 🔄 每次使用流程

### 启动 WDA

每次重启电脑或断开 iPhone 后，需要重新启动 WDA：

**方式 1：Xcode（推荐）**
1. 打开 WebDriverAgent.xcodeproj
2. 选择 WebDriverAgentRunner scheme
3. 选择你的 iPhone
4. 按 ⌘ + U

**方式 2：tidevice（可能不支持新版 iOS）**
```bash
tidevice wdaproxy -B com.facebook.WebDriverAgentRunner.你的名字.xctrunner
```

### 端口转发

```bash
iproxy 8100 8100
```

### 验证连接

```bash
curl http://localhost:8100/status
```

## 📱 可用的 MCP 工具

| 工具 | 功能 |
|------|------|
| `mobile_check_connection` | 检查设备连接状态 |
| `mobile_take_screenshot` | 截图 |
| `mobile_get_screen_size` | 获取屏幕尺寸 |
| `mobile_list_elements` | 列出页面元素 |
| `mobile_click_by_text` | 通过文字点击 |
| `mobile_click_by_id` | 通过 ID 点击 |
| `mobile_click_at_coords` | 通过坐标点击 |
| `mobile_swipe` | 滑动屏幕 |
| `mobile_input_text_by_id` | 输入文字 |
| `mobile_launch_app` | 启动应用 |
| `mobile_terminate_app` | 关闭应用 |
| `mobile_press_key` | 按键（home/back） |
| `mobile_wait` | 等待指定时间 |

## ❗ 常见问题

### Q1: curl: (7) Failed to connect to localhost port 8100

**原因**：WDA 服务未启动

**解决**：
1. 在 Xcode 中按 ⌘ + U 启动 WDA
2. 运行 `iproxy 8100 8100`

### Q2: 免费开发者账号 App 数量限制

**错误**：`This device has reached the maximum number of installed apps using a free developer profile`

**原因**：免费账号最多安装 3 个开发者 App

**解决**：
```bash
# 查看已安装的开发者 App
tidevice applist | grep -i wda

# 卸载不需要的 App
tidevice uninstall com.xxx.xxx
```

### Q3: tidevice 不支持新版 iOS

**错误**：`InvalidService` 或下载 DeviceSupport 失败

**原因**：tidevice 对 iOS 18+ 支持有限

**解决**：使用 Xcode 直接启动 WDA（⌘ + U），然后用 iproxy 转发端口

### Q4: 不受信任的开发者

**解决**：iPhone 上进入 **设置 → 通用 → VPN与设备管理** → 信任开发者账号

### Q5: Bundle Identifier 冲突

**解决**：修改 Bundle Identifier 为唯一值，如 `com.facebook.WebDriverAgentRunner.你的名字`

## 🔀 切换平台

### 切换到 iOS

编辑 `~/.cursor/mcp.json`：
```json
"DEFAULT_PLATFORM": "ios"
```

### 切换到 Android

编辑 `~/.cursor/mcp.json`：
```json
"DEFAULT_PLATFORM": "android"
```

> ⚠️ 修改配置后需要重启 Cursor 生效

## ✅ 快速检查清单

配置完成后，确保以下所有项目都已完成：

- [ ] macOS 系统
- [ ] 已安装 Xcode
- [ ] 已安装 `tidevice` 和 `facebook-wda`
- [ ] 已安装 `libimobiledevice`（iproxy）
- [ ] iPhone 通过 USB 连接且已信任电脑
- [ ] WebDriverAgent 已编译安装到 iPhone
- [ ] 已在 iPhone 上信任开发者证书
- [ ] WDA 服务已启动（Xcode ⌘+U）
- [ ] iproxy 端口转发已运行
- [ ] `curl http://localhost:8100/status` 返回成功
- [ ] MCP 配置已设置 `DEFAULT_PLATFORM=ios`
- [ ] 已重启 Cursor 使配置生效

## 🎯 完整流程总结

```
┌─────────────────────────────────────────────────────────┐
│                    首次配置（一次性）                      │
├─────────────────────────────────────────────────────────┤
│  1. 安装依赖：pip3 install tidevice facebook-wda        │
│  2. 安装 iproxy：brew install libimobiledevice          │
│  3. 克隆 WebDriverAgent 项目                            │
│  4. Xcode 配置签名 → 编译安装到 iPhone（⌘+U）            │
│  5. iPhone 信任开发者证书                                │
│  6. 配置 MCP：DEFAULT_PLATFORM=ios                      │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                    每次使用                              │
├─────────────────────────────────────────────────────────┤
│  1. USB 连接 iPhone                                     │
│  2. Xcode 启动 WDA（⌘+U）                               │
│  3. 终端运行：iproxy 8100 8100                          │
│  4. 验证：curl http://localhost:8100/status             │
│  5. 开始使用 Mobile MCP 自动化！                         │
└─────────────────────────────────────────────────────────┘
```

## 📚 参考资料

- [WebDriverAgent GitHub](https://github.com/appium/WebDriverAgent)
- [tidevice GitHub](https://github.com/alibaba/taobao-iphone-device)
- [facebook-wda GitHub](https://github.com/openatx/facebook-wda)
- [Appium WDA 文档](http://appium.io/docs/en/drivers/ios-xcuitest/)

---

**最后更新**：2025年12月

