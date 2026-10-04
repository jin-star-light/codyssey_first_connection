import assert from "node:assert/strict";
import test from "node:test";

import { validateDataInput } from "../src/js/data.js";

test("data input normalizes valid payload", () => {
  assert.deepEqual(validateDataInput({ date: "2025-01-01", value: "2.50", memo: "  복습  " }, new Date("2025-02-01")), {
    ok: true,
    payload: { date: "2025-01-01", value: 2.5, memo: "복습" },
    errors: [],
  });
});

test("data input rejects range, future date, and long memo", () => {
  const result = validateDataInput({ date: "2025-02-02", value: "25", memo: "가".repeat(201) }, new Date("2025-02-01"));
  assert.equal(result.ok, false);
  assert.equal(result.errors.length, 3);
});
