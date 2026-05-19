import axios from "axios";

// In development: uses localhost (set in .env.development or falls back)
// In production build: uses the values from .env.production (set before npm run build)
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_BASE  = import.meta.env.VITE_WS_URL  || "ws://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export const login = (email, password) =>
  api.post("/api/auth/login", new URLSearchParams({ username: email, password }));

export const getMe = () => api.get("/api/auth/me");

export const getSessions = () => api.get("/api/sessions");
export const createSession = () => api.post("/api/sessions");
export const getSession = (id) => api.get(`/api/sessions/${id}`);
export const deleteSession = (id) => api.delete(`/api/sessions/${id}`);

export const WS_URL = `${WS_BASE}/ws/chat`;
