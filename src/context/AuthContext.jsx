/**
 * AuthContext — single source of truth for authentication state.
 *
 * Persists token + user in localStorage so sessions survive page refreshes.
 * Storage keys are namespaced with "ss_" to avoid collisions.
 *
 * Listens for the "auth:logout" CustomEvent dispatched by src/api/client.js
 * when any request comes back 401, so the context clears itself even when
 * the logout is triggered outside of React (e.g. deep inside a query hook).
 */
import { createContext, useContext, useEffect, useState, useCallback } from 'react';

const LS_TOKEN = 'ss_token';
const LS_USER  = 'ss_user';

const AuthContext = createContext(null);

function loadFromStorage() {
  try {
    const token = localStorage.getItem(LS_TOKEN);
    const raw   = localStorage.getItem(LS_USER);
    const user  = raw ? JSON.parse(raw) : null;
    return { token, user };
  } catch {
    return { token: null, user: null };
  }
}

export function AuthProvider({ children }) {
  const [{ token, user }, setAuth] = useState(loadFromStorage);

  // Called by Login.jsx after a successful /auth/login + /auth/me round-trip.
  const login = useCallback((newToken, newUser) => {
    localStorage.setItem(LS_TOKEN, newToken);
    localStorage.setItem(LS_USER, JSON.stringify(newUser));
    setAuth({ token: newToken, user: newUser });
  }, []);

  // Called by the logout button in any dashboard, or automatically when a
  // 401 is received (via the "auth:logout" event from client.js).
  const logout = useCallback(() => {
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem(LS_USER);
    setAuth({ token: null, user: null });
  }, []);

  // Listen for 401s bubbled up by the fetch wrapper so that any in-flight
  // request that returns 401 clears auth state without the component needing
  // to know about it.
  useEffect(() => {
    const handler = () => logout();
    window.addEventListener('auth:logout', handler);
    return () => window.removeEventListener('auth:logout', handler);
  }, [logout]);

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
