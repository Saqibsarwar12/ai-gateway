import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// Attach API key from localStorage (browser-only)
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const key = localStorage.getItem("api_key") || "";
    if (key) config.headers.Authorization = key.startsWith("Bearer ") ? key : `Bearer ${key}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      if (typeof window !== "undefined") localStorage.removeItem("api_key");
    }
    return Promise.reject(err);
  }
);

export default api;
