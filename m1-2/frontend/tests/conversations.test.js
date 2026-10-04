import assert from "node:assert/strict";
import test from "node:test";

import { deleteConversationState, newConversationState, selectConversationState } from "../src/js/conversations.js";

test("conversation selection, new, and delete transitions are stable", () => {
  const initial = { activeConversationId: null, messages: [] };
  const selected = selectConversationState(initial, { id: "one", messages: [{ role: "user", content: "질문" }] });
  assert.equal(selected.activeConversationId, "one");
  assert.equal(newConversationState(selected).messages.length, 0);
  assert.equal(deleteConversationState(selected, "one").activeConversationId, null);
  assert.equal(deleteConversationState({ ...selected, activeConversationId: "two" }, "one").activeConversationId, "two");
});
