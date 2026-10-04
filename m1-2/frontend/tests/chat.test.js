import assert from "node:assert/strict";
import test from "node:test";

import { coldStartLabel } from "../src/js/chat.js";

test("chat displays a cold-start hint after eight seconds", () => {
  assert.equal(coldStartLabel(7999), "답변을 만들고 있어요…");
  assert.equal(coldStartLabel(8000), "무료 서버를 깨우는 중이에요. 최대 1분 정도 걸릴 수 있어요…");
});
