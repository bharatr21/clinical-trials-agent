"use client";

import type { Message } from "@/types";
import { Download, FileJson, FileSpreadsheet, FileText, FileType } from "lucide-react";
import { useCallback, useState } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";

interface ExportMenuProps {
  messages: Message[];
  conversationId: string | null;
}

type ExportFormat = "pdf" | "txt" | "csv" | "json";

/**
 * Convert messages to plain text format
 */
function messagesToText(messages: Message[]): string {
  return messages
    .map((msg) => {
      const role = msg.role === "user" ? "You" : "Assistant";
      const content = msg.content;
      const sql = msg.sqlQuery ? `\n\nSQL Query:\n${msg.sqlQuery}` : "";
      return `${role}:\n${content}${sql}`;
    })
    .join("\n\n---\n\n");
}

/**
 * Convert messages to CSV format
 */
function messagesToCsv(messages: Message[]): string {
  const headers = ["Role", "Content", "SQL Query"];
  const rows = messages.map((msg) => [
    msg.role === "user" ? "User" : "Assistant",
    `"${msg.content.replace(/"/g, '""')}"`,
    msg.sqlQuery ? `"${msg.sqlQuery.replace(/"/g, '""')}"` : "",
  ]);

  return [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");
}

/**
 * Convert messages to JSON format
 */
function messagesToJson(messages: Message[]): string {
  const exportData = {
    exported_at: new Date().toISOString(),
    message_count: messages.length,
    messages: messages.map((msg) => ({
      role: msg.role,
      content: msg.content,
      sql_query: msg.sqlQuery || null,
    })),
  };
  return JSON.stringify(exportData, null, 2);
}

/**
 * Generate PDF content (as HTML for printing)
 */
function messagesToPdfHtml(messages: Message[]): string {
  const messageHtml = messages
    .map((msg) => {
      const role = msg.role === "user" ? "You" : "Assistant";
      const roleClass = msg.role === "user" ? "user-message" : "assistant-message";
      const content = msg.content
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br>");
      const sql = msg.sqlQuery
        ? `<div class="sql-query"><strong>SQL Query:</strong><pre>${msg.sqlQuery.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre></div>`
        : "";
      return `<div class="message ${roleClass}"><div class="role">${role}</div><div class="content">${content}</div>${sql}</div>`;
    })
    .join("");

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Clinical Trials Conversation Export</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #1e40af; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }
        .meta { color: #64748b; font-size: 14px; margin-bottom: 20px; }
        .message { margin-bottom: 20px; padding: 15px; border-radius: 8px; }
        .user-message { background: #3b82f6; color: white; }
        .assistant-message { background: #f1f5f9; }
        .role { font-weight: bold; margin-bottom: 8px; }
        .content { white-space: pre-wrap; word-wrap: break-word; }
        .sql-query { margin-top: 10px; padding: 10px; background: #1e293b; color: #e2e8f0; border-radius: 4px; }
        .sql-query pre { margin: 5px 0 0 0; white-space: pre-wrap; word-wrap: break-word; font-size: 12px; }
        @media print { body { padding: 0; } }
      </style>
    </head>
    <body>
      <h1>Clinical Trials Agent Conversation</h1>
      <div class="meta">Exported on ${new Date().toLocaleString()}</div>
      ${messageHtml}
    </body>
    </html>
  `;
}

export function ExportMenu({ messages, conversationId }: ExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleExport = useCallback(
    (format: ExportFormat) => {
      if (messages.length === 0) return;

      if (format === "pdf") {
        const htmlContent = messagesToPdfHtml(messages);
        const printWindow = window.open("", "_blank");
        if (printWindow) {
          printWindow.document.write(htmlContent);
          printWindow.document.close();
          printWindow.onload = () => printWindow.print();
        }
        setIsOpen(false);
        return;
      }

      const formats = {
        txt: { content: messagesToText(messages), mimeType: "text/plain;charset=utf-8;" },
        csv: { content: messagesToCsv(messages), mimeType: "text/csv;charset=utf-8;" },
        json: { content: messagesToJson(messages), mimeType: "application/json;charset=utf-8;" },
      } as const;

      const { content, mimeType } = formats[format];
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const timestamp = new Date().toISOString().slice(0, 10);
      const convId = conversationId ? `-${conversationId.slice(0, 8)}` : "";
      link.download = `conversation${convId}-${timestamp}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setIsOpen(false);
    },
    [messages, conversationId],
  );

  const hasMessages = messages.length > 0;

  return (
    <div className="relative">
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            disabled={!hasMessages}
            className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Export conversation"
          >
            <Download className="h-5 w-5 text-muted-foreground" />
          </button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{hasMessages ? "Export conversation" : "No messages to export"}</p>
        </TooltipContent>
      </Tooltip>

      {isOpen && hasMessages && (
        <>
          {/* Backdrop to close menu */}
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />

          {/* Dropdown menu */}
          <div className="absolute right-0 top-full mt-2 w-48 bg-background border rounded-lg shadow-lg z-50 py-1">
            <div className="px-3 py-2 text-xs font-medium text-muted-foreground border-b">
              Export as
            </div>

            <button
              type="button"
              onClick={() => handleExport("pdf")}
              className="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2"
            >
              <FileType className="h-4 w-4 text-red-500" />
              PDF (Print)
            </button>

            <button
              type="button"
              onClick={() => handleExport("txt")}
              className="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2"
            >
              <FileText className="h-4 w-4 text-blue-500" />
              Plain Text (.txt)
            </button>

            <button
              type="button"
              onClick={() => handleExport("csv")}
              className="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2"
            >
              <FileSpreadsheet className="h-4 w-4 text-green-500" />
              CSV (.csv)
            </button>

            <button
              type="button"
              onClick={() => handleExport("json")}
              className="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2"
            >
              <FileJson className="h-4 w-4 text-yellow-500" />
              JSON (.json)
            </button>
          </div>
        </>
      )}
    </div>
  );
}
