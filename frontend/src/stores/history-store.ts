/**
 * History Store - 管理会话历史
 */

import { create } from "zustand";
import {
  api,
  type ConversationSummary,
  type ConversationDetail,
} from "@/lib/api";

interface HistoryState {
  conversations: ConversationSummary[];
  total: number;
  selectedConversation: ConversationDetail | null;
  searchQuery: string;
  loading: boolean;
  detailLoading: boolean;

  fetchConversations: (query?: string) => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  setSearchQuery: (query: string) => void;
  clearSelection: () => void;
}

export const useHistoryStore = create<HistoryState>((set, get) => ({
  conversations: [],
  total: 0,
  selectedConversation: null,
  searchQuery: "",
  loading: false,
  detailLoading: false,

  fetchConversations: async (query?: string) => {
    const q = query ?? get().searchQuery;
    set({ loading: true });
    try {
      const resp = await api.getConversations(q);
      set({ conversations: resp.conversations, total: resp.total });
    } catch {
      set({ conversations: [], total: 0 });
    } finally {
      set({ loading: false });
    }
  },

  selectConversation: async (id: string) => {
    set({ detailLoading: true });
    try {
      const detail = await api.getConversation(id);
      set({ selectedConversation: detail });
    } catch {
      set({ selectedConversation: null });
    } finally {
      set({ detailLoading: false });
    }
  },

  deleteConversation: async (id: string) => {
    try {
      await api.deleteConversation(id);
      const { selectedConversation } = get();
      if (selectedConversation?.id === id) {
        set({ selectedConversation: null });
      }
      await get().fetchConversations();
    } catch {
      // ignore
    }
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query });
  },

  clearSelection: () => {
    set({ selectedConversation: null });
  },
}));
