/**
 * Auth API calls.
 *
 * login()  → POST /auth/login (OAuth2 password flow, form-encoded)
 *            Returns Token: { access_token: string, token_type: "bearer" }
 *
 * getMe()  → GET /auth/me (Bearer token required)
 *            Returns UserOut: { id, email, staff_id, full_name, role, created_at }
 *
 * The login endpoint is deliberately NOT routed through apiFetch() for the
 * Authorization header injection — there is no token yet at that point. It
 * does use apiFetch() for error normalisation (NetworkError / ApiError).
 */
import { apiFetch } from './client';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/**
 * Authenticate against POST /auth/login.
 *
 * The backend is a standard OAuth2 password flow: the body MUST be
 * application/x-www-form-urlencoded with fields `username` and `password`.
 * Field name is `username` (not `email`) per the OAuth2 spec; the backend
 * accepts the user's email address in this field.
 *
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ access_token: string, token_type: string }>}
 */
export async function login(email, password) {
  // We build this request manually because apiFetch() always sets
  // Content-Type: application/json, but this endpoint requires form-encoding.
  return apiFetch('/auth/login', {
    method: 'POST',
    headers: {
      // Override the default JSON content type for this one endpoint.
      'Content-Type': 'application/x-www-form-urlencoded',
      // No Authorization header — we don't have a token yet.
      Authorization: undefined,
    },
    body: new URLSearchParams({ username: email, password }),
  });
}

/**
 * Fetch the authenticated user's profile from GET /auth/me.
 *
 * @returns {Promise<{ id: string, email: string, staff_id: string, full_name: string, role: string, created_at: string }>}
 */
export function getMe() {
  return apiFetch('/auth/me');
}
