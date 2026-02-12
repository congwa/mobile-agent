/**
 * Agent Store - 管理聊天、连接状态
 *
 * 使用 SDK createChatStoreSlice 管理聊天状态，
 * 通过 onEvent 回调处理 screenshot_id 注入。
 */

import { create } from "zustand";
import { type TimelineItem } from "@embedease/chat-sdk";
import {
  createChatStoreSlice,
  type ChatStoreState,
} from "@embedease/chat-sdk-react";
import { api, getApiRoot, type StatusResponse } from "@/lib/api";

interface AgentState extends ChatStoreState {
  // 连接状态
  status: StatusResponse | null;
  statusLoading: boolean;

  // Derived
  timeline: () => TimelineItem[];

  // Actions
  fetchStatus: () => Promise<void>;
  stopStreaming: () => void;
  newConversation: () => void;
}

export const useAgentStore = create<AgentState>((set, get) => {
  // SDK slice 提供核心聊天功能
  const sdkSlice = createChatStoreSlice({
    baseUrl: () => getApiRoot(),
    userId: "default",
    onEvent: (event, storeApi) => {
      // tool.end 后注入 screenshot_id（SDK reducer 不处理此自定义字段）
      if (event.type === "tool.end") {
        const payload = event.payload as { tool_call_id?: string; screenshot_id?: string };
        const screenshotId = payload.screenshot_id;
        const toolCallId = payload.tool_call_id;
        if (screenshotId && toolCallId) {
          const { timelineState } = storeApi.getState();
          const idx = timelineState.indexById[toolCallId];
          if (idx !== undefined) {
            const timeline = [...timelineState.timeline];
            const item = timeline[idx];
            if (item && item.type === "tool.call") {
              timeline[idx] = { ...item, screenshot_id: screenshotId } as typeof item;
              storeApi.setState({
                timelineState: { ...timelineState, timeline },
              });
            }
          }
        }
      }
      return event;
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  })(set as any, get as any);

  return {
    ...sdkSlice,

    // 连接状态
    status: null,
    statusLoading: false,

    // Derived
    timeline: () => get().timelineState.timeline,

    // 连接状态查询
    fetchStatus: async () => {
      set({ statusLoading: true });
      try {
        const status = await api.getStatus();
        set({ status });
      } catch {
        set({ status: null });
      } finally {
        set({ statusLoading: false });
      }
    },

    // 自定义停止：额外通知后端取消 Agent 任务（防止手机继续执行操作）
    stopStreaming: () => {
      const { conversationId } = get();
      get().abortStream();
      if (conversationId) {
        api.abortChat(conversationId).catch(() => {});
      }
    },

    // 新会话
    newConversation: () => {
      get().abortStream();
      get().clearMessages();
      set({ conversationId: "" });
    },
  };
});
