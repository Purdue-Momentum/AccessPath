/**
 * Auth API helper.
 *
 * The backend uses Django session authentication. The login endpoint is open
 * (AllowAny) and does not require a CSRF token, since the user is not yet
 * authenticated when they post credentials. Once logged in, a `sessionid`
 * cookie is set and subsequent authenticated requests (e.g. logout) DO require
 * the CSRF token from the `csrftoken` cookie in the `X-CSRFToken` header — so
 * we always include it when the cookie is present.
 *
 * In development, requests go to `/api/v1/*`. The Vite dev server proxies
 * `/api/*` to the Django backend (see vite.config.js), so everything stays
 * same-origin and no CORS config is needed on the backend.
 */

const API_BASE = "/api/v1";

/** Read a cookie value by name. Returns null if not present. */
export function getCookie(name) {
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + name.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1") + "=([^;]*)")
  );
  return match ? decodeURIComponent(match[1]) : null;
}

/** Build request headers, including the CSRF token when we have it. */
function buildHeaders() {
  const headers = { "Content-Type": "application/json" };
  const csrf = getCookie("csrftoken");
  if (csrf) headers["X-CSRFToken"] = csrf;
  return headers;
}

/**
 * Log in with email + password.
 * Resolves to the user object on success.
 * Throws an Error whose message is suitable to show the user on failure.
 */
export async function login(email, password) {
  let response;
  try {
    response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: buildHeaders(),
      body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new Error("Could not reach the server. Is the backend running?");
  }

  if (response.ok) {
    return response.json();
  }

  // Surface the backend's message (e.g. "Email or password is wrong.").
  let message = "Login failed. Please try again.";
  try {
    const data = await response.json();
    if (data?.detail) message = data.detail;
  } catch {
    // Non-JSON error body; keep the generic message.
  }
  throw new Error(message);
}
