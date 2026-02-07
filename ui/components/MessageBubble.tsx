"use client";

import { cn } from "@/lib/utils";
import type { Message } from "@/types";
import { Bot, Check, Copy, Download, User } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  currentStage?: string | null;
}

/**
 * Check if markdown content contains a table
 */
function containsMarkdownTable(content: string): boolean {
  // Match markdown table pattern: | header | header |
  const tablePattern = /\|.+\|[\r\n]+\|[-:| ]+\|/;
  return tablePattern.test(content);
}

/**
 * Strip markdown links, keeping only the link text
 * e.g., [NCT12345678](https://clinicaltrials.gov/study/NCT12345678) -> NCT12345678
 */
function stripMarkdownLinks(text: string): string {
  return text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
}

/**
 * Parse markdown tables to CSV format
 */
function markdownTablesToCsv(content: string): string {
  const lines = content.split("\n");
  const csvLines: string[] = [];
  let inTable = false;

  for (const line of lines) {
    const trimmed = line.trim();

    // Check if line is a table row
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      // Skip separator rows (e.g., |---|---|)
      if (/^\|[\s-:|]+\|$/.test(trimmed)) {
        continue;
      }

      inTable = true;
      // Extract cells, remove leading/trailing pipes, split by |
      const cells = trimmed
        .slice(1, -1)
        .split("|")
        .map((cell) => {
          // Strip markdown links and clean for CSV
          const stripped = stripMarkdownLinks(cell.trim());
          const cleaned = stripped.replace(/"/g, '""');
          return `"${cleaned}"`;
        });
      csvLines.push(cells.join(","));
    } else if (inTable && trimmed === "") {
      // Empty line after table, add separator
      csvLines.push("");
      inTable = false;
    }
  }

  return csvLines.join("\n");
}

export function MessageBubble({ message, isStreaming = false, currentStage }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const showStreamingIndicator = isStreaming && !message.content;
  const [copied, setCopied] = useState(false);
  const [csvExported, setCsvExported] = useState(false);

  const hasTable = useMemo(
    () => !isUser && message.content && containsMarkdownTable(message.content),
    [isUser, message.content],
  );

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(message.content).catch(console.error);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  const handleExportCsv = useCallback(() => {
    const csv = markdownTablesToCsv(message.content);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `table-export-${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setCsvExported(true);
    setTimeout(() => setCsvExported(false), 2000);
  }, [message.content]);

  return (
    <div className={cn("flex gap-3 w-full", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4 text-muted-foreground" />}
      </div>

      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2.5 shadow-sm overflow-hidden break-words relative group",
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "bg-muted text-foreground rounded-tl-sm",
        )}
      >
        {isUser ? (
          <p className="text-sm break-words">{message.content}</p>
        ) : showStreamingIndicator ? (
          <div className="flex items-center gap-2.5">
            <span className="orbit-dots" />
            <span className="shimmer-text animate-shimmer text-sm font-medium">
              {currentStage || "Analyzing your question"}...
            </span>
          </div>
        ) : (
          <>
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-p:leading-relaxed prose-headings:my-2 prose-ul:my-1 prose-li:my-0.5 prose-table:text-xs prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1 prose-a:text-blue-600 prose-a:underline prose-a:hover:text-blue-800 [&_table]:block [&_table]:overflow-x-auto [&_table]:max-w-full">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-2 h-4 ml-0.5 bg-current animate-pulse" />
              )}
            </div>

            {/* Action buttons - show on hover */}
            {!isStreaming && message.content && (
              <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={handleCopy}
                      className="p-1.5 rounded-md bg-background/80 hover:bg-background border shadow-sm transition-colors"
                      aria-label="Copy to clipboard"
                    >
                      {copied ? (
                        <Check className="h-3.5 w-3.5 text-green-600" />
                      ) : (
                        <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{copied ? "Copied!" : "Copy to clipboard"}</p>
                  </TooltipContent>
                </Tooltip>

                {hasTable && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={handleExportCsv}
                        className="p-1.5 rounded-md bg-background/80 hover:bg-background border shadow-sm transition-colors"
                        aria-label="Export table to CSV"
                      >
                        {csvExported ? (
                          <Check className="h-3.5 w-3.5 text-green-600" />
                        ) : (
                          <Download className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{csvExported ? "Exported!" : "Export table to CSV"}</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
