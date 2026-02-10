/**
 * 用户消息组件
 *
 * 参照 embedease-ai 的 TimelineUserMessageItem，使用 Markdown 渲染
 */

import { cn } from "@/utils/tailwind";
import { Markdown } from "@/components/ui/markdown";
import type { UserMessageItem } from "@embedease/chat-sdk";

interface TimelineUserMessageItemProps {
  item: UserMessageItem;
}

export function TimelineUserMessageItem({ item }: TimelineUserMessageItemProps) {
  const hasContent = item.content && item.content.trim().length > 0;
  if (!hasContent) return null;

  return (
    <div
      className={cn(
        "max-w-[85%] sm:max-w-[75%] rounded-2xl rounded-br-md",
        "bg-primary/15 border border-primary/20 px-4 py-2.5"
      )}
    >
      <div className="prose prose-sm dark:prose-invert max-w-none text-sm text-foreground">
        <Markdown>{item.content}</Markdown>
      </div>
      <p className="mt-1 text-right text-[10px] text-muted-foreground">
        {new Date(item.ts).toLocaleTimeString("zh-CN", { hour12: false })}
      </p>
    </div>
  );
}
