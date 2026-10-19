import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, authApi, setUnauthorizedHandler } from "../api/index.js";

const AuthContext = createContext(null);

/** Session state for the whole app: "loading", then a User or nobody. */
export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: "loading", user: null });
  const signedOut = useCallback(() => setState({ status: "anonymous", user: null }), []);

  useEffect(() => {
    setUnauthorizedHandler(signedOut);
    let cancelled = false;
    (async () => {
      try {
        await api.ensureCsrfToken();
        const user = await authApi.me();
        if (!cancelled) setState({ status: "authenticated", user });
      } catch {
        if (!cancelled) signedOut();
      }
    })();
    return () => {
      cancelled = true;
      setUnauthorizedHandler(() => {});
    };
  }, [signedOut]);

  const login = useCallback(async (username, password) => {
    await api.ensureCsrfToken();
    const { user } = await authApi.login(username, password);
    setState({ status: "authenticated", user });
  }, []);

  /**
   * Ends the session on the server. The User is only shown as logged out once
   * the server confirms it (or says there was no session); otherwise the error
   * is thrown so the screen can say logout failed, rather than hiding a session
   * that is still alive.
   */
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (error) {
      if (error.status !== 401) throw error;
    }
    signedOut();
    // Make sure a CSRF cookie exists before the next login.
    await api.ensureCsrfToken().catch(() => {});
  }, [signedOut]);

  const value = useMemo(() => ({ ...state, login, logout }), [state, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
