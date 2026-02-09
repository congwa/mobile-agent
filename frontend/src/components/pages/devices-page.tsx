import { useEffect } from "react";
import {
  Smartphone,
  Plus,
  Server,
  RefreshCw,
  Loader2,
} from "lucide-react";
import ConnectionIndicator from "@/components/layout/connection-indicator";
import { useDeviceStore } from "@/stores/device-store";
import { useSettingsStore } from "@/stores/settings-store";
import type { DeviceInfo as DeviceInfoType, ToolDetail } from "@/lib/api";

export default function DevicesPage() {
  const { devices, tools, mcpConnected, mcpUrl, uptimeSeconds, toolsCount, loading, refresh } =
    useDeviceStore();
  const { reconnectMCP, reconnectLoading } = useSettingsStore();

  useEffect(() => {
    refresh();
  }, [refresh]);

  const formatUptime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    if (m < 60) return `${m}m`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  };

  return (
    <div className="flex h-full flex-col overflow-auto">
      <div className="border-b border-border bg-card/50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-foreground">设备管理</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              管理已连接的设备和 MCP Server 状态
            </p>
          </div>
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-md border border-border bg-secondary/50 px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer disabled:opacity-40"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            刷新
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        <section>
          <h2 className="mb-4 text-sm font-medium text-foreground">设备列表</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {devices.map((device) => (
              <DeviceCard key={device.id} device={device} />
            ))}
            {devices.length === 0 && (
              <div className="rounded-lg border border-dashed border-border bg-card/30 p-8 text-center text-muted-foreground col-span-full">
                <Smartphone className="mx-auto mb-2 h-8 w-8 opacity-30" />
                <p className="text-sm">{mcpConnected ? "暂无设备信息" : "MCP 未连接，无法获取设备"}</p>
              </div>
            )}
            <button className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-card/30 p-8 text-muted-foreground hover:border-primary/30 hover:text-foreground transition-colors cursor-pointer">
              <Plus className="h-6 w-6" />
              <span className="text-sm">添加设备</span>
            </button>
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-sm font-medium text-foreground">MCP Server 状态</h2>
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Server className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">MCP Server</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {mcpUrl}
                  </p>
                </div>
              </div>
              <ConnectionIndicator connected={mcpConnected} size="md" />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div className="rounded-md bg-secondary/50 p-3 text-center">
                <p className="text-lg font-semibold text-foreground">{toolsCount}</p>
                <p className="text-xs text-muted-foreground">可用工具</p>
              </div>
              <div className="rounded-md bg-secondary/50 p-3 text-center">
                <p className={`text-lg font-semibold ${mcpConnected ? "text-primary" : "text-red-500"}`}>
                  {mcpConnected ? "运行中" : "已断开"}
                </p>
                <p className="text-xs text-muted-foreground">状态</p>
              </div>
              <div className="rounded-md bg-secondary/50 p-3 text-center">
                <p className="text-lg font-semibold text-foreground">{formatUptime(uptimeSeconds)}</p>
                <p className="text-xs text-muted-foreground">已运行</p>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={async () => { await reconnectMCP(); refresh(); }}
                disabled={reconnectLoading}
                className="flex items-center gap-1.5 rounded-md border border-border bg-secondary/50 px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors cursor-pointer disabled:opacity-40"
              >
                {reconnectLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                重新连接
              </button>
            </div>
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-sm font-medium text-foreground">
            可用工具 ({tools.length})
          </h2>
          <ToolListTable tools={tools} />
        </section>
      </div>
    </div>
  );
}

function DeviceCard({ device }: { device: DeviceInfoType }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/30">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
            <Smartphone className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">{device.name}</p>
            <p className="text-xs text-muted-foreground">
              {device.platform} {device.version}
            </p>
          </div>
        </div>
        <ConnectionIndicator connected={device.connected} size="sm" />
      </div>
      {device.resolution && (
        <div className="mt-3 flex items-center justify-between text-xs">
          <span className="text-muted-foreground">分辨率</span>
          <span className="text-foreground">{device.resolution}</span>
        </div>
      )}
    </div>
  );
}

function ToolListTable({ tools }: { tools: ToolDetail[] }) {
  if (tools.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card/30 p-8 text-center text-muted-foreground">
        <p className="text-sm">暂无可用工具</p>
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border bg-secondary/30">
            <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">工具名称</th>
            <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">描述</th>
          </tr>
        </thead>
        <tbody>
          {tools.map((tool) => (
            <tr key={tool.name} className="border-b border-border/50 last:border-0 hover:bg-secondary/20 transition-colors">
              <td className="px-4 py-2.5">
                <span className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-primary">{tool.name}</span>
              </td>
              <td className="px-4 py-2.5 text-xs text-muted-foreground">{tool.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
