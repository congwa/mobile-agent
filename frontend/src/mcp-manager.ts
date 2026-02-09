/**
 * MCP Server 进程管理器
 *
 * 由 Electron 主进程调用，负责：
 * 1. 启动 MCP Server（--sse 模式）
 * 2. 监控进程健康
 * 3. 应用退出时清理进程
 */

import { spawn, type ChildProcess } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/** MCP Server 默认端口 */
const MCP_PORT = 3100;

/** MCP Server 子进程 */
let mcpProcess: ChildProcess | null = null;

/**
 * 获取项目根目录（mobile-mcp）
 */
function getProjectRoot(): string {
  const inDevelopment = process.env.NODE_ENV === "development";
  if (inDevelopment) {
    // 开发模式：frontend/ 的上级目录即 mobile-mcp 项目根
    return path.resolve(__dirname, "..", "..");
  }
  return path.resolve(process.resourcesPath);
}

/**
 * 获取 MCP Server 脚本路径
 */
function getMcpServerPath(): string {
  return path.resolve(getProjectRoot(), "mcp_tools", "mcp_server.py");
}

/**
 * 获取 Python 可执行文件路径
 * 优先级：MCP_PYTHON 环境变量 > 项目虚拟环境 > 系统 python
 */
function getPythonPath(): string {
  // 1. 环境变量显式指定
  if (process.env.MCP_PYTHON) {
    return process.env.MCP_PYTHON;
  }

  // 2. 检测项目根目录下的 .venv
  const projectRoot = getProjectRoot();
  const fs = require("fs");
  const venvPaths = [
    path.join(projectRoot, ".venv_bundle", "bin", "python"),        // 打包内嵌环境 (Unix)
    path.join(projectRoot, ".venv_bundle", "Scripts", "python.exe"), // 打包内嵌环境 (Windows)
    path.join(projectRoot, ".venv", "bin", "python"),        // 开发环境 (Unix)
    path.join(projectRoot, ".venv", "Scripts", "python.exe"), // 开发环境 (Windows)
    path.join(projectRoot, "agent-app", ".venv", "bin", "python"),        // agent-app 子目录
    path.join(projectRoot, "agent-app", ".venv", "Scripts", "python.exe"),
  ];

  for (const venvPython of venvPaths) {
    try {
      if (fs.existsSync(venvPython)) {
        console.log(`[MCP] 检测到虚拟环境: ${venvPython}`);
        return venvPython;
      }
    } catch {
      // ignore
    }
  }

  // 3. 系统 python
  return "python";
}

/**
 * 检查 Python 环境是否就绪
 * 验证 Python 可执行 + 核心依赖已安装
 */
function checkPythonReady(pythonCmd: string): { ok: boolean; error?: string } {
  try {
    const { execSync } = require("child_process");
    // 检查 Python 可执行
    execSync(`${pythonCmd} --version`, { timeout: 5000, stdio: "pipe" });
    // 检查核心依赖
    execSync(
      `${pythonCmd} -c "import mcp; import starlette; import uvicorn"`,
      { timeout: 10000, stdio: "pipe" },
    );
    return { ok: true };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("ENOENT") || msg.includes("not found")) {
      return { ok: false, error: `Python 未找到: ${pythonCmd}\n请安装 Python 3.8+ 或设置 MCP_PYTHON 环境变量` };
    }
    return {
      ok: false,
      error: `Python 依赖缺失，请执行:\n  ${pythonCmd} -m pip install -r requirements.txt`,
    };
  }
}

/**
 * 启动 MCP Server（SSE 模式）
 */
export function startMcpServer(): void {
  if (mcpProcess) {
    console.log("[MCP] Server 已在运行中");
    return;
  }

  const scriptPath = getMcpServerPath();
  const pythonCmd = getPythonPath();

  // 启动前检查 Python 环境
  const check = checkPythonReady(pythonCmd);
  if (!check.ok) {
    console.error(`[MCP] Python 环境检查失败: ${check.error}`);
    return;
  }

  console.log(`[MCP] 启动 Server: ${pythonCmd} ${scriptPath} --sse --port ${MCP_PORT}`);

  const cwd = getProjectRoot();
  mcpProcess = spawn(pythonCmd, [scriptPath, "--sse", "--port", String(MCP_PORT)], {
    cwd,
    stdio: ["ignore", "pipe", "pipe"],
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
    },
  });

  mcpProcess.stdout?.on("data", (data: Buffer) => {
    console.log(`[MCP stdout] ${data.toString().trim()}`);
  });

  mcpProcess.stderr?.on("data", (data: Buffer) => {
    console.log(`[MCP stderr] ${data.toString().trim()}`);
  });

  mcpProcess.on("exit", (code, signal) => {
    console.log(`[MCP] Server 退出: code=${code}, signal=${signal}`);
    mcpProcess = null;
  });

  mcpProcess.on("error", (err) => {
    console.error(`[MCP] Server 启动失败:`, err.message);
    mcpProcess = null;
  });
}

/**
 * 停止 MCP Server
 */
export function stopMcpServer(): void {
  if (!mcpProcess) return;

  console.log("[MCP] 正在停止 Server...");
  mcpProcess.kill("SIGTERM");

  // 3 秒后强制杀死
  const forceKillTimer = setTimeout(() => {
    if (mcpProcess) {
      console.log("[MCP] 强制终止 Server");
      mcpProcess.kill("SIGKILL");
      mcpProcess = null;
    }
  }, 3000);

  mcpProcess.on("exit", () => {
    clearTimeout(forceKillTimer);
    mcpProcess = null;
  });
}

/**
 * MCP Server 是否在运行
 */
export function isMcpRunning(): boolean {
  return mcpProcess !== null && !mcpProcess.killed;
}
