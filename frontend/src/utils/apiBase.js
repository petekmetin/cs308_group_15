const DEFAULT_API_BASE_URL = "http://localhost:8000";

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, "");
}

function isLocalHostname(hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

function normalizeApiBaseUrl(rawValue) {
  const value = String(rawValue || "").trim();
  if (!value) {
    return DEFAULT_API_BASE_URL;
  }

  try {
    const parsed = new URL(value);
    const isLocal = isLocalHostname(parsed.hostname);

    if (isLocal && parsed.protocol === "https:") {
      parsed.protocol = "http:";
    }

    // Keep a host-only base URL by default. Older env examples sometimes used
    // /api, which can cause accidental /api/api/... paths with current callers.
    if (parsed.pathname === "/api" || parsed.pathname === "/api/") {
      parsed.pathname = "/";
    }

    return trimTrailingSlash(parsed.toString());
  } catch {
    return DEFAULT_API_BASE_URL;
  }
}

export const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
);
