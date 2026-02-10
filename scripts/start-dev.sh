#!/bin/bash
#
# 一键启动测试环境（开发模式）
#
# 启动顺序：
#   1. MCP Server (port 3100) — 手机设备控制
#   2. Backend API (port 8088) — FastAPI Agent 服务
#   3. Frontend (Electron)     — 测试执行界面
#
# 特性：
#   - 自动杀掉占用端口的旧进程
#   - 所有子进程日志实时输出到控制台
#   - Ctrl+C 优雅关闭所有进程
#
# 前提条件：
#   - 手机已连接电脑（USB/WiFi）
#   - agent-app/.env 已配置 LLM API Key
#   - 测试 App 已安装在设备上
#
# 用法：
#   bash scripts/start-dev.sh
#   bash scripts/start-dev.sh --no-frontend  # 不启动前端（仅后端）
#
# 停止：Ctrl+C 会优雅关闭所有进程
#

set -e

# ── 路径 ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENT_APP="$PROJECT_ROOT/agent-app"
FRONTEND="$PROJECT_ROOT/frontend"
MCP_SERVER="$PROJECT_ROOT/mcp_tools/mcp_server.py"

# ── 参数 ──────────────────────────────────────────────────
NO_FRONTEND=false
for arg in "$@"; do
  case $arg in
    --no-frontend) NO_FRONTEND=true ;;
  esac
done

# ── Python 路径 ───────────────────────────────────────────
if [ -f "$PROJECT_ROOT/.venv_bundle/bin/python" ]; then
  MCP_PYTHON="$PROJECT_ROOT/.venv_bundle/bin/python"
elif [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
  MCP_PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
  MCP_PYTHON="python"
fi

# ── 端口 ──────────────────────────────────────────────────
MCP_PORT=3100
BACKEND_PORT=8088

# ── 颜色 ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# ── PID 追踪 ──────────────────────────────────────────────
PIDS=()

cleanup() {
  echo ""
  echo -e "${YELLOW}━━━ 正在关闭所有服务 ━━━${NC}"
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  sleep 2
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
  echo -e "${GREEN}所有服务已关闭${NC}"
  exit 0
}

trap cleanup INT TERM

wait_for_port() {
  local port=$1
  local name=$2
  local timeout=${3:-30}
  local elapsed=0
  while [ $elapsed -lt $timeout ]; do
    if nc -z localhost "$port" 2>/dev/null; then
      return 0
    fi
    sleep 0.5
    elapsed=$((elapsed + 1))
  done
  echo -e "${RED}$name 启动超时 (port $port)${NC}"
  return 1
}

# ── 杀掉占用端口的进程 ───────────────────────────────────
kill_port() {
  local port=$1
  local name=$2
  local pids
  pids=$(lsof -i ":$port" -sTCP:LISTEN -t 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo -e "${YELLOW}  杀掉 $name 旧进程 (port $port, pid: $pids)${NC}"
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 1
    # 强制杀
    pids=$(lsof -i ":$port" -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -n "$pids" ]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
      sleep 0.5
    fi
  fi
}

echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Mobile Agent 测试环境启动脚本          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. 启动 MCP Server ───────────────────────────────────
echo -e "${GREEN}[1/3] MCP Server (port $MCP_PORT)${NC}"
kill_port $MCP_PORT "MCP Server"

cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT" $MCP_PYTHON "$MCP_SERVER" --sse --port $MCP_PORT 2>&1 | \
  sed "s/^/$(printf "${MAGENTA}[MCP]${NC} ")/" &
PIDS+=($!)

if wait_for_port $MCP_PORT "MCP Server" 30; then
  echo -e "${GREEN}  ✓ MCP Server 就绪: http://localhost:$MCP_PORT/sse${NC}"
else
  cleanup
fi

# ── 2. 启动 Backend API ──────────────────────────────────
echo -e "${GREEN}[2/3] Backend API (port $BACKEND_PORT)${NC}"
kill_port $BACKEND_PORT "Backend API"

cd "$AGENT_APP"
uv run uvicorn mobile_agent.api.app:app \
  --host 0.0.0.0 \
  --port $BACKEND_PORT \
  --reload \
  --log-level info 2>&1 | \
  sed "s/^/$(printf "${CYAN}[API]${NC} ")/" &
PIDS+=($!)

if wait_for_port $BACKEND_PORT "Backend API" 30; then
  echo -e "${GREEN}  ✓ Backend API 就绪: http://localhost:$BACKEND_PORT${NC}"
else
  cleanup
fi

# ── 3. 启动 Frontend ─────────────────────────────────────
if [ "$NO_FRONTEND" = false ]; then
  echo -e "${GREEN}[3/3] Frontend (Electron)${NC}"
  cd "$FRONTEND"
  npm start 2>&1 | sed "s/^/$(printf "${YELLOW}[FE]${NC}  ")/" &
  PIDS+=($!)
  echo -e "${GREEN}  ✓ Frontend 启动中...${NC}"
else
  echo -e "${YELLOW}[3/3] 跳过 Frontend（--no-frontend）${NC}"
fi

# ── 启动完成 ──────────────────────────────────────────────
echo ""
echo -e "${CYAN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}测试环境已就绪！${NC}"
echo ""
echo -e "  MCP Server:  ${CYAN}http://localhost:$MCP_PORT/sse${NC}"
echo -e "  Backend API: ${CYAN}http://localhost:$BACKEND_PORT${NC}"
echo -e "  API 文档:    ${CYAN}http://localhost:$BACKEND_PORT/docs${NC}"
if [ "$NO_FRONTEND" = false ]; then
  echo -e "  Frontend:    ${CYAN}Electron 窗口${NC}"
fi
echo ""
echo -e "  日志前缀: ${MAGENTA}[MCP]${NC} = MCP Server  ${CYAN}[API]${NC} = Backend  ${YELLOW}[FE]${NC} = Frontend"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo -e "${CYAN}════════════════════════════════════════════${NC}"
echo ""

# 等待所有后台进程（保持脚本运行，日志持续输出）
wait
