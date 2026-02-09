import { useEffect, useCallback } from "react";
import {
  Search,
  CheckCircle2,
  XCircle,
  Trash2,
  Calendar,
  Loader2,
} from "lucide-react";
import { cn } from "@/utils/tailwind";
import { useHistoryStore } from "@/stores/history-store";
import type { ConversationMessage } from "@/lib/api";

export default function HistoryPage() {
  const {
    conversations,
    total,
    selectedConversation,
    searchQuery,
    loading,
    detailLoading,
    fetchConversations,
    selectConversation,
    deleteConversation,
    setSearchQuery,
  } = useHistoryStore();

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleSearch = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const q = e.target.value;
      setSearchQuery(q);
      fetchConversations(q);
    },
    [setSearchQuery, fetchConversations],
  );

  const successCount = conversations.filter((c) => c.status === "success").length;
  const failedCount = conversations.filter((c) => c.status !== "success").length;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border bg-card/50 px-6 py-4">
        <h1 className="text-lg font-semibold text-foreground">历史记录</h1>
        <p className="mt-1 text-sm text-muted-foreground">查看和回放历史会话</p>
      </div>

      <div className="border-b border-border bg-card/30 px-6 py-3">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={handleSearch}
            placeholder="搜索会话..."
            className="w-full rounded-lg border border-border bg-secondary/50 py-2 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-colors"
          />
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* 会话列表 */}
        <div className="w-80 flex-shrink-0 border-r border-border overflow-y-auto">
          {loading && conversations.length === 0 ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              暂无会话记录
            </div>
          ) : (
            conversations.map((session) => (
              <button
                key={session.id}
                onClick={() => selectConversation(session.id)}
                className={cn(
                  "w-full border-b border-border/50 px-4 py-3 text-left transition-colors cursor-pointer",
                  selectedConversation?.id === session.id
                    ? "bg-primary/5 border-l-2 border-l-primary"
                    : "hover:bg-secondary/30",
                )}
              >
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Calendar className="h-3 w-3" />
                  {session.created_at ? new Date(session.created_at).toLocaleString("zh-CN") : ""}
                </div>
                <p className="mt-1 text-sm font-medium text-foreground truncate">
                  {session.summary || "(无摘要)"}
                </p>
                <div className="mt-1.5 flex items-center gap-3 text-xs">
                  <span
                    className={cn(
                      "flex items-center gap-1",
                      session.status === "success" ? "text-green-500" : "text-red-500",
                    )}
                  >
                    {session.status === "success" ? (
                      <CheckCircle2 className="h-3 w-3" />
                    ) : (
                      <XCircle className="h-3 w-3" />
                    )}
                    {session.status === "success" ? "成功" : "失败"}
                  </span>
                  {session.steps > 0 && (
                    <span className="text-muted-foreground">{session.steps} 步</span>
                  )}
                  {session.duration && (
                    <span className="text-muted-foreground">{session.duration}</span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>

        {/* 会话详情 */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {detailLoading ? (
            <div className="flex flex-1 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : selectedConversation ? (
            <>
              <div className="flex items-center justify-between border-b border-border bg-card/30 px-6 py-3">
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {selectedConversation.summary || "(无摘要)"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {selectedConversation.created_at
                      ? new Date(selectedConversation.created_at).toLocaleString("zh-CN")
                      : ""}
                    {selectedConversation.steps > 0 && ` · ${selectedConversation.steps} 步`}
                    {selectedConversation.duration && ` · ${selectedConversation.duration}`}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => deleteConversation(selectedConversation.id)}
                    className="flex items-center gap-1.5 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/20 transition-colors cursor-pointer"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    删除
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-6 space-y-3">
                {selectedConversation.messages.length === 0 ? (
                  <div className="text-center text-sm text-muted-foreground py-8">
                    无消息记录
                  </div>
                ) : (
                  selectedConversation.messages.map((msg) => (
                    <SessionMessageBubble key={msg.id} message={msg} />
                  ))
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-muted-foreground">
              <p className="text-sm">选择一个会话查看详情</p>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border bg-card/50 px-6 py-2.5 text-xs text-muted-foreground">
        总计 {total} 个会话 · 成功{" "}
        <span className="text-green-500">{successCount}</span> · 失败{" "}
        <span className="text-red-500">{failedCount}</span>
      </div>
    </div>
  );
}

function SessionMessageBubble({ message }: { message: ConversationMessage }) {
  if (message.type === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] rounded-2xl rounded-br-md bg-primary/15 border border-primary/20 px-4 py-2.5">
          <p className="text-sm text-foreground">{message.content}</p>
          {message.timestamp && (
            <p className="mt-1 text-right text-[10px] text-muted-foreground">{message.timestamp}</p>
          )}
        </div>
      </div>
    );
  }

  if (message.type === "assistant") {
    return (
      <div className="flex justify-start">
        <div className="max-w-[70%] rounded-2xl rounded-bl-md bg-secondary border border-border px-4 py-2.5">
          <p className="text-sm text-foreground whitespace-pre-wrap">{message.content}</p>
          {message.timestamp && (
            <p className="mt-1 text-[10px] text-muted-foreground">{message.timestamp}</p>
          )}
        </div>
      </div>
    );
  }

  if (message.type === "tool_call" || message.type === "tool_result") {
    return (
      <div className="flex justify-start">
        <div className="max-w-[80%] rounded-lg border border-border bg-secondary/60 px-3 py-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
            {message.tool_name && (
              <span className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-[11px] text-primary">
                {message.tool_name}
              </span>
            )}
            <span className="text-xs text-muted-foreground">{message.content}</span>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
