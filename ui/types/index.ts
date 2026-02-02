/**
 * TypeScript types for the Clinical Trials Agent API
 */

/**
 * A message in a conversation (frontend representation)
 */
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sqlQuery?: string | null;
}

/**
 * API message response (from backend)
 */
export interface ApiMessage {
  id: string;
  role: string;
  content: string;
  tool_calls?: Array<{ name?: string; args?: { query?: string } }> | null;
}

/**
 * Summary of a conversation for listing
 */
export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

/**
 * Detailed conversation with messages (from API)
 */
export interface ConversationDetail {
  id: string;
  title: string;
  messages: ApiMessage[];
  created_at: string;
  updated_at: string;
}

/**
 * Response from the conversations list endpoint
 */
export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
}

/**
 * Request to query the agent
 */
export interface QueryRequest {
  question: string;
  conversation_id?: string;
}

/**
 * Response from the query endpoint
 */
export interface QueryResponse {
  answer: string;
  sql_query: string | null;
  conversation_id: string;
}

/**
 * Streaming event types
 */
export type StreamEventType = "stage" | "token" | "sql" | "done" | "error";

/**
 * Streaming event from the query stream endpoint
 */
export interface StreamEvent {
  type: StreamEventType;
  /** Stage identifier (for stage events) */
  stage?: string;
  /** Human-readable stage label (for stage events) */
  label?: string;
  /** Token content (for token events) */
  content?: string;
  /** SQL query (for sql events) */
  query?: string;
  /** Conversation ID (for done events) */
  conversation_id?: string;
  /** Final answer (for done events) */
  answer?: string;
  /** Final SQL query (for done events) */
  sql_query?: string | null;
  /** Error message (for error events) */
  message?: string;
  /** Error code (for error events, e.g., "rate_limit") */
  code?: string;
}
