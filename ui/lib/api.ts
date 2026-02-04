import type {
  ConversationDetail,
  ConversationListResponse,
  QueryResponse,
  StreamEvent,
} from "@/types";

import { getClientId, setClientId } from "./clientId";
import { getOpenAIApiKey } from "./settings";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Check if a URL is secure (HTTPS or localhost)
 */
function isSecureUrl(url: string): boolean {
  return url.startsWith("https://") || url.includes("localhost") || url.includes("127.0.0.1");
}

/**
 * Wrapper for fetch that includes client ID and optional OpenAI API key headers
 */
async function fetchWithClientId(url: string, options: RequestInit = {}): Promise<Response> {
  const clientId = getClientId();
  const openaiApiKey = getOpenAIApiKey();

  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (clientId) {
    headers.set("X-Client-ID", clientId);
  }
  if (openaiApiKey && isSecureUrl(url)) {
    headers.set("X-OpenAI-API-Key", openaiApiKey);
  }

  const response = await fetch(url, { ...options, headers });

  // Store backend-generated client ID if present
  const newClientId = response.headers.get("X-Client-ID");
  if (newClientId) {
    setClientId(newClientId);
  }

  return response;
}

/**
 * Query the agent with a question
 */
export async function queryAgent(
  question: string,
  conversationId?: string
): Promise<QueryResponse> {
  const response = await fetchWithClientId(`${API_BASE_URL}/api/v1/query`, {
    method: "POST",
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Stream the agent response token-by-token
 */
export async function* streamQuery(
  question: string,
  conversationId?: string,
  signal?: AbortSignal
): AsyncGenerator<StreamEvent> {
  const clientId = getClientId();
  const openaiApiKey = getOpenAIApiKey();

  const streamUrl = `${API_BASE_URL}/api/v1/query/stream`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (clientId) {
    headers["X-Client-ID"] = clientId;
  }
  if (openaiApiKey && isSecureUrl(streamUrl)) {
    headers["X-OpenAI-API-Key"] = openaiApiKey;
  }

  const response = await fetch(streamUrl, {
    method: "POST",
    headers,
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
    }),
    signal,
  });

  // Store backend-generated client ID if present
  const newClientId = response.headers.get("X-Client-ID");
  if (newClientId) {
    setClientId(newClientId);
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel();
        break;
      }

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events
      const lines = buffer.split("\n\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6)) as StreamEvent;
            yield data;
          } catch {
            console.warn("Failed to parse SSE event:", line);
          }
        }
      }
    }
  } finally {
    if (signal?.aborted) {
      await reader.cancel();
    }
  }
}

/**
 * Get list of conversations
 */
export async function getConversations(
  limit = 50,
  offset = 0
): Promise<ConversationListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  const response = await fetchWithClientId(`${API_BASE_URL}/api/v1/conversations?${params}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Get a single conversation with messages
 */
export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  const response = await fetchWithClientId(
    `${API_BASE_URL}/api/v1/conversations/${conversationId}`
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Delete a conversation
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await fetchWithClientId(
    `${API_BASE_URL}/api/v1/conversations/${conversationId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
