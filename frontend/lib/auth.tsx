'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://ai-gateway-7dkh.onrender.com';

interface User {
  id: string;
  email: string;
  name?: string;
  role?: string;
  credits?: number;
  api_key?: string;
}

interface AuthState {
  token: string | null;
  apiKey: string | null;
  user: User | null;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  setAuth: (auth: Partial<AuthState>) => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    apiKey: null,
    user: null,
    isLoading: true,
  });

  useEffect(() => {
    const token = localStorage.getItem('ai_gateway_token');
    const apiKey = localStorage.getItem('ai_gateway_api_key');
    const userStr = localStorage.getItem('ai_gateway_user');
    setState({
      token,
      apiKey,
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
      if (auth.apiKey !== undefined) {
        if (auth.apiKey) localStorage.setItem('ai_gateway_api_key', auth.apiKey);
        else localStorage.removeItem('ai_gateway_api_key');
      }
      if (auth.user !== undefined) {
        if (auth.user) localStorage.setItem('ai_gateway_user', JSON.stringify(auth.user));
        else localStorage.removeItem('ai_gateway_user');
      }
      return next;
    });
  };

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/admin/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    const user: User = data.user;
    const apiKey: string = user.api_key || '';
    setAuth({ token: data.access_token, apiKey, user });
  };

  const logout = () => {
    localStorage.removeItem('ai_gateway_token');
    localStorage.removeItem('ai_gateway_api_key');
    localStorage.removeItem('ai_gateway_user');
    setState({ token: null, apiKey: null, user: null, isLoading: false });
  };

  const refresh = async () => {
    if (!state.token) return;
    try {
      const res = await fetch(`${API_BASE}/admin/users/me`, {
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
    <AuthContext.Provider value={{ ...state, setAuth, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
