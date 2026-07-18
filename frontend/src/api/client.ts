/**
 * Axios-based API client for the VeinSim backend.
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 globally
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;

// ── Auth API ──────────────────────────────────────────────────────────────────

export const authApi = {
  register: (data: { email: string; username: string; password: string }) =>
    apiClient.post('/auth/register', data),
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  getMe: () => apiClient.get('/auth/me'),
};

// ── Project API ───────────────────────────────────────────────────────────────

export const projectApi = {
  list: (skip = 0, limit = 20) =>
    apiClient.get('/projects', { params: { skip, limit } }),
  get: (id: string) => apiClient.get(`/projects/${id}`),
  create: (data: { name: string; description?: string }) =>
    apiClient.post('/projects', data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.patch(`/projects/${id}`, data),
  delete: (id: string) => apiClient.delete(`/projects/${id}`),
  uploadGeometry: (id: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiClient.post(`/projects/${id}/geometry`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ── Simulation API ────────────────────────────────────────────────────────────

export const simulationApi = {
  list: (projectId?: string, skip = 0, limit = 20) =>
    apiClient.get('/simulations', { params: { project_id: projectId, skip, limit } }),
  get: (id: string) => apiClient.get(`/simulations/${id}`),
  create: (data: { project_id: string; solver_type?: string; run_params?: Record<string, unknown> }) =>
    apiClient.post('/simulations', data),
  cancel: (id: string) => apiClient.post(`/simulations/${id}/cancel`),
  getResults: (id: string) => apiClient.get(`/simulations/${id}/results`),
};
