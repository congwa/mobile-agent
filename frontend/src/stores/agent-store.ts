/**
 * Agent Store - 管理聊天、连接状态
 *
 * 使用 @embedease/chat-sdk 的 ChatClient + Timeline 管理聊天状态。
 */

import { create } from "zustand";
import {
  ChatClient,
  createInitialState,
  addUserMessage,
  startAssistantTurn,
  timelineReducer,
  clearTurn,
  endTurn,
  type TimelineState,
  type TimelineItem,
  type ChatEvent,
} from "@embedease/chat-sdk";
import { api, API_BASE, type StatusResponse } from "@/lib/api";

interface AgentState {
  // 连接状态
  status: StatusResponse | null;
  statusLoading: boolean;

  // 聊天
  conversationId: string;
  timelineState: TimelineState;
  isStreaming: boolean;

  // 内部
  _client: ChatClient | null;

  // Derived
  timeline: () => TimelineItem[];

  // Actions
  fetchStatus: () => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  stopStreaming: () => void;
  newConversation: () => void;
  setConversationId: (id: string) => void;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  status: null,
  statusLoading: false,
  conversationId: "",
  timelineState: createInitialState(),
  isStreaming: false,
  _client: null,

  timeline: () => get().timelineState.timeline,

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

  sendMessage: async (message: string) => {
    const { conversationId, isStreaming } = get();
    if (isStreaming) return;

    const userMessageId = crypto.randomUUID();
    const assistantTurnId = crypto.randomUUID();

    // 添加用户消息 + 开始助手 Turn
    set((s) => {
      let state = addUserMessage(s.timelineState, userMessageId, message.trim());
      state = startAssistantTurn(state, assistantTurnId);
      return { timelineState: state, isStreaming: true };
    });

    // 创建 ChatClient（使用 SDK 的 SSE 流式客户端）
    const client = new ChatClient({ baseUrl: API_BASE });
    set({ _client: client });

    try {
      for await (const event of client.stream({
        user_id: "default",
        conversation_id: conversationId || crypto.randomUUID(),
        message: message.trim(),
      })) {
        // meta.start 中提取 conversation_id
        if (event.type === "meta.start") {
          const cid = (event as ChatEvent & { conversation_id?: string }).conversation_id;
          if (cid) {
            set({ conversationId: cid });
          }
        }

        // 通过 timelineReducer 处理所有事件
        set((s) => ({
          timelineState: timelineReducer(s.timelineState, event),
        }));
      }

      // 流结束
      set((s) => ({
        timelineState: endTurn(s.timelineState),
        isStreaming: false,
        _client: null,
      }));
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        // 清除当前 turn
        set((s) => ({
          timelineState: clearTurn(s.timelineState, assistantTurnId),
          isStreaming: false,
          _client: null,
        }));
      } else {
        set({ isStreaming: false, _client: null });
      }
    }
  },

  stopStreaming: () => {
    const { _client, timelineState } = get();
    if (_client) {
      _client.abort();
      const turnId = timelineState.activeTurn.turnId;
      if (turnId) {
        set((s) => ({
          timelineState: clearTurn(s.timelineState, turnId),
        }));
      }
      set({ isStreaming: false, _client: null });
    }
  },

  newConversation: () => {
    const { _client } = get();
    if (_client) _client.abort();
    set({
      conversationId: "",
      timelineState: createInitialState(),
      isStreaming: false,
      _client: null,
    });
  },

  setConversationId: (id: string) => {
    set({ conversationId: id });
  },
}));
