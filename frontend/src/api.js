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

// ── Sprint 8: portfolio / findings / dashboard ──────────────────────────────
export const getDashboard = () => api.get("/api/dashboard/stats");
export const getProperties = (params = {}) =>
  api.get("/api/portfolio/properties", { params });
export const getProperty = (id) => api.get(`/api/properties/${id}`);
export const getEvidencePacket = (id) =>
  api.get(`/api/properties/${id}/evidence-packet`);
export const getFindings = (params = {}) => api.get("/api/findings", { params });
export const setFindingStatus = (id, status) =>
  api.patch(`/api/findings/${id}`, { status });
export const portfolioCell = (property_id, question) =>
  api.post("/api/portfolio/cell", { property_id, question });

export const WS_URL = `${WS_BASE}/ws/chat`;
