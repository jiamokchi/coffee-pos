/**
 * src/lib/api.js
 * Axios — 統一 API 請求設定
 * 
 * 使用相對路徑 /api/v1，讓所有請求經過 Vite proxy 轉發到後端
 * 這樣完全避免 CORS 問題
 */
import axios from "axios";

export const api = axios.create({
  // 相對路徑 → 經 Vite proxy 轉發到 http://localhost:8000
  // 不使用絕對路徑，避免 CORS
  baseURL: "/api/v1",
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

/**
 * 將 FastAPI 錯誤格式化為可讀字串
 */
export function parseApiError(error) {
  if (!error?.response) return error?.message || "Network Error - 請確認後端服務是否正在執行";

  const data = error.response.data;
  if (!data) return `HTTP ${error.response.status}`;

  const detail = data.detail;
  if (!detail) return `伺服器錯誤 (${error.response.status})`;

  if (Array.isArray(detail)) {
    return detail.map(e => {
      const field = e.loc?.slice(1).join(".") || "";
      return field ? `${field}: ${e.msg}` : e.msg;
    }).join("; ");
  }

  if (typeof detail === "object") {
    return detail.message || JSON.stringify(detail);
  }

  return String(detail);
}

api.interceptors.response.use(
  r => r,
  err => {
    const status = err?.response?.status;
    const data   = err?.response?.data;
    console.error("[API Error]", status, data ?? err.message);
    return Promise.reject(err);
  }
);
