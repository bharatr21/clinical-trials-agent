"use client";

import { deleteConversation, getConversation, getConversations } from "@/lib/api";
import type { ConversationDetail, ConversationSummary, Message } from "@/types";
import type React from "react";
import { useCallback, useEffect, useState } from "react";

interface UseConversationReturn {
  /** List of conversation summaries */
  conversations: ConversationSummary[];
  /** Currently active conversation ID */
  currentConversationId: string | null;
  /** Messages in the current conversation */
  messages: Message[];
  /** Whether conversations are loading */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Start a new conversation */
  newConversation: () => void;
  /** Select an existing conversation */
  selectConversation: (id: string) => Promise<void>;
  /** Delete a conversation */
  removeConversation: (id: string) => Promise<void>;
  /** Refresh the conversations list */
  refreshConversations: () => Promise<void>;
  /** Set the current conversation ID (used when agent returns new ID) */
  setCurrentConversationId: (id: string | null) => void;
  /** Add a message to the current conversation */
  addMessage: (message: Message) => void;
  /** Update the last message in the conversation */
  updateLastMessage: (update: Partial<Message>) => void;
  /** Set messages directly (supports functional updates) */
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
}

export function useConversation(): UseConversationReturn {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load conversations on mount
  const refreshConversations = useCallback(async () => {
    try {
      const response = await getConversations();
      setConversations(response.conversations);
    } catch (err) {
      console.error("Failed to load conversations:", err);
      setError(err instanceof Error ? err.message : "Failed to load conversations");
    }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  // Start a new conversation
  const newConversation = useCallback(() => {
    setCurrentConversationId(null);
    setMessages([]);
    setError(null);
  }, []);

  // Select an existing conversation
  const selectConversation = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const detail: ConversationDetail = await getConversation(id);
      setCurrentConversationId(id);

      const transformedMessages: Message[] = [];
      let pendingSqlQuery: string | null = null;

      for (const m of detail.messages) {
        if (m.role !== "user" && m.role !== "assistant") continue;

        const sqlQuery = m.tool_calls?.[0]?.args?.query ?? null;
        if (sqlQuery) pendingSqlQuery = sqlQuery;

        if (!m.content.trim()) continue;

        transformedMessages.push({
          id: m.id,
          role: m.role as "user" | "assistant",
          content: m.content,
          sqlQuery: m.role === "assistant" ? sqlQuery || pendingSqlQuery : null,
        });

        if (m.role === "assistant") pendingSqlQuery = null;
      }

      setMessages(transformedMessages);
    } catch (err) {
      console.error("Failed to load conversation:", err);
      setError(err instanceof Error ? err.message : "Failed to load conversation");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Delete a conversation
  const removeConversation = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id);
        setConversations((prev) => prev.filter((c) => c.id !== id));

        // If we deleted the current conversation, start a new one
        if (currentConversationId === id) {
          newConversation();
        }
      } catch (err) {
        console.error("Failed to delete conversation:", err);
        setError(err instanceof Error ? err.message : "Failed to delete conversation");
      }
    },
    [currentConversationId, newConversation],
  );

  // Add a message to the current conversation
  const addMessage = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  // Update the last message
  const updateLastMessage = useCallback((update: Partial<Message>) => {
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      return [...prev.slice(0, -1), { ...last, ...update }];
    });
  }, []);

  return {
    conversations,
    currentConversationId,
    messages,
    isLoading,
    error,
    newConversation,
    selectConversation,
    removeConversation,
    refreshConversations,
    setCurrentConversationId,
    addMessage,
    updateLastMessage,
    setMessages,
  };
}
