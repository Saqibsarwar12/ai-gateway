import axios from "axios";

// Backend is served as a Zo user service.
// In production, update NEXT_PUBLIC_API_URL to the actual backend URL.
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Attach API key from localStorage on each request
if (typeof window !== "undefined") {
  api.interceptors.request.use((config) => {
    const key = localStorage.getItem("api_key") || sessionStorage.getItem("api_key");
    if (key) {
      config.headers.Authorization = `Bearer ${key}`;
    }
    return config;
  });
}

export const dashboard = {
  // Providers
  listProviders: () => api.get("/admin/providers").then(r => r.data),
  createProvider: (data: any) => api.post("/admin/providers", data).then(r => r.data),
  testProvider: (id: string) => api.post(`/admin/providers/${id}/test`).then(r => r.data),
  updateProvider: (id: string, data: any) => api.put(`/admin/providers/${id}`, data).then(r => r.data),
  deleteProvider: (id: string) => api.delete(`/admin/providers/${id}`).then(r => r.data),

  // Models
  listModels: () => api.get("/admin/models").then(r => r.data),
  updateModel: (id: string, data: any) => api.put(`/admin/models/${id}`, data).then(r => r.data),

  // Users
  listUsers: () => api.get("/admin/users").then(r => r.data),
  createUser: (data: any) => api.post("/admin/users", data).then(r => r.data),
  updateUser: (id: string, data: any) => api.put(`/admin/users/${id}`, data).then(r => r.data),

  // Routing
  listRules: () => api.get("/admin/routing").then(r => r.data),
  createRule: (data: any) => api.post("/admin/routing", data).then(r => r.data),
  updateRule: (id: string, data: any) => api.put(`/admin/routing/${id}`, data).then(r => r.data),

  // Analytics
  getAnalytics: () => api.get("/admin/analytics/overview").then(r => r.data),

  // Logs
  listLogs: (params?: any) => api.get("/admin/logs", { params }).then(r => r.data),

  // Feature Flags
  getFeatureFlags: () => api.get("/admin/feature-flags").then(r => r.data),
  updateFeatureFlag: (key: string, value: any) =>
    api.put(`/admin/feature-flags/${key}`, { value }).then(r => r.data),

  // System Config
  getSystemConfig: () => api.get("/admin/system-config").then(r => r.data),
  updateSystemConfig: (key: string, value: any) =>
    api.put(`/admin/system-config/${key}`, { value }).then(r => r.data),
};

export const setApiUrl = (url: string) => {
  api.defaults.baseURL = url;
};

export default api;
