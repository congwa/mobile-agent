/**
 * AI 推理内容组件
 *
 * 参照 embedease-ai 的 TimelineReasoningItem，使用 Markdown 渲染
 */

import { Markdown } from "@/components/ui/markdown";
import { cn } from "@/utils/tailwind";

interface TimelineReasoningItemProps {
  item: { type: "assistant.reasoning"; id: string; turnId: string; text: string; isOpen?: boolean; ts: number };
  isStreaming?: boolean;
}

export function TimelineReasoningItem({ item }: TimelineReasoningItemProps) {
  if (!item.text) return null;

  return (
    <div className={cn(
      "prose dark:prose-invert prose-sm max-w-none",
      "text-muted-foreground"
    )}>
      <Markdown>{item.text}</Markdown>
    </div>
  );
}
