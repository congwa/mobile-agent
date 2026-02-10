/**
 * AI 正文内容组件
 *
 * 参照 embedease-ai 的 TimelineContentItem，使用 Markdown 渲染
 */

import { MessageContent } from "@/components/prompt-kit/message";
import { cn } from "@/utils/tailwind";

interface TimelineContentItemProps {
  item: { type: "assistant.content"; id: string; turnId: string; text: string; ts: number };
}

export function TimelineContentItem({ item }: TimelineContentItemProps) {
  if (!item.text) return null;

  return (
    <MessageContent
      className={cn(
        "prose dark:prose-invert flex-1 rounded-lg bg-transparent p-0",
        "text-foreground prose-strong:text-foreground"
      )}
      markdown
    >
      {item.text}
    </MessageContent>
  );
}
