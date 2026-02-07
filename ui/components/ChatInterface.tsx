"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { useStreamingQuery } from "@/hooks/useStreamingQuery";
import type { Message } from "@/types";
import { Loader2, MessageSquare, Send, StopCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { useSettingsDialog } from "./SettingsDialog";
import { SqlQueryDisplay } from "./SqlQueryDisplay";

interface ChatInterfaceProps {
  initialQuestion: string | null;
  onQuestionUsed: () => void;
  conversationId: string | null;
  messages: Message[];
  onMessagesChange: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
  onConversationIdChange: (id: string) => void;
  onConversationCreated: () => void;
}

export function ChatInterface({
  initialQuestion,
  onQuestionUsed,
  conversationId,
  messages,
  onMessagesChange,
  onConversationIdChange,
  onConversationCreated,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { openSettings } = useSettingsDialog();
  const { isStreaming, currentStage, executeQuery, cancelQuery } = useStreamingQuery();

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll on message changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (initialQuestion) {
      setInput(initialQuestion);
      onQuestionUsed();
      inputRef.current?.focus();
    }
  }, [initialQuestion, onQuestionUsed]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
    };

    // Add user message
    const newMessages = [...messages, userMessage];
    onMessagesChange(newMessages);
    setInput("");
    setError(null);

    // Add placeholder for assistant message
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
    };
    onMessagesChange([...newMessages, assistantMessage]);

    // Execute streaming query
    const result = await executeQuery(userMessage.content, conversationId || undefined, {
      onToken: (token) => {
        // Update the assistant message content progressively
        onMessagesChange((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg.id === assistantMessageId) {
            return [...prev.slice(0, -1), { ...lastMsg, content: lastMsg.content + token }];
          }
          return prev;
        });
      },
      onSql: (query) => {
        // Update the SQL query on the assistant message
        onMessagesChange((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg.id === assistantMessageId) {
            return [...prev.slice(0, -1), { ...lastMsg, sqlQuery: query }];
          }
          return prev;
        });
      },
      onComplete: (streamResult) => {
        // Update conversation ID if this was a new conversation
        if (!conversationId && streamResult.conversationId) {
          onConversationIdChange(streamResult.conversationId);
          onConversationCreated();
        }

        // Finalize the assistant message
        onMessagesChange((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg.id === assistantMessageId) {
            return [
              ...prev.slice(0, -1),
              {
                ...lastMsg,
                content: streamResult.answer || lastMsg.content,
                sqlQuery: streamResult.sqlQuery,
              },
            ];
          }
          return prev;
        });
      },
      onError: (errorMsg, errorCode) => {
        setError(errorMsg);
        // Remove the empty assistant message on error
        onMessagesChange(newMessages);
        // If API key issue, prompt user to provide their own API key
        if (
          errorCode === "rate_limit" ||
          errorCode === "insufficient_quota" ||
          errorCode === "invalid_api_key"
        ) {
          openSettings(errorCode);
        }
      },
    });

    if (!result) {
      // If streaming failed and we didn't get an error callback
      if (!error) {
        setError("Failed to get a response. Please try again.");
        onMessagesChange(newMessages);
      }
    }
  };

  return (
    <Card className="flex-1 flex flex-col overflow-hidden w-full min-h-0">
      <CardContent className="flex-1 p-0 overflow-auto min-h-0">
        <div className="h-full w-full overflow-auto overflow-x-auto">
          <div className="p-4 space-y-4 w-full min-w-0">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-muted mb-4">
                  <MessageSquare className="h-6 w-6 text-muted-foreground" />
                </div>
                <h3 className="font-medium text-foreground mb-1">Start a conversation</h3>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                  Ask questions about clinical trials, conditions, sponsors, study phases, and more.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <div key={message.id} className="w-full overflow-x-auto">
                <MessageBubble
                  message={message}
                  isStreaming={
                    isStreaming &&
                    message === messages[messages.length - 1] &&
                    message.role === "assistant"
                  }
                  currentStage={
                    isStreaming &&
                    message === messages[messages.length - 1] &&
                    message.role === "assistant"
                      ? currentStage
                      : null
                  }
                />
                {message.sqlQuery && <SqlQueryDisplay query={message.sqlQuery} />}
              </div>
            ))}

            {error && (
              <div className="ml-0 md:ml-11 bg-destructive/10 text-destructive p-3 rounded-lg text-sm border border-destructive/20">
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>
      </CardContent>

      <CardFooter className="border-t p-2 md:p-4">
        <form onSubmit={handleSubmit} className="flex gap-2 w-full">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about clinical trials..."
            className="flex-1 h-12 md:h-10 px-3 md:px-4 rounded-lg border border-input bg-background text-base md:text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isStreaming}
          />
          {isStreaming ? (
            <Button type="button" onClick={cancelQuery} variant="destructive" size="icon">
              <StopCircle className="h-4 w-4" />
            </Button>
          ) : (
            <Button type="submit" disabled={!input.trim()} size="icon">
              <Send className="h-4 w-4" />
            </Button>
          )}
        </form>
      </CardFooter>
    </Card>
  );
}
