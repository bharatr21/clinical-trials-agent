const CLIENT_ID_KEY = "clinical-trials-client-id";

/**
 * Generate a simple hash from a string (djb2 algorithm)
 */
function hashString(str: string): number {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 33) ^ str.charCodeAt(i);
  }
  return hash >>> 0;
}

/**
 * Generate a device fingerprint based on stable browser/device characteristics.
 * This creates a deterministic ID that should be the same across browser sessions
 * on the same device, even across different browsers.
 */
function generateDeviceFingerprint(): string {
  if (typeof window === "undefined") return "";

  const components: string[] = [];

  // Screen characteristics
  components.push(`${screen.width}x${screen.height}`);
  components.push(`${screen.colorDepth}`);
  components.push(`${screen.pixelDepth}`);
  components.push(`${window.devicePixelRatio || 1}`);

  // Timezone
  components.push(Intl.DateTimeFormat().resolvedOptions().timeZone || "");

  // Language
  components.push(navigator.language || "");
  components.push((navigator.languages || []).join(","));

  // Platform info
  components.push(navigator.platform || "");
  components.push(`${navigator.hardwareConcurrency || 0}`);
  components.push(`${(navigator as Navigator & { deviceMemory?: number }).deviceMemory || 0}`);

  // Create a hash from all components
  const fingerprint = components.join("|");
  const hash1 = hashString(fingerprint);
  const hash2 = hashString(fingerprint.split("").reverse().join(""));

  // Format as UUID-like string for consistency
  const hex1 = hash1.toString(16).padStart(8, "0");
  const hex2 = hash2.toString(16).padStart(8, "0");
  const hex3 = hashString(`${hash1}${hash2}`).toString(16).padStart(8, "0");
  const hex4 = hashString(`${fingerprint}salt`).toString(16).padStart(8, "0");

  return `${hex1}-${hex2.slice(0, 4)}-4${hex2.slice(5, 8)}-${hex3.slice(0, 4)}-${hex3.slice(4)}${hex4.slice(0, 4)}`;
}

/**
 * Get the client ID, using localStorage as cache and device fingerprint as fallback.
 * This ensures the same device gets the same ID even across different browsers.
 */
export function getClientId(): string {
  if (typeof window === "undefined") return "";

  const stored = localStorage.getItem(CLIENT_ID_KEY);
  if (stored) return stored;

  const fingerprint = generateDeviceFingerprint();
  if (fingerprint) {
    localStorage.setItem(CLIENT_ID_KEY, fingerprint);
  }
  return fingerprint;
}

/**
 * Set the client ID (used when backend generates a new one)
 */
export function setClientId(clientId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CLIENT_ID_KEY, clientId);
}

/**
 * Clear the stored client ID (useful for testing or resetting)
 */
export function clearClientId(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(CLIENT_ID_KEY);
}

/**
 * Regenerate client ID from device fingerprint (useful if localStorage was corrupted)
 */
export function regenerateClientId(): string {
  clearClientId();
  return getClientId();
}
