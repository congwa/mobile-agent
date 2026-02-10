/**
 * LLM 调用组组件
 *
 * 参照 embedease-ai 的 LLMCallCluster，移除 theme 系统
 * 包含推理过程（可折叠）和正文内容
 */

import { useState } from "react";
import { Brain, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { cn } from "@/utils/tailwind";
import type { LLMCallClusterItem } from "@embedease/chat-sdk";
import { TimelineReasoningItem } from "./TimelineReasoningItem";
import { TimelineContentItem } from "./TimelineContentItem";

interface LLMCallClusterProps {
  item: LLMCallClusterItem;
  isStreaming?: boolean;
}

export function LLMCallCluster({ item, isStreaming = false }: LLMCallClusterProps) {
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false);

  const contentItems = item.children.filter((c) => c.type === "content");
  const reasoningItems = item.children.filter((c) => c.type === "reasoning");

  const hasReasoning = reasoningItems.length > 0;
  const isRunning = item.status === "running";

  return (
    <div className="flex flex-col gap-3">
      {/* 1. 推理过程 - 可折叠 */}
      {hasReasoning && (
        <div className="rounded-lg overflow-hidden border border-border">
          <button
            className={cn(
              "w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors cursor-pointer",
              "bg-secondary/50 hover:bg-secondary/80 text-muted-foreground"
            )}
            onClick={() => setIsReasoningExpanded(!isReasoningExpanded)}
          >
            <Brain className="h-3.5 w-3.5 opacity-60" />
            {isRunning && <Loader2 className="h-3 w-3 animate-spin" />}
            <span className="text-xs font-medium">AI 思考过程</span>
            {item.elapsedMs !== undefined && !isRunning && (
              <span className="text-[10px] opacity-50">· {item.elapsedMs}ms</span>
            )}
            <div className="ml-auto">
              {isReasoningExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 opacity-50" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 opacity-50" />
              )}
            </div>
          </button>

          {isReasoningExpanded && (
            <div className="p-3 space-y-3 border-t border-border bg-background/50">
              {reasoningItems.map((child) => (
                <TimelineReasoningItem
                  key={child.id}
                  item={{
                    type: "assistant.reasoning",
                    id: child.id,
                    turnId: "",
                    text: child.text,
                    isOpen: child.isOpen,
                    ts: child.ts,
                  }}
                  isStreaming={isStreaming}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* 2. AI 回复内容 */}
      {contentItems.map((child) => (
        <TimelineContentItem
          key={child.id}
          item={{
            type: "assistant.content",
            id: child.id,
            turnId: "",
            text: child.text,
            ts: child.ts,
          }}
        />
      ))}
    </div>
  );
}
