"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { authApi } from "@/lib/api";

interface User {
  id: string;
  email: string | null;
  displayName: string | null;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  refreshUser: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshSeq = useRef(0);

  const refreshUser = useCallback(async () => {
    const seq = refreshSeq.current + 1;
    refreshSeq.current = seq;
    try {
      const u = await authApi.me();
      if (seq === refreshSeq.current) {
        setUser({ id: u.id, email: u.email, displayName: u.display_name });
      }
    } catch (error) {
      if (seq === refreshSeq.current) {
        setUser(null);
      }
      throw error;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    refreshUser()
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshUser]);

  const logout = useCallback(async () => {
    refreshSeq.current += 1;
    try {
      await authApi.logout();
    } catch {
      // Silently fail.
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated: !!user, refreshUser, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
