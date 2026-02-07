"use client";

import { Button } from "@/components/ui/button";
import {
  getOpenAIApiKey,
  hasCustomApiKey,
  isValidApiKeyFormat,
  setOpenAIApiKey,
} from "@/lib/settings";
import { AlertTriangle, ExternalLink, Eye, EyeOff, Key, Settings, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

// Context for triggering the settings dialog from anywhere
type SettingsReason = "rate_limit" | "insufficient_quota" | "invalid_api_key" | "settings";

interface SettingsDialogContextType {
  openSettings: (reason?: SettingsReason) => void;
}

const SettingsDialogContext = createContext<SettingsDialogContextType | null>(null);

export function useSettingsDialog() {
  const context = useContext(SettingsDialogContext);
  if (!context) {
    throw new Error("useSettingsDialog must be used within SettingsDialogProvider");
  }
  return context;
}

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reason?: SettingsReason;
}

export function SettingsDialog({ open, onOpenChange, reason }: SettingsDialogProps) {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [hasKey, setHasKey] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      const storedKey = getOpenAIApiKey();
      setApiKey(storedKey || "");
      setHasKey(hasCustomApiKey());
      setError(null);
      setSaved(false);
      // Focus input when opened due to API key issues
      if (reason !== "settings") {
        setTimeout(() => inputRef.current?.focus(), 0);
      }
    }
  }, [open, reason]);

  const handleSave = () => {
    if (apiKey && !isValidApiKeyFormat(apiKey)) {
      setError("Invalid API key format. Keys should start with 'sk-'");
      return;
    }

    setOpenAIApiKey(apiKey || null);
    setHasKey(!!apiKey);
    setError(null);
    setSaved(true);

    // Close after brief delay to show saved state
    setTimeout(() => {
      onOpenChange(false);
    }, 500);
  };

  const handleClear = () => {
    setApiKey("");
    setOpenAIApiKey(null);
    setHasKey(false);
    setError(null);
    setSaved(true);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={() => onOpenChange(false)}
        onKeyDown={(e) => e.key === "Escape" && onOpenChange(false)}
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-md mx-4 md:mx-0 rounded-lg border bg-background p-4 md:p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings
          </h2>
          <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Rate limit warning banner */}
        {reason === "rate_limit" && (
          <div className="mb-4 p-3 rounded-md bg-amber-50 border border-amber-200 text-amber-800">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium">API Rate Limit Reached</p>
                <p className="mt-1">
                  The server&apos;s API key has hit its rate limit. You can wait a moment and try
                  again, or provide your own OpenAI API key to continue immediately.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Quota exceeded warning banner */}
        {reason === "insufficient_quota" && (
          <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-800">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium">API Quota Exceeded</p>
                <p className="mt-1">
                  The server&apos;s API key has exceeded its quota. Please provide your own OpenAI
                  API key to continue.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Invalid API key warning banner */}
        {reason === "invalid_api_key" && (
          <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-800">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium">Invalid API Key</p>
                <p className="mt-1">
                  The server&apos;s API key is invalid or has been revoked. Please provide your own
                  OpenAI API key to continue.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label htmlFor="api-key" className="text-sm font-medium flex items-center gap-2 mb-2">
              <Key className="h-4 w-4" />
              OpenAI API Key {reason === "settings" && "(Optional)"}
            </label>
            <p className="text-xs text-muted-foreground mb-2">
              Your key is stored locally in your browser and is only sent directly to OpenAI. We
              never store your key on our servers.
            </p>
            <div className="relative">
              <input
                ref={inputRef}
                id="api-key"
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setError(null);
                  setSaved(false);
                }}
                placeholder="sk-..."
                className="w-full h-10 px-3 pr-10 rounded-md border border-input bg-background text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-10 w-10"
                onClick={() => setShowKey(!showKey)}
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            {error && <p className="text-xs text-destructive mt-1">{error}</p>}
            {saved && !error && <p className="text-xs text-green-600 mt-1">Settings saved!</p>}
          </div>

          {hasKey && (
            <div className="flex items-center gap-2 p-2 rounded-md bg-muted text-sm">
              <Key className="h-4 w-4 text-green-600" />
              <span>Custom API key is configured</span>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            {hasKey && (
              <Button variant="outline" onClick={handleClear} className="flex-1">
                Clear Key
              </Button>
            )}
            <Button onClick={handleSave} className="flex-1">
              Save
            </Button>
          </div>

          {/* OpenAI link footer */}
          <div className="pt-2 border-t text-xs text-muted-foreground">
            <a
              href="https://platform.openai.com/api-keys"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              Get an API key from OpenAI
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

interface SettingsDialogProviderProps {
  children: React.ReactNode;
}

export function SettingsDialogProvider({ children }: SettingsDialogProviderProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<SettingsReason>("settings");

  const openSettings = useCallback((openReason: SettingsReason = "settings") => {
    setReason(openReason);
    setOpen(true);
  }, []);

  return (
    <SettingsDialogContext.Provider value={{ openSettings }}>
      {children}
      <SettingsDialog open={open} onOpenChange={setOpen} reason={reason} />
    </SettingsDialogContext.Provider>
  );
}

export function SettingsButton() {
  const [hasKey, setHasKey] = useState(false);
  const { openSettings } = useSettingsDialog();

  useEffect(() => {
    setHasKey(hasCustomApiKey());
  }, []);

  useEffect(() => {
    const interval = setInterval(() => setHasKey(hasCustomApiKey()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => openSettings("settings")}
      title="Settings"
      className="relative"
    >
      <Settings className="h-4 w-4" />
      {hasKey && <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-green-500" />}
    </Button>
  );
}
