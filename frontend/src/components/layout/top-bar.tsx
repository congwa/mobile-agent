import { Plus, Settings } from "lucide-react";
import { Link } from "@tanstack/react-router";
import ConnectionIndicator from "@/components/layout/connection-indicator";
import { useAgentStore } from "@/stores/agent-store";

export default function TopBar() {
  const { status, newConversation } = useAgentStore();

  return (
    <div className="flex h-11 items-center justify-between border-b border-border bg-card/50 px-4">
      <div className="flex items-center gap-3">
        <ConnectionIndicator connected={status?.mcp_connected ?? false} size="md" />
        <span className="text-sm text-muted-foreground">
          {status?.ready ? `${status.tools_count} 个工具就绪` : "Agent 未就绪"}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={newConversation}
          className="flex items-center gap-1.5 rounded-md border border-border bg-secondary/50 px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
        >
          <Plus className="h-3.5 w-3.5" />
          新建会话
        </button>
        <Link
          to="/settings"
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer"
        >
          <Settings className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
