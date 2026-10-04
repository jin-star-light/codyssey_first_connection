export function selectConversationState(state, conversation) {
  return { ...state, activeConversationId: conversation.id, messages: conversation.messages };
}

export function newConversationState(state) {
  return { ...state, activeConversationId: null, messages: [], error: null };
}

export function deleteConversationState(state, deletedId) {
  return state.activeConversationId === deletedId ? newConversationState(state) : state;
}
