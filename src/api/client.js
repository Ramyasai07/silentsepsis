/**
 * API fetch wrapper — all requests go through here.
 *
 * Reads the token from localStorage directly (rather than from AuthContext)
 * to avoid a circular-import between this module and the context. The token
 * value is always current because localStorage is synchronously readable.
 *
 * Error taxonomy (three distinct cases, as required):
 *
 *   NetworkError   — fetch() itself threw (DNS failure, refused connection,
 *                    CORS preflight blocked, etc.).  Means "can't reach server".
 *
 *   ApiError{401}  — Server is reachable but rejected the token.
 *                    Clears localStorage + dispatches "auth:logout" so
 *                    AuthContext clears itself, then redirects to "/".
 *
 *   ApiError{403}  — Authenticated but not permitted for this resource.
 *                    Does NOT redirect; caller surfaces a permission-denied
 *                    state in the UI.
 *
 *   ApiError{n}    — Any other 4xx/5xx with status + parsed message.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const LS_TOKEN  = 'ss_token';

// ── Error classes ─────────────────────────────────────────────────────────────

export class NetworkError extends Error {
  constructor(message = 'Cannot reach the server. Check your connection.') {
    super(message);
    this.name = 'NetworkError';
  }
}

export class ApiError extends Error {
  /** @param {number} status  @param {string} message  @param {unknown} [body] */
  constructor(status, message, body) {
    super(message);
    this.name   = 'ApiError';
    this.status = status;
    this.body   = body;
  }
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

/**
 * @param {string} path         — e.g. "/auth/me"
 * @param {RequestInit} [opts]  — standard fetch options; headers are merged
 * @returns {Promise<unknown>}  — parsed JSON body on success
 */
export async function apiFetch(path, opts = {}) {
  const token = localStorage.getItem(LS_TOKEN);

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(opts.headers ?? {}),
  };

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...opts, headers });
  } catch (err) {
    // fetch() itself threw — network-level failure
    throw new NetworkError(err?.message);
  }

  if (response.ok) {
    // 204 No Content has no body
    if (response.status === 204) return null;
    return response.json();
  }

  // Parse the error body (FastAPI returns { detail: "..." })
  let errorBody;
  try {
    errorBody = await response.json();
  } catch {
    errorBody = null;
  }
  const detail =
    (typeof errorBody?.detail === 'string' ? errorBody.detail : null) ??
    response.statusText ??
    `HTTP ${response.status}`;

  if (response.status === 401) {
    // Token is expired / invalid. Clear auth state everywhere.
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem('ss_user');
    window.dispatchEvent(new CustomEvent('auth:logout'));
    // The AuthContext listener will pick this up and clear React state.
    // Redirect to login so the user can re-authenticate.
    if (window.location.pathname !== '/') {
      window.location.replace('/');
    }
  }

  throw new ApiError(response.status, detail, errorBody);
}
