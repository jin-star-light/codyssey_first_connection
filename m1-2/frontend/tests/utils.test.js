import assert from "node:assert/strict";
import test from "node:test";

import { formatDate, formatHours, normalizeBaseUrl } from "../src/js/utils.js";

test("display helpers format stable Korean labels", () => {
  assert.equal(formatHours(2.5), "2.5시간");
  assert.equal(formatDate("2025-01-02"), "2025. 1. 2.");
  assert.equal(normalizeBaseUrl("https://api.example.com///"), "https://api.example.com");
});
