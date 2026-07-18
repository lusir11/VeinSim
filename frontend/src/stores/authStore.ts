/**
 * Global auth store powered by Zustand.
 */
import { create } from 'zustand';
import { authApi } from '../api/client';

interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, username: string, password: string) => Promise<boolean>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authApi.login(email, password);
      const token = res.data.access_token;
      localStorage.setItem('access_token', token);
      const meRes = await authApi.getMe();
      set({ user: meRes.data, token, isLoading: false });
      return true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Login failed';
      set({ error: msg, isLoading: false });
      return false;
    }
  },

  register: async (email, username, password) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.register({ email, username, password });
      // auto-login after register
      const loginRes = await authApi.login(email, password);
      const token = loginRes.data.access_token;
      localStorage.setItem('access_token', token);
      const meRes = await authApi.getMe();
      set({ user: meRes.data, token, isLoading: false });
      return true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed';
      set({ error: msg, isLoading: false });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    set({ user: null, token: null });
  },

  fetchMe: async () => {
    if (!localStorage.getItem('access_token')) return;
    try {
      const res = await authApi.getMe();
      set({ user: res.data });
    } catch {
      localStorage.removeItem('access_token');
      set({ user: null, token: null });
    }
  },
}));
