/**
 * 工具调用组件
 *
 * 参照 embedease-ai 的 TimelineToolCallItem，增加 mobile-mcp 特有的截图支持
 */

import { useState } from "react";
import { Loader2, Check, XCircle, Wrench, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/utils/tailwind";
import { api } from "@/lib/api";
import type { ToolCallItem, ItemStatus } from "@embedease/chat-sdk";

interface TimelineToolCallItemProps {
  item: ToolCallItem;
}

const STATUS_CONFIG: Record<
  ItemStatus,
  { icon: React.ReactNode; className: string }
> = {
  running: {
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    className: "bg-secondary text-muted-foreground border-border",
  },
  success: {
    icon: <Check className="h-4 w-4" />,
    className: "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
  },
  error: {
    icon: <XCircle className="h-4 w-4" />,
    className: "bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
  },
  empty: {
    icon: <Check className="h-4 w-4 opacity-60" />,
    className: "bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
  },
};

function getStatusText(item: ToolCallItem): string {
  const label = item.label || item.name;
  switch (item.status) {
    case "running":
      return `${label}中…`;
    case "success":
      return `${label}完成`;
    case "error":
      return `${label}失败`;
    case "empty":
      return `${label}无结果`;
    default:
      return label;
  }
}

export function TimelineToolCallItem({ item }: TimelineToolCallItemProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const config = STATUS_CONFIG[item.status];
  const showStats = item.status !== "running";

  // mobile-mcp 特有：截图支持
  const raw = item as unknown as Record<string, unknown>;
  const screenshotId = raw.screenshot_id as string | undefined;

  const inputStr: string | null = item.input
    ? typeof item.input === "string"
      ? item.input
      : JSON.stringify(item.input)
    : null;

  const hasDetails = Boolean(inputStr) || Boolean(screenshotId) || Boolean(item.error);

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      {/* Header */}
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-2 text-sm transition-all",
          hasDetails && "cursor-pointer",
          config.className
        )}
        onClick={() => hasDetails && setIsExpanded(!isExpanded)}
      >
        <Wrench className="h-4 w-4 opacity-60" />
        {config.icon}
        <span className="font-medium text-xs">{getStatusText(item)}</span>
        {showStats && item.elapsedMs !== undefined && (
          <span className="text-[10px] opacity-70">· {item.elapsedMs}ms</span>
        )}
        {item.error && (
          <span className="text-xs opacity-70 ml-auto truncate max-w-[200px]">{item.error}</span>
        )}
        {hasDetails && (
          <span className="ml-auto shrink-0">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 opacity-50" />
            ) : (
              <ChevronRight className="h-4 w-4 opacity-50" />
            )}
          </span>
        )}
      </div>

      {/* Details */}
      {isExpanded && hasDetails && (
        <div className="border-t border-border bg-background/50 p-3 space-y-2">
          {inputStr && (
            <div className="rounded bg-secondary/50 px-2 py-1 font-mono text-[11px] text-muted-foreground truncate">
              {inputStr}
            </div>
          )}
          {item.error && (
            <p className="text-xs text-red-400">{item.error}</p>
          )}
          {screenshotId && (
            <img
              src={api.getScreenshotUrl(screenshotId)}
              alt="截图"
              className="max-h-40 rounded-md border border-border/40"
            />
          )}
        </div>
      )}
    </div>
  );
}
