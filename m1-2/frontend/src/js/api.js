import { normalizeBaseUrl } from "./utils.js";

export class ApiError extends Error {
  constructor(message, status = 0, code = "request_failed") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function createApi({ baseUrl, fetchImpl = globalThis.fetch } = {}) {
  const normalized = normalizeBaseUrl(baseUrl);
  if (!normalized) throw new Error("API_BASE_URL이 비어 있습니다.");
  if (typeof fetchImpl !== "function") throw new Error("fetch implementation is required");

  async function request(path, options = {}) {
    let response;
    try {
      response = await fetchImpl(`${normalized}${path}`, options);
    } catch {
      throw new ApiError("서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.");
    }
    if (response.status === 204) return null;
    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new ApiError("요청을 처리하지 못했습니다.", response.status);
    }
    if (!response.ok) {
      throw new ApiError(
        payload?.error?.message || "요청을 처리하지 못했습니다.",
        response.status,
        payload?.error?.code,
      );
    }
    return payload;
  }

  const json = (method, body) => ({
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return {
    listData: () => request("/api/data"),
    getSummary: () => request("/api/data/summary"),
    createData: (payload) => request("/api/data", json("POST", payload)),
    updateData: (id, payload) => request(`/api/data/${encodeURIComponent(id)}`, json("PUT", payload)),
    deleteData: (id) => request(`/api/data/${encodeURIComponent(id)}`, { method: "DELETE" }),
    listConversations: () => request("/api/conversations"),
    createConversation: (payload) => request("/api/conversations", json("POST", payload)),
    getConversation: (id) => request(`/api/conversations/${encodeURIComponent(id)}`),
    deleteConversation: (id) => request(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }),
    chat: (payload) => request("/api/chat", json("POST", payload)),
  };
}
