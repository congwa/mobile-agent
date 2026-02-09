/**
 * Device Store - 管理设备列表和 MCP Server 状态
 */

import { create } from "zustand";
import {
  api,
  type DeviceInfo,
  type ToolDetail,
  type StatusResponse,
} from "@/lib/api";

interface DeviceState {
  devices: DeviceInfo[];
  tools: ToolDetail[];
  mcpConnected: boolean;
  mcpUrl: string;
  uptimeSeconds: number;
  toolsCount: number;
  loading: boolean;

  fetchDevices: () => Promise<void>;
  fetchStatus: () => Promise<void>;
  refresh: () => Promise<void>;
}

export const useDeviceStore = create<DeviceState>((set) => ({
  devices: [],
  tools: [],
  mcpConnected: false,
  mcpUrl: "",
  uptimeSeconds: 0,
  toolsCount: 0,
  loading: false,

  fetchDevices: async () => {
    try {
      const resp = await api.getDevices();
      set({ devices: resp.devices });
    } catch {
      set({ devices: [] });
    }
  },

  fetchStatus: async () => {
    try {
      const status: StatusResponse = await api.getStatus();
      set({
        tools: status.tools,
        mcpConnected: status.mcp_connected,
        mcpUrl: status.mcp_url,
        uptimeSeconds: status.uptime_seconds,
        toolsCount: status.tools_count,
      });
    } catch {
      // ignore
    }
  },

  refresh: async () => {
    set({ loading: true });
    try {
      const [devResp, status] = await Promise.all([
        api.getDevices(),
        api.getStatus(),
      ]);
      set({
        devices: devResp.devices,
        tools: status.tools,
        mcpConnected: status.mcp_connected,
        mcpUrl: status.mcp_url,
        uptimeSeconds: status.uptime_seconds,
        toolsCount: status.tools_count,
      });
    } catch {
      // ignore
    } finally {
      set({ loading: false });
    }
  },
}));
