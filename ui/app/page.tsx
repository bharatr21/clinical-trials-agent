"use client";

import { ChatInterface } from "@/components/ChatInterface";
import { ConversationSidebar } from "@/components/ConversationSidebar";
import { ExampleQuestions } from "@/components/ExampleQuestions";
import { ExportMenu } from "@/components/ExportMenu";
import { SettingsButton, SettingsDialogProvider } from "@/components/SettingsDialog";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useConversation } from "@/hooks/useConversation";
import { Activity, Database, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useState } from "react";

export default function Home() {
  const [selectedQuestion, setSelectedQuestion] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const {
    conversations,
    currentConversationId,
    messages,
    newConversation,
    selectConversation,
    removeConversation,
    refreshConversations,
    setCurrentConversationId,
    setMessages,
  } = useConversation();

  return (
    <SettingsDialogProvider>
      <TooltipProvider>
        <main className="h-screen flex bg-gradient-to-b from-slate-50 to-white overflow-hidden">
          {/* Sidebar backdrop (mobile only) */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 bg-black/70 z-40 md:hidden"
              onClick={() => setSidebarOpen(false)}
              onKeyDown={(e) => e.key === "Escape" && setSidebarOpen(false)}
            />
          )}

          {/* Sidebar */}
          {sidebarOpen && (
            <div className="fixed inset-y-0 left-0 z-50 md:relative md:z-auto">
              <ConversationSidebar
                conversations={conversations}
                currentConversationId={currentConversationId}
                onNewConversation={newConversation}
                onSelectConversation={selectConversation}
                onDeleteConversation={removeConversation}
              />
            </div>
          )}

          {/* Main content */}
          <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
            <header className="flex-shrink-0 border-b bg-white/80 backdrop-blur-sm z-10">
              <div className="px-3 py-3 md:px-6 md:py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setSidebarOpen(!sidebarOpen)}
                      className="p-2 hover:bg-muted rounded-lg transition-colors"
                      aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
                    >
                      {sidebarOpen ? (
                        <PanelLeftClose className="h-5 w-5 text-muted-foreground" />
                      ) : (
                        <PanelLeftOpen className="h-5 w-5 text-muted-foreground" />
                      )}
                    </button>

                    <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10">
                      <Activity className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h1 className="text-base md:text-xl font-semibold text-foreground">
                        Clinical Trials Agent
                      </h1>
                      <p className="text-sm text-muted-foreground hidden sm:flex items-center gap-1.5">
                        <Database className="h-3 w-3" />
                        Query the AACT database using natural language
                      </p>
                    </div>
                  </div>

                  {/* Settings and export menu */}
                  <div className="flex items-center gap-2">
                    <SettingsButton />
                    <ExportMenu messages={messages} conversationId={currentConversationId} />
                  </div>
                </div>
              </div>
            </header>

            <div className="flex-1 flex flex-col w-full px-2 py-2 md:px-4 md:py-4 gap-3 md:gap-4 min-h-0 overflow-hidden">
              <ExampleQuestions onSelect={setSelectedQuestion} />
              <ChatInterface
                initialQuestion={selectedQuestion}
                onQuestionUsed={() => setSelectedQuestion(null)}
                conversationId={currentConversationId}
                messages={messages}
                onMessagesChange={setMessages}
                onConversationIdChange={setCurrentConversationId}
                onConversationCreated={refreshConversations}
              />
            </div>

            <footer className="flex-shrink-0 border-t py-2 md:py-3 text-center text-xs md:text-sm text-muted-foreground">
              <p>
                Powered by{" "}
                <a
                  href="https://aact.ctti-clinicaltrials.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  AACT Database
                </a>{" "}
                &bull; Data from{" "}
                <a
                  href="https://clinicaltrials.gov/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  ClinicalTrials.gov
                </a>
              </p>
            </footer>
          </div>
        </main>
      </TooltipProvider>
    </SettingsDialogProvider>
  );
}
