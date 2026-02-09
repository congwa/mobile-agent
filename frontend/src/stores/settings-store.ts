/**
 * Settings Store - 管理 LLM/MCP/Agent/中间件配置
 */

import { create } from "zustand";
import {
  api,
  type SettingsResponse,
  type SettingsUpdateRequest,
  type TestLLMResponse,
} from "@/lib/api";

interface SettingsState {
  settings: SettingsResponse | null;
  loading: boolean;
  saving: boolean;
  testResult: TestLLMResponse | null;
  testLoading: boolean;
  reconnectLoading: boolean;
  reconnectResult: { success: boolean; message: string } | null;

  fetchSettings: () => Promise<void>;
  updateSettings: (data: SettingsUpdateRequest) => Promise<void>;
  testLLM: () => Promise<void>;
  reconnectMCP: () => Promise<void>;
  clearTestResult: () => void;
  clearReconnectResult: () => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  loading: false,
  saving: false,
  testResult: null,
  testLoading: false,
  reconnectLoading: false,
  reconnectResult: null,

  fetchSettings: async () => {
    set({ loading: true });
    try {
      const settings = await api.getSettings();
      set({ settings });
    } catch {
      // ignore
    } finally {
      set({ loading: false });
    }
  },

  updateSettings: async (data: SettingsUpdateRequest) => {
    set({ saving: true });
    try {
      const settings = await api.updateSettings(data);
      set({ settings });
    } catch {
      // ignore
    } finally {
      set({ saving: false });
    }
  },

  testLLM: async () => {
    set({ testLoading: true, testResult: null });
    try {
      const result = await api.testLLM();
      set({ testResult: result });
    } catch (err) {
      set({
        testResult: {
          success: false,
          message: (err as Error).message,
          model: "",
          latency_ms: 0,
        },
      });
    } finally {
      set({ testLoading: false });
    }
  },

  reconnectMCP: async () => {
    set({ reconnectLoading: true, reconnectResult: null });
    try {
      const result = await api.reconnectMCP();
      set({ reconnectResult: { success: result.success, message: result.message } });
    } catch (err) {
      set({
        reconnectResult: {
          success: false,
          message: (err as Error).message,
        },
      });
    } finally {
      set({ reconnectLoading: false });
    }
  },

  clearTestResult: () => set({ testResult: null }),
  clearReconnectResult: () => set({ reconnectResult: null }),
}));
