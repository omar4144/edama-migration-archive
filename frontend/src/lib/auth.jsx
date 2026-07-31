import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "./api";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = loading, false = anon, obj = user
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch (e) {
      // 428 means must_change_password — but /auth/me itself is not gated.
      // 401 means anonymous.
      setUser(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = async (email, password) => {
    setError(null);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      if (data.access_token) localStorage.setItem("edama_access_token", data.access_token);
      setUser(data.user);
      return data.user;
    } catch (e) {
      setError(formatApiError(e));
      throw e;
    }
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("edama_access_token");
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, error, login, logout, refresh, setUser }}>
      {children}
    </AuthCtx.Provider>
  );
}
