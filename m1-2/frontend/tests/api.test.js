import assert from "node:assert/strict";
import test from "node:test";

import { ApiError, createApi } from "../src/js/api.js";

test("API client normalizes URLs, JSON bodies, and 204 responses", async () => {
  const calls = [];
  const api = createApi({
    baseUrl: "https://api.example.com/",
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return new Response(null, { status: 204 });
    },
  });
  assert.equal(await api.deleteData("2025-01-01"), null);
  assert.equal(calls[0].url, "https://api.example.com/api/data/2025-01-01");

  const createApiClient = createApi({
    baseUrl: "https://api.example.com",
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return Response.json({ id: "2025-01-01" }, { status: 201 });
    },
  });
  await createApiClient.createData({ date: "2025-01-01", value: 2, memo: "학습" });
  assert.equal(calls[1].options.headers["Content-Type"], "application/json");
  assert.equal(JSON.parse(calls[1].options.body).value, 2);
});

test("API client extracts safe errors and falls back for malformed responses", async () => {
  const safe = createApi({
    baseUrl: "https://api.example.com",
    fetchImpl: async () => Response.json({ error: { message: "중복 날짜" } }, { status: 409 }),
  });
  await assert.rejects(safe.listData(), (error) => error instanceof ApiError && error.message === "중복 날짜");

  const malformed = createApi({
    baseUrl: "https://api.example.com",
    fetchImpl: async () => new Response("not-json", { status: 500 }),
  });
  await assert.rejects(malformed.listData(), /요청을 처리하지 못했습니다/);
});

test("API client rejects blank base URL and maps network errors", async () => {
  assert.throws(() => createApi({ baseUrl: "  " }), /API_BASE_URL/);
  const api = createApi({
    baseUrl: "https://api.example.com",
    fetchImpl: async () => { throw new Error("socket secret"); },
  });
  await assert.rejects(api.listData(), /서버에 연결할 수 없습니다/);
});
