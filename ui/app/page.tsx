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
          {/* Sidebar */}
          {sidebarOpen && (
            <ConversationSidebar
              conversations={conversations}
              currentConversationId={currentConversationId}
              onNewConversation={newConversation}
              onSelectConversation={selectConversation}
              onDeleteConversation={removeConversation}
            />
          )}

          {/* Main content */}
          <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
            <header className="flex-shrink-0 border-b bg-white/80 backdrop-blur-sm z-10">
              <div className="px-6 py-4">
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
                      <h1 className="text-xl font-semibold text-foreground">
                        Clinical Trials Agent
                      </h1>
                      <p className="text-sm text-muted-foreground flex items-center gap-1.5">
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

            <div className="flex-1 flex flex-col w-full px-4 py-4 gap-4 min-h-0 overflow-hidden">
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

            <footer className="flex-shrink-0 border-t py-3 text-center text-sm text-muted-foreground">
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
