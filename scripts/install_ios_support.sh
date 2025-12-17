#!/bin/bash
# iOS 自动化支持一键安装脚本
# 
# 使用方法：
#   chmod +x scripts/install_ios_support.sh
#   ./scripts/install_ios_support.sh
#
# 功能：
#   1. 安装 tidevice 和 facebook-wda
#   2. 检查 Xcode 命令行工具
#   3. 检查设备连接状态
#   4. 提供后续步骤指引

set -e

echo "🍎 iOS 自动化支持安装脚本"
echo "=================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在 macOS 上
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ 错误：iOS 自动化仅支持 macOS${NC}"
    exit 1
fi

echo "📦 步骤 1/4: 安装 Python 依赖..."
echo "-----------------------------------"

# 安装 tidevice 和 facebook-wda（兼容 pip 和 pip3）
if command -v pip3 &> /dev/null; then
    pip3 install tidevice facebook-wda --quiet
elif command -v pip &> /dev/null; then
    pip install tidevice facebook-wda --quiet
else
    python3 -m pip install tidevice facebook-wda --quiet
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ tidevice 和 facebook-wda 安装成功${NC}"
else
    echo -e "${RED}❌ 安装失败，请检查 pip 环境${NC}"
    exit 1
fi

echo ""
echo "🔧 步骤 2/4: 检查 Xcode 命令行工具..."
echo "-----------------------------------"

# 检查 xcode-select
if xcode-select -p &> /dev/null; then
    XCODE_PATH=$(xcode-select -p)
    echo -e "${GREEN}✅ Xcode 命令行工具已安装: $XCODE_PATH${NC}"
else
    echo -e "${YELLOW}⚠️  Xcode 命令行工具未安装${NC}"
    echo "   正在安装..."
    xcode-select --install
    echo "   请在弹出的对话框中点击'安装'，完成后重新运行此脚本"
    exit 0
fi

echo ""
echo "📱 步骤 3/4: 检查已连接的 iOS 设备..."
echo "-----------------------------------"

# 使用 tidevice 列出设备
DEVICES=$(tidevice list 2>/dev/null || echo "")

if [ -n "$DEVICES" ] && [ "$DEVICES" != "[]" ]; then
    echo -e "${GREEN}✅ 发现以下 iOS 设备:${NC}"
    tidevice list
else
    echo -e "${YELLOW}⚠️  未发现 iOS 设备${NC}"
    echo "   请确保:"
    echo "   1. iOS 设备已通过 USB 连接"
    echo "   2. 设备已解锁"
    echo "   3. 设备已信任此电脑（会弹出对话框）"
fi

echo ""
echo "📋 步骤 4/4: 后续步骤..."
echo "-----------------------------------"
echo ""
echo -e "${YELLOW}⚠️  重要：首次使用需要用 Xcode 编译 WebDriverAgent${NC}"
echo ""
echo "请按以下步骤操作："
echo ""
echo "1. 克隆 WebDriverAgent:"
echo "   git clone https://github.com/appium/WebDriverAgent.git"
echo "   cd WebDriverAgent"
echo ""
echo "2. 用 Xcode 打开项目:"
echo "   open WebDriverAgent.xcodeproj"
echo ""
echo "3. 在 Xcode 中配置签名:"
echo "   - 选择 'WebDriverAgentRunner' target"
echo "   - 点击 'Signing & Capabilities'"
echo "   - 选择你的 Apple ID 团队"
echo "   - 勾选 'Automatically manage signing'"
echo ""
echo "4. 编译并安装到设备:"
echo "   - 连接 iOS 设备"
echo "   - 选择设备作为运行目标"
echo "   - 点击 Product -> Test (或按 Cmd+U)"
echo ""
echo "5. 编译成功后，运行以下命令启动 WDA 代理:"
echo "   tidevice wdaproxy -B com.facebook.WebDriverAgentRunner.xctrunner"
echo ""
echo "6. 验证连接:"
echo "   curl http://localhost:8100/status"
echo ""
echo "=================================="
echo -e "${GREEN}✅ 安装脚本执行完成！${NC}"
echo ""
echo "📚 更多帮助请参考: docs/iOS_QUICK_START.md"

