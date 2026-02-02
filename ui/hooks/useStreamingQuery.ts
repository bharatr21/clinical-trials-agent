"use client";

import { streamQuery } from "@/lib/api";
import type { StreamEvent } from "@/types";
import { useCallback, useRef, useState } from "react";

interface UseStreamingQueryReturn {
  /** Whether a query is currently streaming */
  isStreaming: boolean;
  /** Current streamed content */
  streamedContent: string;
  /** Current SQL query being executed */
  currentSqlQuery: string | null;
  /** Current agent stage label */
  currentStage: string | null;
  /** Error message if any */
  error: string | null;
  /** Execute a streaming query */
  executeQuery: (
    question: string,
    conversationId?: string,
    callbacks?: StreamCallbacks,
  ) => Promise<StreamResult | null>;
  /** Cancel the current query */
  cancelQuery: () => void;
}

interface StreamCallbacks {
  /** Called when agent stage changes */
  onStage?: (stage: string, label: string) => void;
  /** Called for each token received */
  onToken?: (token: string) => void;
  /** Called when SQL query is received */
  onSql?: (query: string) => void;
  /** Called when streaming completes */
  onComplete?: (result: StreamResult) => void;
  /** Called on error, includes optional error code for specific handling (e.g., "rate_limit") */
  onError?: (error: string, code?: string) => void;
}

export interface StreamResult {
  conversationId: string;
  answer: string;
  sqlQuery: string | null;
}

export function useStreamingQuery(): UseStreamingQueryReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedContent, setStreamedContent] = useState("");
  const [currentSqlQuery, setCurrentSqlQuery] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const executeQuery = useCallback(
    async (
      question: string,
      conversationId?: string,
      callbacks?: StreamCallbacks,
    ): Promise<StreamResult | null> => {
      // Cancel any existing query
      cancelQuery();

      setIsStreaming(true);
      setStreamedContent("");
      setCurrentSqlQuery(null);
      setCurrentStage(null);
      setError(null);

      abortControllerRef.current = new AbortController();

      try {
        let result: StreamResult | null = null;

        for await (const event of streamQuery(question, conversationId)) {
          // Check if cancelled
          if (abortControllerRef.current?.signal.aborted) {
            break;
          }

          if (event.type === "stage" && event.label) {
            setCurrentStage(event.label);
            callbacks?.onStage?.(event.stage || "", event.label);
          } else if (event.type === "token" && event.content) {
            setStreamedContent((prev) => prev + event.content);
            callbacks?.onToken?.(event.content);
          } else if (event.type === "sql" && event.query) {
            setCurrentSqlQuery(event.query);
            callbacks?.onSql?.(event.query);
          } else if (event.type === "done") {
            result = {
              conversationId: event.conversation_id || "",
              answer: event.answer || "",
              sqlQuery: event.sql_query ?? null,
            };
            callbacks?.onComplete?.(result);
          } else if (event.type === "error") {
            const errorMsg = event.message || "An error occurred";
            setError(errorMsg);
            callbacks?.onError?.(errorMsg, event.code);
          }
        }

        return result;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "An error occurred";
        setError(errorMsg);
        callbacks?.onError?.(errorMsg);
        return null;
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [cancelQuery],
  );

  return {
    isStreaming,
    streamedContent,
    currentSqlQuery,
    currentStage,
    error,
    executeQuery,
    cancelQuery,
  };
}
