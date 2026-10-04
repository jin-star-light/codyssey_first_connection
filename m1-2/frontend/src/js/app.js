import { createApi } from "./api.js";
import { coldStartLabel } from "./chat.js";
import { deleteConversationState, newConversationState, selectConversationState } from "./conversations.js";
import { validateDataInput } from "./data.js";
import { createInitialState, createStore, runChat, runMutation } from "./state.js";
import { summaryViewModel } from "./summary.js";
import { formatDate, formatHours } from "./utils.js";

const api = createApi({ baseUrl: window.APP_CONFIG?.API_BASE_URL });
const store = createStore(createInitialState());
const byId = (id) => document.getElementById(id);
const node = (tag, className, text) => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
};

const elements = {
  status: byId("global-status"), conversations: byId("conversation-list"), messages: byId("chat-messages"),
  chatForm: byId("chat-form"), chatInput: byId("chat-input"), chatProgress: byId("chat-progress"),
  summary: byId("summary-content"), summaryPeriod: byId("summary-period"), rows: byId("data-rows"),
  recordCount: byId("record-count"), dataForm: byId("data-form"), dataError: byId("data-error"),
  date: byId("study-date"), value: byId("study-value"), memo: byId("study-memo"), editingId: byId("editing-id"),
  cancelEdit: byId("cancel-edit"), newConversation: byId("new-conversation"),
};

function setStatus(message = "") { elements.status.textContent = message; }

function renderConversations(state) {
  const children = state.conversations.map((conversation) => {
    const row = node("div", "conversation-row");
    const button = node("button", `conversation-item${state.activeConversationId === conversation.id ? " active" : ""}`);
    button.type = "button";
    const copy = node("span");
    copy.append(node("span", "", conversation.title), node("small", "", `${conversation.message_count}개 메시지`));
    button.append(copy);
    button.addEventListener("click", () => loadConversation(conversation.id));
    const remove = node("button", "conversation-delete", "×");
    remove.type = "button"; remove.setAttribute("aria-label", `${conversation.title} 삭제`);
    remove.addEventListener("click", () => removeConversation(conversation.id));
    row.style.display = "flex";
    row.append(button, remove);
    return row;
  });
  if (!children.length) children.push(node("p", "empty", "아직 저장된 대화가 없습니다.\nAI 코치에게 첫 질문을 해보세요."));
  elements.conversations.replaceChildren(...children);
}

function renderMessages(state) {
  if (!state.messages.length) {
    const welcome = node("div", "welcome");
    welcome.append(node("strong", "", "오늘의 학습을 함께 돌아볼까요?"), node("span", "", "학습시간을 먼저 기록한 뒤 흐름, 변화, 다음 목표를 질문해 보세요."));
    elements.messages.replaceChildren(welcome);
    return;
  }
  elements.messages.replaceChildren(...state.messages.map((message) => node("div", `message ${message.role}`, message.content)));
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function renderSummary(summary) {
  const view = summaryViewModel(summary);
  elements.summaryPeriod.textContent = view.period || "";
  if (view.empty) {
    elements.summary.replaceChildren(node("p", "empty", "학습시간을 기록하면 요약과 추세가 여기에 표시됩니다."));
    return;
  }
  const metrics = [["기록 일수", `${view.count}일`], ["총 학습시간", view.total], ["하루 평균", view.average], ["최근 기록", view.latest], ["학습 추세", view.trendLabel]];
  elements.summary.replaceChildren(...metrics.map(([label, value], index) => {
    const item = node("div", "metric");
    item.append(node("span", "", label), node("strong", index === 4 ? "positive" : "", value));
    return item;
  }));
}

function renderRecords(records) {
  elements.recordCount.textContent = `${records.length} DAYS`;
  const rows = records.map((record) => {
    const row = node("tr");
    row.append(node("td", "", formatDate(record.date)), node("td", "", formatHours(record.value)), node("td", "", record.memo || "—"));
    const actions = node("td");
    const edit = node("button", "table-action", "수정"); edit.type = "button";
    edit.addEventListener("click", () => startEdit(record));
    const remove = node("button", "table-action danger", "삭제"); remove.type = "button";
    remove.addEventListener("click", () => removeRecord(record.id));
    actions.append(edit, remove); row.append(actions); return row;
  });
  if (!rows.length) { const row = node("tr"); const cell = node("td", "empty", "아직 기록이 없습니다."); cell.colSpan = 4; row.append(cell); rows.push(row); }
  elements.rows.replaceChildren(...rows);
}

function render(state) {
  renderConversations(state); renderMessages(state); renderSummary(state.summary); renderRecords(state.records);
  elements.chatForm.querySelector("button").disabled = state.loading.chat;
  elements.dataForm.querySelector("button[type='submit']").disabled = state.loading.mutation;
}
store.subscribe(render);

async function refreshData() {
  const [data, summary] = await Promise.all([api.listData(), api.getSummary()]);
  store.set({ records: data.items, summary });
}
async function refreshConversations() {
  const result = await api.listConversations(); store.set({ conversations: result.items });
}
async function loadConversation(id) {
  try { const conversation = await api.getConversation(id); store.set(selectConversationState(store.get(), conversation)); }
  catch (error) { setStatus(error.message); }
}
async function removeConversation(id) {
  if (!window.confirm("이 대화 기록을 삭제할까요?")) return;
  try { await api.deleteConversation(id); store.set(deleteConversationState(store.get(), id)); await refreshConversations(); }
  catch (error) { setStatus(error.message); }
}
function resetDataForm() { elements.dataForm.reset(); elements.editingId.value = ""; elements.cancelEdit.hidden = true; elements.date.max = new Date().toISOString().slice(0, 10); }
function startEdit(record) { elements.editingId.value = record.id; elements.date.value = record.date; elements.value.value = record.value; elements.memo.value = record.memo; elements.cancelEdit.hidden = false; elements.date.focus(); }
async function removeRecord(id) {
  if (!window.confirm("이 학습 기록을 삭제할까요?")) return;
  try { await runMutation(store, store.get().records.filter((item) => item.id !== id), () => api.deleteData(id)); await refreshData(); }
  catch (error) { elements.dataError.textContent = error.message; }
}

elements.dataForm.addEventListener("submit", async (event) => {
  event.preventDefault(); elements.dataError.textContent = "";
  const result = validateDataInput({ date: elements.date.value, value: elements.value.value, memo: elements.memo.value });
  if (!result.ok) { elements.dataError.textContent = result.errors.join(" "); return; }
  const editingId = elements.editingId.value;
  try {
    await runMutation(store, store.get().records, () => editingId ? api.updateData(editingId, result.payload) : api.createData(result.payload));
    resetDataForm(); await refreshData(); setStatus(editingId ? "기록을 수정했습니다." : "새 학습 기록을 저장했습니다.");
  } catch (error) { elements.dataError.textContent = error.message; }
});
elements.cancelEdit.addEventListener("click", resetDataForm);
elements.newConversation.addEventListener("click", () => { store.set(newConversationState(store.get())); elements.chatInput.focus(); });

elements.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault(); const message = elements.chatInput.value.trim(); if (!message) return;
  elements.chatProgress.textContent = coldStartLabel(0);
  const timer = window.setTimeout(() => { elements.chatProgress.textContent = coldStartLabel(8000); }, 8000);
  try {
    const active = store.get().activeConversationId;
    await runChat(store, message, () => api.chat({ message, ...(active ? { conversation_id: active } : {}) }));
    elements.chatInput.value = ""; await refreshConversations();
  } catch (error) { setStatus(error.message); }
  finally { window.clearTimeout(timer); elements.chatProgress.textContent = ""; }
});

async function initialize() {
  resetDataForm(); render(store.get()); setStatus("데이터를 불러오고 있습니다…");
  try { await Promise.all([refreshData(), refreshConversations()]); setStatus(""); }
  catch (error) { setStatus(`${error.message} 무료 서버의 첫 연결은 시간이 걸릴 수 있습니다.`); }
}
initialize();
