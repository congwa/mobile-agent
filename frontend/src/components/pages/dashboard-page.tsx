import { useEffect, useMemo, useRef, useState } from "react";
import {
  Play,
  Smartphone,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Square,
  FlaskConical,
  RotateCcw,
} from "lucide-react";
import { cn } from "@/utils/tailwind";
import { api } from "@/lib/api";
import ConnectionIndicator from "@/components/layout/connection-indicator";
import TopBar from "@/components/layout/top-bar";
import { useAgentStore } from "@/stores/agent-store";
import {
  LLMCallCluster,
  TimelineToolCallItem,
  TimelineUserMessageItem,
  TimelineErrorItem,
} from "@/components/timeline";
import type {
  TimelineItem,
  ToolCallItem,
} from "@embedease/chat-sdk";

type TestPhase = "input" | "running" | "done";

const DEFAULT_TEST_CASE = `测试任务名称：测试 App 登录流程
前置条件：App 处于关闭状态
测试步骤：
1. 打开App
2. 等待3秒
3. 关闭弹窗
4. 点击消息
5. 点击立即登录
验证点：显示"登录"或"注册"
com.im30.way`;

export default function DashboardPage() {
  const [testCaseText, setTestCaseText] = useState(DEFAULT_TEST_CASE);
  const [phase, setPhase] = useState<TestPhase>("input");
  const [devicePanelCollapsed, setDevicePanelCollapsed] = useState(false);
  const [logPanelCollapsed, setLogPanelCollapsed] = useState(false);

  const { timelineState, isStreaming, status, fetchStatus, sendMessage, stopStreaming, newConversation } =
    useAgentStore();

  const timeline = timelineState.timeline ?? [];
  const timelineEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [timeline]);

  // 流结束时自动切换到 done
  useEffect(() => {
    if (phase === "running" && !isStreaming && timeline.length > 0) {
      setPhase("done");
    }
  }, [isStreaming, phase, timeline.length]);

  const handleExecute = () => {
    if (isStreaming || !testCaseText.trim()) return;
    newConversation();
    setPhase("running");
    sendMessage(testCaseText.trim());
  };

  const handleReset = () => {
    newConversation();
    setPhase("input");
  };

  // 从 timeline 提取 ToolCallItem 作为操作日志
  const toolItems = useMemo(
    () => (timeline ?? []).filter((item): item is ToolCallItem => item.type === "tool.call"),
    [timeline],
  );

  // 最新截图 ID
  const latestScreenshotId = useMemo(() => {
    for (let i = toolItems.length - 1; i >= 0; i--) {
      const raw = toolItems[i] as unknown as Record<string, unknown>;
      if (raw.screenshot_id) return raw.screenshot_id as string;
    }
    return null;
  }, [toolItems]);

  return (
    <div className="flex h-full flex-col">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        {/* 设备预览面板 */}
        {!devicePanelCollapsed && (
          <div className="flex w-72 flex-col border-r border-border bg-card/50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">设备预览</h3>
              <button
                onClick={() => setDevicePanelCollapsed(true)}
                className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
              >
                <ChevronDown className="h-4 w-4" />
              </button>
            </div>
            <DeviceFrame screenshotId={latestScreenshotId} />
            <DeviceInfoPanel status={status} />
          </div>
        )}
        {devicePanelCollapsed && (
          <button
            onClick={() => setDevicePanelCollapsed(false)}
            className="flex w-8 items-center justify-center border-r border-border bg-card/50 hover:bg-accent transition-colors cursor-pointer"
          >
            <ChevronUp className="h-4 w-4 rotate-90 text-muted-foreground" />
          </button>
        )}

        {/* 主面板 */}
        <div className="flex flex-1 flex-col">
          {/* 阶段：输入 */}
          {phase === "input" && (
            <div className="flex flex-1 flex-col overflow-y-auto p-6">
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-3">
                  <FlaskConical className="h-5 w-5 text-primary" />
                  <h2 className="text-base font-semibold text-foreground">测试用例</h2>
                </div>
                <textarea
                  value={testCaseText}
                  onChange={(e) => setTestCaseText(e.target.value)}
                  placeholder={`测试任务名称：...\n前置条件：...\n测试步骤：\n1. 打开App\n2. 点击xxx\n验证点：...\ncom.example.app`}
                  className="w-full resize-none rounded-lg border border-border bg-secondary/50 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-colors font-mono leading-relaxed"
                  rows={10}
                />
                <div className="mt-3">
                  <button
                    onClick={handleExecute}
                    disabled={!testCaseText.trim() || !status?.ready || isStreaming}
                    className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer shadow-[var(--glow-green)] disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <Play className="h-3.5 w-3.5" />
                    开始执行
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 阶段：运行中 / 完成 */}
          {(phase === "running" || phase === "done") && (
            <>
              {/* 测试摘要栏 */}
              <div className="border-b border-border bg-card/30 px-6 py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <FlaskConical className="h-4 w-4 text-primary flex-shrink-0" />
                    <span className="text-sm font-medium text-foreground truncate">
                      {testCaseText.split("\n")[0].replace(/^测试任务名称[：:]\s*/, "") || "测试执行中"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {phase === "running" && (
                      <button
                        onClick={stopStreaming}
                        className="flex items-center gap-1.5 rounded-md bg-red-500/80 px-3 py-1.5 text-xs text-white hover:bg-red-500 transition-colors cursor-pointer"
                      >
                        <Square className="h-3 w-3" />
                        停止
                      </button>
                    )}
                    {phase === "done" && (
                      <button
                        onClick={handleReset}
                        className="flex items-center gap-1.5 rounded-md border border-border bg-secondary/50 px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
                      >
                        <RotateCcw className="h-3 w-3" />
                        新测试
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* 实时 Timeline */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {timeline.length === 0 && phase === "running" && (
                  <div className="flex h-full items-center justify-center">
                    <div className="text-center text-muted-foreground">
                      <Loader2 className="mx-auto mb-3 h-8 w-8 animate-spin text-primary" />
                      <p className="text-sm">正在初始化测试...</p>
                    </div>
                  </div>
                )}
                {timeline.map((item) => (
                  <TimelineItemBubble key={item.id} item={item} isStreaming={isStreaming} />
                ))}
                {isStreaming && timeline.length > 0 && (
                  <div className="flex justify-start">
                    <div className="rounded-lg border border-border bg-secondary/60 px-3 py-2">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    </div>
                  </div>
                )}
                <div ref={timelineEndRef} />
              </div>
            </>
          )}
        </div>

        {/* 操作日志面板 */}
        {!logPanelCollapsed && (
          <div className="flex w-80 flex-col border-l border-border bg-card/50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">操作日志</h3>
              <button
                onClick={() => setLogPanelCollapsed(true)}
                className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
              >
                <ChevronDown className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <OperationTimeline items={toolItems} />
            </div>
            <OperationSummary items={toolItems} />
          </div>
        )}
        {logPanelCollapsed && (
          <button
            onClick={() => setLogPanelCollapsed(false)}
            className="flex w-8 items-center justify-center border-l border-border bg-card/50 hover:bg-accent transition-colors cursor-pointer"
          >
            <ChevronUp className="h-4 w-4 -rotate-90 text-muted-foreground" />
          </button>
        )}
      </div>
    </div>
  );
}

// ── 设备面板 ─────────────────────────────────────────────────

function DeviceFrame({ screenshotId }: { screenshotId: string | null | undefined }) {
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-48 rounded-2xl border-2 border-border bg-secondary/50 p-1 shadow-lg">
        <div className="mx-auto mb-1 h-1 w-12 rounded-full bg-border" />
        <div className="aspect-[9/19.5] w-full rounded-xl bg-slate-800 flex items-center justify-center overflow-hidden">
          {screenshotId ? (
            <img
              src={api.getScreenshotUrl(screenshotId)}
              alt="设备截图"
              className="h-full w-full object-contain"
            />
          ) : (
            <div className="text-center text-xs text-muted-foreground">
              <Smartphone className="mx-auto mb-2 h-8 w-8 opacity-30" />
              <p>等待截图...</p>
            </div>
          )}
        </div>
        <div className="mx-auto mt-1 h-1 w-8 rounded-full bg-border" />
      </div>
    </div>
  );
}

function DeviceInfoPanel({ status }: { status: { ready: boolean; mcp_connected: boolean; tools_count: number } | null }) {
  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">MCP 状态</span>
        <ConnectionIndicator connected={status?.mcp_connected ?? false} size="sm" />
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">Agent</span>
        <span className={cn("text-xs font-medium", status?.ready ? "text-green-500" : "text-red-500")}>
          {status?.ready ? "就绪" : "未就绪"}
        </span>
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">工具数</span>
        <span className="text-foreground">{status?.tools_count ?? 0}</span>
      </div>
    </div>
  );
}

// ── Timeline Item 渲染 ──────────────────────────────────────

function TimelineItemBubble({ item, isStreaming }: { item: TimelineItem; isStreaming?: boolean }) {
  switch (item.type) {
    case "user.message":
      return (
        <div className="flex justify-end">
          <TimelineUserMessageItem item={item} />
        </div>
      );
    case "llm.call.cluster":
      return (
        <div className="flex justify-start">
          <div className="max-w-[80%] flex flex-col gap-2">
            <LLMCallCluster item={item} isStreaming={isStreaming} />
          </div>
        </div>
      );
    case "tool.call":
      return (
        <div className="flex justify-start">
          <div className="max-w-[80%] w-full">
            <TimelineToolCallItem item={item} />
          </div>
        </div>
      );
    case "error":
      return (
        <div className="flex justify-start">
          <div className="max-w-[70%]">
            <TimelineErrorItem item={item} />
          </div>
        </div>
      );
    default:
      return null;
  }
}


// ── 操作日志面板 ─────────────────────────────────────────────

function OperationTimeline({ items }: { items: ToolCallItem[] }) {
  if (items.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
        暂无操作记录
      </div>
    );
  }
  return (
    <div className="relative space-y-0">
      {items.map((item, index) => {
        const isRunning = item.status === "running";
        const isError = item.status === "error";
        return (
          <div key={item.id} className="relative flex gap-3 pb-4">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-full",
                  isRunning ? "bg-primary/80" : isError ? "bg-red-600" : "bg-green-600",
                )}
              >
                {isRunning ? (
                  <Loader2 className="h-3 w-3 text-white animate-spin" />
                ) : isError ? (
                  <XCircle className="h-3 w-3 text-white" />
                ) : (
                  <CheckCircle2 className="h-3 w-3 text-white" />
                )}
              </div>
              {index < items.length - 1 && (
                <div className="w-px flex-1 bg-border mt-1" />
              )}
            </div>
            <div className="flex-1 -mt-0.5">
              <div className="flex items-center gap-2">
                <span className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] text-primary">
                  {item.name}
                </span>
                {item.elapsedMs !== undefined && (
                  <span className="text-[10px] text-muted-foreground">{item.elapsedMs}ms</span>
                )}
              </div>
              {item.label && (
                <p className="mt-1 text-xs text-muted-foreground truncate">{item.label}</p>
              )}
              {item.error && (
                <p className="mt-1 text-xs text-red-400 truncate">{item.error}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function OperationSummary({ items }: { items: ToolCallItem[] }) {
  const total = items.length;
  const completed = items.filter((i) => i.status === "success").length;
  const running = items.filter((i) => i.status === "running").length;
  const errors = items.filter((i) => i.status === "error").length;

  return (
    <div className="mt-3 rounded-lg border border-border bg-secondary/50 p-3">
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-lg font-semibold text-foreground">{total}</p>
          <p className="text-[10px] text-muted-foreground">工具调用</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-green-500">{completed}</p>
          <p className="text-[10px] text-muted-foreground">完成</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-foreground">{running > 0 ? running : errors}</p>
          <p className="text-[10px] text-muted-foreground">{running > 0 ? "运行中" : "错误"}</p>
        </div>
      </div>
    </div>
  );
}
