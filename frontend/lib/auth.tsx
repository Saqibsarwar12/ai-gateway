'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://saki-gateway.indevs.in';

interface User {
  id: string;
  email: string;
  name?: string;
  role?: string;
  credits?: number;
  api_key?: string;
  is_active?: boolean;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  setAuth: (auth: Partial<AuthState>) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
  apiKey: string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    isLoading: true,
  });

  useEffect(() => {
    const token = localStorage.getItem('ai_gateway_token');
    const userStr = localStorage.getItem('ai_gateway_user');
    setState({
      token,
      user: userStr ? JSON.parse(userStr) : null,
      isLoading: false,
    });
  }, []);

  const setAuth = (auth: Partial<AuthState>) => {
    setState((prev) => {
      const next = { ...prev, ...auth };
      if (auth.token !== undefined) {
        if (auth.token) localStorage.setItem('ai_gateway_token', auth.token);
        else localStorage.removeItem('ai_gateway_token');
      }
      if (auth.user !== undefined) {
        if (auth.user) localStorage.setItem('ai_gateway_user', JSON.stringify(auth.user));
        else localStorage.removeItem('ai_gateway_user');
      }
      return next;
    });
  };

  const login = async (email: string, password: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/admin/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      let detail = 'Login failed';
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch {}
      throw new Error(detail);
    }
    const data = await res.json();
    const user: User = data.user;
    setAuth({ token: data.access_token, user });
  };

  const logout = () => {
    localStorage.removeItem('ai_gateway_token');
    localStorage.removeItem('ai_gateway_user');
    setState({ token: null, user: null, isLoading: false });
  };

  const refresh = async () => {
    if (!state.token) return;
    try {
      const res = await fetch(`${API_BASE}/admin/auth/me`, {
        headers: { Authorization: `Bearer ${state.token}` },
      });
      if (res.ok) {
        const user = await res.json();
        setAuth({ user });
      } else if (res.status === 401) {
        logout();
      }
    } catch {}
  };

  return (
    <AuthContext.Provider value={{ ...state, setAuth, login, logout, refresh, apiKey: null }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
