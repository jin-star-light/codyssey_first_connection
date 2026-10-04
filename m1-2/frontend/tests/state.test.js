import assert from "node:assert/strict";
import test from "node:test";

import { createInitialState, createStore, runChat, runMutation } from "../src/js/state.js";

test("store updates state and notifies subscribers", () => {
  const store = createStore(createInitialState());
  let calls = 0;
  store.subscribe(() => { calls += 1; });
  store.set({ records: [{ id: "one" }] });
  assert.equal(store.get().records.length, 1);
  assert.equal(calls, 1);
});

test("failed mutation restores records and clears loading", async () => {
  const store = createStore({ ...createInitialState(), records: [{ id: "saved" }] });
  await assert.rejects(runMutation(store, [{ id: "optimistic" }], async () => { throw new Error("fail"); }));
  assert.deepEqual(store.get().records, [{ id: "saved" }]);
  assert.equal(store.get().loading.mutation, false);
});

test("failed chat removes optimistic message and clears loading", async () => {
  const store = createStore(createInitialState());
  await assert.rejects(runChat(store, "질문", async () => { throw new Error("fail"); }));
  assert.deepEqual(store.get().messages, []);
  assert.equal(store.get().loading.chat, false);
});
