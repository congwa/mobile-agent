#!/bin/bash
# 发布 mobile-mcp-ai 到 PyPI 的脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🚀 准备发布 mobile-mcp-ai"
echo "=========================================="

# 获取当前版本号
VERSION=$(python3 -c "import re; content=open('setup.py').read(); print(re.search(r'version=\"([^\"]+)\"', content).group(1))")
echo "📦 当前版本: v${VERSION}"

# 确认发布
read -p "确认发布版本 v${VERSION} 到 PyPI? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ 取消发布"
    exit 1
fi

echo ""
echo "=========================================="
echo "🧹 清理旧构建"
echo "=========================================="
rm -rf dist/ build/ *.egg-info/
echo "✅ 清理完成"

echo ""
echo "=========================================="
echo "📦 构建分发包"
echo "=========================================="
python3 -m build
echo "✅ 构建完成"

echo ""
echo "=========================================="
echo "🔍 检查构建产物"
echo "=========================================="
ls -lh dist/
echo ""
python3 -m twine check dist/*
echo "✅ 检查通过"

echo ""
echo "=========================================="
echo "📤 上传到 PyPI"
echo "=========================================="
echo "⚠️  需要输入 PyPI 用户名和密码（或 API Token）"
echo ""
python3 -m twine upload dist/*

echo ""
echo "=========================================="
echo "✅ 发布成功！"
echo "=========================================="
echo "📦 版本: v${VERSION}"
echo "🔗 查看: https://pypi.org/project/mobile-mcp-ai/${VERSION}/"
echo ""
echo "用户可以通过以下命令安装："
echo "  pip install mobile-mcp-ai==${VERSION}"
echo "  pip install --upgrade mobile-mcp-ai"
echo ""



