/**
 * Settings storage utilities for user preferences.
 * Stores settings in localStorage for persistence across sessions.
 */

const OPENAI_API_KEY_STORAGE_KEY = "clinical-trials-openai-api-key";

/**
 * Get the user's OpenAI API key from localStorage.
 * Returns null if not set or if running on server.
 */
export function getOpenAIApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(OPENAI_API_KEY_STORAGE_KEY);
}

/**
 * Save the user's OpenAI API key to localStorage.
 * Pass null or empty string to clear the stored key.
 */
export function setOpenAIApiKey(apiKey: string | null): void {
  if (typeof window === "undefined") return;
  if (apiKey) {
    localStorage.setItem(OPENAI_API_KEY_STORAGE_KEY, apiKey);
  } else {
    localStorage.removeItem(OPENAI_API_KEY_STORAGE_KEY);
  }
}

/**
 * Check if user has a custom API key set.
 */
export function hasCustomApiKey(): boolean {
  return !!getOpenAIApiKey();
}

/**
 * Validate OpenAI API key format (basic validation).
 * Returns true if the key appears to be in valid format.
 */
export function isValidApiKeyFormat(apiKey: string): boolean {
  // OpenAI keys start with 'sk-' and are typically 40+ characters
  return /^sk-[a-zA-Z0-9_-]{20,}$/.test(apiKey);
}
