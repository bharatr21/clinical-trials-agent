"use client";

import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Check, ChevronDown, ChevronUp, Copy, Database } from "lucide-react";
import { useState } from "react";

interface SqlQueryDisplayProps {
  query: string;
}

export function SqlQueryDisplay({ query }: SqlQueryDisplayProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(query);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="ml-11 mt-2">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <div className="rounded-lg border bg-card overflow-hidden">
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="w-full flex items-center justify-between px-3 py-2 text-sm text-muted-foreground hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Database className="h-3.5 w-3.5" />
                <span className="font-medium">SQL Query</span>
              </div>
              {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </CollapsibleTrigger>

          <CollapsibleContent>
            <div className="relative border-t">
              <div className="absolute top-2 right-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={copyToClipboard}
                    >
                      {copied ? (
                        <Check className="h-3.5 w-3.5 text-green-500" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{copied ? "Copied!" : "Copy to clipboard"}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <pre className="p-3 pr-10 overflow-x-auto text-xs bg-slate-950 rounded-b-lg">
                <code className="text-slate-100 whitespace-pre-wrap break-all">{query}</code>
              </pre>
            </div>
          </CollapsibleContent>
        </div>
      </Collapsible>
    </div>
  );
}
