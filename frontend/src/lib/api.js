import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

// Attach bearer token if present (fallback when cookies are blocked)
api.interceptors.request.use((config) => {
  const t = localStorage.getItem("edama_access_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// Extract readable error text from FastAPI responses
export function formatApiError(err) {
  const d = err?.response?.data?.detail;
  if (d == null) return err?.message || "حدث خطأ";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => e?.msg || JSON.stringify(e)).join(" ");
  return String(d);
}

export default api;
