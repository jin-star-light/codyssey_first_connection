import assert from "node:assert/strict";
import test from "node:test";

import { summaryViewModel } from "../src/js/summary.js";

test("summary view model handles empty and populated data", () => {
  assert.equal(summaryViewModel({ count: 0, metrics: null, trend: { status: "no_data" } }).empty, true);
  const view = summaryViewModel({
    count: 20,
    period: { start: "2025-01-01", end: "2025-01-20" },
    metrics: { total: 50, average: 2.5, latest: { value: 3 }, total_change: 1 },
    trend: { status: "increase", difference: 0.5 },
  });
  assert.equal(view.empty, false);
  assert.equal(view.trendLabel, "증가 중");
  assert.equal(view.average, "2.5시간");
});
