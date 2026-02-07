"use client";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ConversationSummary } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import { useState } from "react";

interface ConversationSidebarProps {
  conversations: ConversationSummary[];
  currentConversationId: string | null;
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
}

export function ConversationSidebar({
  conversations,
  currentConversationId,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
}: ConversationSidebarProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (deleteConfirm === id) {
      onDeleteConversation(id);
      setDeleteConfirm(null);
      return;
    }
    setDeleteConfirm(id);
    setTimeout(() => setDeleteConfirm(null), 3000);
  };

  const formatDate = (dateStr: string) => {
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="w-[80vw] sm:w-64 max-w-[80vw] md:max-w-64 flex-shrink-0 border-r bg-background md:bg-muted/30 flex flex-col h-screen sticky top-0 overflow-hidden">
      <div className="p-3 border-b">
        <Button
          onClick={onNewConversation}
          variant="outline"
          className="w-full justify-start gap-2"
        >
          <MessageSquarePlus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <ScrollArea className="flex-1 w-full">
        <div className="p-2 space-y-1 w-full overflow-hidden">
          {conversations.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">No conversations yet</p>
          )}

          {conversations.map((conv) => (
            <button
              type="button"
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`
                w-full text-left p-3 rounded-lg group transition-colors overflow-hidden
                ${
                  currentConversationId === conv.id
                    ? "bg-primary/10 border border-primary/20"
                    : "hover:bg-muted"
                }
              `}
            >
              <div className="flex items-start justify-between gap-2 w-full">
                <div className="flex-1 min-w-0 overflow-hidden">
                  <p className="text-sm font-medium line-clamp-2" title={conv.title}>
                    {conv.title}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {formatDate(conv.updated_at)}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={(e) => handleDelete(e, conv.id)}
                  className={`
                    p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity
                    ${
                      deleteConfirm === conv.id
                        ? "bg-destructive text-destructive-foreground opacity-100"
                        : "hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                    }
                  `}
                  title={
                    deleteConfirm === conv.id ? "Click again to confirm" : "Delete conversation"
                  }
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
