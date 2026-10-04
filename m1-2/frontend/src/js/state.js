export function createInitialState() {
  return {
    records: [],
    summary: null,
    conversations: [],
    activeConversationId: null,
    messages: [],
    loading: { mutation: false, chat: false },
    error: null,
  };
}

export function createStore(initial) {
  let state = structuredClone(initial);
  const listeners = new Set();
  return {
    get: () => state,
    set(patch) {
      state = { ...state, ...patch };
      listeners.forEach((listener) => listener(state));
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

export async function runMutation(store, optimisticRecords, operation) {
  const previous = store.get().records;
  store.set({ records: optimisticRecords, loading: { ...store.get().loading, mutation: true }, error: null });
  try {
    const result = await operation();
    store.set({ loading: { ...store.get().loading, mutation: false } });
    return result;
  } catch (error) {
    store.set({ records: previous, loading: { ...store.get().loading, mutation: false }, error: error.message });
    throw error;
  }
}

export async function runChat(store, content, operation) {
  const previous = store.get().messages;
  const optimistic = { role: "user", content };
  store.set({ messages: [...previous, optimistic], loading: { ...store.get().loading, chat: true }, error: null });
  try {
    const result = await operation();
    store.set({
      messages: [...store.get().messages, { role: "assistant", content: result.answer }],
      activeConversationId: result.conversation_id,
      loading: { ...store.get().loading, chat: false },
    });
    return result;
  } catch (error) {
    store.set({ messages: previous, loading: { ...store.get().loading, chat: false }, error: error.message });
    throw error;
  }
}
