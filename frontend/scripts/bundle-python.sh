#!/bin/bash
# ============================================================
# 打包 Python 环境到 Electron 安装包
#
# 功能：
# 1. 在项目根目录创建独立的 .venv_bundle 虚拟环境
# 2. 安装所有 MCP Server 运行时依赖
# 3. Electron Forge 的 extraResource 会将其打入安装包
#
# 用法：
#   cd frontend && bash scripts/bundle-python.sh
#   然后执行 npm run make 打包
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$FRONTEND_DIR")"
BUNDLE_VENV="$PROJECT_ROOT/.venv_bundle"
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"

echo "============================================"
echo "  打包 Python 环境"
echo "============================================"
echo "项目根目录: $PROJECT_ROOT"
echo "虚拟环境:   $BUNDLE_VENV"
echo ""

# 1. 检查 Python
PYTHON_CMD="${PYTHON:-python3}"
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "→ 使用 Python: $($PYTHON_CMD --version 2>&1)"

# 2. 创建虚拟环境
if [ -d "$BUNDLE_VENV" ]; then
    echo "→ 清理旧虚拟环境..."
    rm -rf "$BUNDLE_VENV"
fi

echo "→ 创建虚拟环境..."
"$PYTHON_CMD" -m venv "$BUNDLE_VENV"

# 3. 安装依赖
echo "→ 安装依赖 (from $REQUIREMENTS)..."
"$BUNDLE_VENV/bin/pip" install --upgrade pip -q
"$BUNDLE_VENV/bin/pip" install -r "$REQUIREMENTS" -q

# 4. 清理不需要的文件（减小包体积）
# 注意：保留 .dist-info 目录，Python importlib.metadata 需要它
echo "→ 清理缓存..."
find "$BUNDLE_VENV" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUNDLE_VENV" -name "*.pyc" -delete 2>/dev/null || true
rm -rf "$BUNDLE_VENV/share" 2>/dev/null || true

# 5. 统计大小
VENV_SIZE=$(du -sh "$BUNDLE_VENV" | cut -f1)
echo ""
echo "============================================"
echo "  ✅ Python 环境打包完成"
echo "  大小: $VENV_SIZE"
echo "  路径: $BUNDLE_VENV"
echo "============================================"
echo ""
echo "下一步: cd frontend && npm run make"
