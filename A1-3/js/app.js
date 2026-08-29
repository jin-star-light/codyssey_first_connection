"use strict";

const menuToggle = document.querySelector("#menu-toggle");
const primaryNav = document.querySelector("#primary-nav");
const recommendForm = document.querySelector("#recommend-form");
const dateInput = document.querySelector("#date-input");
const submitButton = document.querySelector("#submit-button");
const buttonLabel = submitButton?.querySelector(".button-label");
const statusMessage = document.querySelector("#status-message");
const resultHeading = document.querySelector("#result-heading");
const resultDate = document.querySelector("#result-date");
const fruitResults = document.querySelector("#fruit-results");

const REQUIRED_FRUIT_FIELDS = [
  "name",
  "emoji",
  "season_reason",
  "taste_nutrition",
  "selection_tip",
  "storage_tip",
  "recipe",
];
const DETAIL_FIELDS = [
  ["taste_nutrition", "맛과 영양"],
  ["selection_tip", "잘 고르는 법"],
  ["storage_tip", "보관법"],
  ["recipe", "간단 레시피"],
];
const REQUEST_TIMEOUT_MS = 20_000;


class ApiResponseError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "ApiResponseError";
    this.code = code;
  }
}


function setMenuOpen(isOpen) {
  if (!menuToggle || !primaryNav) return;
  primaryNav.classList.toggle("is-open", isOpen);
  menuToggle.setAttribute("aria-expanded", String(isOpen));
  menuToggle.setAttribute("aria-label", isOpen ? "메뉴 닫기" : "메뉴 열기");
}


menuToggle?.addEventListener("click", () => {
  setMenuOpen(menuToggle.getAttribute("aria-expanded") !== "true");
});

primaryNav?.addEventListener("click", (event) => {
  if (event.target instanceof HTMLAnchorElement) setMenuOpen(false);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setMenuOpen(false);
});

const desktopQuery = window.matchMedia("(min-width: 768px)");
desktopQuery.addEventListener("change", (event) => {
  if (event.matches) setMenuOpen(false);
});


function localIsoDate(value = new Date()) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}


if (dateInput instanceof HTMLInputElement) {
  dateInput.value = localIsoDate();
}


function setStatus(message, type = "notice") {
  if (!statusMessage) return;
  statusMessage.textContent = message;
  statusMessage.classList.remove("status--notice", "status--success", "status--error");
  if (message) statusMessage.classList.add(`status--${type}`);
}


function setLoading(isLoading) {
  if (!(submitButton instanceof HTMLButtonElement) || !buttonLabel) return;
  submitButton.disabled = isLoading;
  submitButton.classList.toggle("is-loading", isLoading);
  submitButton.setAttribute("aria-busy", String(isLoading));
  buttonLabel.textContent = isLoading ? "추천을 준비하고 있어요" : "제철 과일 추천받기";
}


function clearResults() {
  fruitResults?.replaceChildren();
  if (resultHeading) resultHeading.hidden = true;
  if (resultDate) resultDate.textContent = "";
}


function assertRecommendationPayload(payload) {
  if (!payload || typeof payload !== "object" || !Array.isArray(payload.fruits)) {
    throw new ApiResponseError("INVALID_RESPONSE", "추천 결과 형식을 확인할 수 없어요.");
  }
  if (payload.fruits.length !== 3) {
    throw new ApiResponseError("INVALID_RESPONSE", "추천 과일이 세 가지가 아니에요.");
  }
  payload.fruits.forEach((fruit) => {
    if (!fruit || typeof fruit !== "object") {
      throw new ApiResponseError("INVALID_RESPONSE", "추천 과일 정보가 올바르지 않아요.");
    }
    REQUIRED_FRUIT_FIELDS.forEach((field) => {
      if (typeof fruit[field] !== "string" || !fruit[field].trim()) {
        throw new ApiResponseError("INVALID_RESPONSE", "추천 과일 정보가 비어 있어요.");
      }
    });
  });
}


function createDetailRow(label, value) {
  const row = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = value;
  row.append(term, description);
  return row;
}


function createFruitCard(fruit, index) {
  const card = document.createElement("article");
  card.className = "fruit-card";
  card.setAttribute("aria-labelledby", `fruit-name-${index}`);

  const emoji = document.createElement("div");
  emoji.className = "fruit-card__emoji";
  emoji.setAttribute("aria-hidden", "true");
  emoji.textContent = fruit.emoji;

  const title = document.createElement("h4");
  title.id = `fruit-name-${index}`;
  title.textContent = fruit.name;

  const seasonReason = document.createElement("p");
  seasonReason.textContent = fruit.season_reason;

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "맛있게 즐기는 방법";
  const detailList = document.createElement("dl");
  detailList.className = "fruit-card__details";
  DETAIL_FIELDS.forEach(([field, label]) => {
    detailList.append(createDetailRow(label, fruit[field]));
  });
  details.append(summary, detailList);
  card.append(emoji, title, seasonReason, details);
  return card;
}


function formatSelectedDate(isoDate) {
  const parts = isoDate.split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return isoDate;
  const localDate = new Date(parts[0], parts[1] - 1, parts[2]);
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(localDate);
}


function renderRecommendations(payload) {
  assertRecommendationPayload(payload);
  const cards = payload.fruits.map(createFruitCard);
  fruitResults?.replaceChildren(...cards);
  if (resultDate) resultDate.textContent = formatSelectedDate(payload.date);
  if (resultHeading) resultHeading.hidden = false;
}


function messageForError(error) {
  if (error?.name === "AbortError") {
    return "응답이 늦어지고 있어요. 잠시 후 다시 시도해 주세요.";
  }
  if (error instanceof ApiResponseError) {
    const messages = {
      INVALID_DATE: "올바른 날짜를 선택해 주세요.",
      INVALID_BODY: "입력 내용을 확인한 뒤 다시 시도해 주세요.",
      CONFIGURATION_ERROR: "서비스 설정이 아직 완료되지 않았어요. 관리자에게 알려 주세요.",
      UPSTREAM_ERROR: "AI 추천을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.",
      INVALID_RESPONSE: "추천 결과를 읽지 못했어요. 다시 한 번 시도해 주세요.",
      INTERNAL_ERROR: "예상하지 못한 오류가 발생했어요. 잠시 후 다시 시도해 주세요.",
    };
    return messages[error.code] || error.message || "추천을 불러오지 못했어요.";
  }
  return "네트워크 연결을 확인하고 다시 시도해 주세요.";
}


recommendForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!(dateInput instanceof HTMLInputElement) || !dateInput.value) {
    clearResults();
    setStatus("추천받을 날짜를 먼저 선택해 주세요.", "error");
    dateInput?.focus();
    return;
  }

  clearResults();
  setStatus("선택한 달의 제철 과일을 찾고 있어요.", "notice");
  setLoading(true);

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: dateInput.value }),
      signal: controller.signal,
    });

    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new ApiResponseError("INVALID_RESPONSE", "서버 응답을 읽을 수 없어요.");
    }

    if (!response.ok) {
      const code = payload?.error?.code || "INTERNAL_ERROR";
      const message = payload?.error?.message || "추천을 불러오지 못했어요.";
      throw new ApiResponseError(code, message);
    }

    renderRecommendations(payload);
    if (payload.source === "fallback") {
      setStatus(payload.notice || "기본 제철 정보를 보여드려요.", "notice");
    } else {
      setStatus("제철 과일 세 가지를 준비했어요. 맛있게 살펴보세요!", "success");
    }
    resultHeading?.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    clearResults();
    setStatus(messageForError(error), "error");
  } finally {
    window.clearTimeout(timeoutId);
    setLoading(false);
  }
});
