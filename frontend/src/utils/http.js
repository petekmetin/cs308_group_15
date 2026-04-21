export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export function getStoredUser() {
  const raw = localStorage.getItem("user");
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function getStoredRole() {
  return localStorage.getItem("user_role") || getStoredUser()?.role || "";
}

export async function parseErrorMessage(response, fallbackMessage) {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      return payload.detail;
    }
    if (typeof payload === "object" && payload) {
      const firstKey = Object.keys(payload)[0];
      const value = payload[firstKey];
      if (Array.isArray(value) && value.length) {
        return `${firstKey}: ${value[0]}`;
      }
      if (typeof value === "string") {
        return `${firstKey}: ${value}`;
      }
    }
  } catch {
    // Ignore parse failures and use fallback.
  }
  return fallbackMessage;
}

export async function fetchJson(path, { method = "GET", token, body, headers } = {}) {
  const requestHeaders = {
    ...(body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(headers || {}),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response, "Request failed.");
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
