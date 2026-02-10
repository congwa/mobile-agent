# 📱 Mobile MCP — Mobile Automation MCP Tools

> 39 mobile automation tools for use with Cursor / Claude / Windsurf and other AI IDEs

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/mobile-mcp-ai.svg?style=flat-square&color=blue)](https://pypi.org/project/mobile-mcp-ai/)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg?style=flat-square)](../LICENSE)

[中文](MCP_README.md) · [Back to Main Project](../README_EN.md)

</div>

---

## 📖 What is this?

Mobile MCP is a toolkit that provides mobile automation capabilities via the MCP (Model Context Protocol) protocol. Once installed, you can control mobile devices directly from any MCP-compatible AI IDE (such as Cursor, Claude Desktop, Windsurf).

**No Agent needed, no Electron Console needed** — just one pip command to get started.

---

## 🚀 Quick Start

### Step 1: Install

```bash
pip install mobile-mcp-ai
```

Upgrade to the latest version:

```bash
pip install --upgrade mobile-mcp-ai
```

Check current version:

```bash
pip show mobile-mcp-ai
```

### Step 2: Connect Device

**Android:**

1. Enable "USB Debugging" on your phone (Settings → Developer Options → USB Debugging)
2. Connect to computer via USB cable
3. Verify connection:

```bash
adb devices
```

Device listed means connection is successful.

**iOS:**

```bash
# Install dependencies
pip install tidevice facebook-wda
brew install libimobiledevice

# Check connection
tidevice list
```

> 📖 iOS requires additional WebDriverAgent setup, see [iOS Setup Guide](iOS_SETUP_GUIDE.md)

### Step 3: Configure AI IDE

#### Cursor Configuration

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "mobile-mcp"
    }
  }
}
```

#### Claude Desktop Configuration

Edit Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "mobile-mcp"
    }
  }
}
```

#### Windsurf Configuration

Edit `~/.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "mobile-mcp"
    }
  }
}
```

> 💡 All IDEs require a **restart** after configuration changes
>
> 💡 Android/iOS devices are auto-detected, no additional configuration needed

### Step 4: Start Using

After restarting the IDE, type in chat:

```
@MCP Check device connection
```

```
@MCP Take a screenshot of the current page
```

```
@MCP Click the "Login" button
```

---

## ⚙️ Advanced Configuration

### Running from Source

If running from source instead of pip install:

**Android Configuration:**

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "mobile_mcp.mcp_tools.mcp_server"],
      "cwd": "/path/to/mobile_mcp",
      "env": {
        "MOBILE_PLATFORM": "android"
      }
    }
  }
}
```

**iOS Configuration:**

```json
{
  "mcpServers": {
    "mobile-automation": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "mobile_mcp.mcp_tools.mcp_server"],
      "cwd": "/path/to/mobile_mcp",
      "env": {
        "MOBILE_PLATFORM": "ios"
      }
    }
  }
}
```

> ⚠️ Replace `/path/to/` with your actual paths

### Environment Variables

Create a `.env` file in the project root for additional configuration, refer to `env.example`:

```bash
# Platform type (auto-detected if not set)
# MOBILE_PLATFORM=android

# Debug mode
# MOBILE_MCP_DEBUG=0

# AI provider (optional, basic tools don't need this)
# AI_PROVIDER=qwen
# QWEN_API_KEY=your-key

# Log level
# LOG_LEVEL=INFO
```

### Batch Test Execution (Feishu Integration)

If you need to batch execute test cases from Feishu multidimensional tables, the `mobile_open_new_chat` feature will automatically open new chat sessions to continue execution.

**macOS Users:** Accessibility permission required

| Step | Action |
|:---:|--------|
| 1 | Open "System Settings" |
| 2 | Click "Privacy & Security" |
| 3 | Click "Accessibility" |
| 4 | Click +, add **Cursor.app** |
| 5 | Ensure toggle is ON ✅ |

> ⚠️ Without this permission, auto-opening new chat sessions won't work

**Windows Users:** Install additional dependencies

```bash
pip install mobile-mcp-ai[windows]
```

Or manually install:

```bash
pip install pyautogui pyperclip pygetwindow
```

---

## 🚀 Usage Examples

Chat directly in your AI IDE:

**Basic Operations**

```
@MCP List all elements on the current page
```

```
@MCP Click the "Login" button
```

```
@MCP Type test123 in the username input field
```

**App Control**

```
@MCP Launch WeChat
```

```
@MCP Open TikTok and swipe up 3 times
```

```
@MCP List all installed apps on the phone
```

**Screenshot Analysis**

```
@MCP Take a screenshot of the current page
```

```
@MCP Take a screenshot, then click the search icon on the page
```

**Test Script Generation**

```
@MCP Test the login flow: enter username and password, click login
```

```
@MCP Generate a pytest test script from the previous operations
```

**Combined Operations**

```
@MCP Open Settings, find WLAN, tap into it and take a screenshot
```

```
@MCP Open WeChat, tap Discover, then tap Moments
```

---

## 🛠️ Tool List

| Category | Tool | Description |
|:---:|------|------|
| 📋 | `mobile_list_elements` | List page elements |
| 📸 | `mobile_take_screenshot` | Take screenshot |
| 📸 | `mobile_screenshot_with_som` | Set-of-Mark screenshot (smart annotation) |
| 📸 | `mobile_screenshot_with_grid` | Screenshot with grid coordinates |
| 📐 | `mobile_get_screen_size` | Screen size |
| 👆 | `mobile_click_by_text` | Click by text |
| 👆 | `mobile_click_by_id` | Click by ID |
| 👆 | `mobile_click_at_coords` | Click by coordinates |
| 👆 | `mobile_click_by_percent` | Click by percentage |
| 👆 | `mobile_click_by_som` | Click by SoM number |
| 👆 | `mobile_long_press_by_id` | Long press by ID |
| 👆 | `mobile_long_press_by_text` | Long press by text |
| 👆 | `mobile_long_press_by_percent` | Long press by percentage |
| 👆 | `mobile_long_press_at_coords` | Long press by coordinates |
| ⌨️ | `mobile_input_text_by_id` | Input by ID |
| ⌨️ | `mobile_input_at_coords` | Input by coordinates |
| 👆 | `mobile_swipe` | Swipe |
| ⌨️ | `mobile_press_key` | Press key |
| ⏱️ | `mobile_wait` | Wait |
| ⌨️ | `mobile_hide_keyboard` | Hide keyboard (essential for login flows) |
| 📦 | `mobile_launch_app` | Launch app |
| 📦 | `mobile_terminate_app` | Terminate app |
| 📦 | `mobile_list_apps` | List apps |
| 📱 | `mobile_list_devices` | List devices |
| 🔌 | `mobile_check_connection` | Check connection |
| 🔍 | `mobile_find_close_button` | Find close button |
| 🚫 | `mobile_close_popup` | Close popup |
| 🚫 | `mobile_close_ad` | Smart close ad popup |
| 🎯 | `mobile_template_close` | Template match close popup |
| ➕ | `mobile_template_add` | Add X button template |
| ✅ | `mobile_assert_text` | Assert text |
| 📜 | `mobile_get_operation_history` | Operation history |
| 🗑️ | `mobile_clear_operation_history` | Clear history |
| 📝 | `mobile_generate_test_script` | Generate test script |

---

## ❓ FAQ

### Q: Can't see MCP tools in Cursor after installation?

1. Confirm `~/.cursor/mcp.json` is correctly configured
2. **Restart Cursor** (fully quit and reopen, not just reload window)
3. Check Cursor settings to see if MCP service shows as connected

### Q: Device not found?

- **Android**: Confirm `adb devices` shows your device
- **iOS**: Confirm `tidevice list` shows your device
- Ensure USB debugging is enabled / computer is trusted

### Q: Click operations not working?

1. Use `@MCP Take a screenshot` to confirm current page state
2. Use `@MCP List page elements` to see available elements
3. Try different click methods (text, ID, coordinates)

### Q: iOS connection failed?

See [iOS Setup Guide](iOS_SETUP_GUIDE.md) to ensure WebDriverAgent is properly installed and running.

---

## 📞 Contact

<div align="center">

<img src="../images/qq.jpg" alt="QQ Group" width="250"/>

*Join QQ Group (Group ID: 1080722489)*

</div>

---

## 📄 License

Apache 2.0
