export function validateDataInput(input, now = new Date()) {
  const errors = [];
  const date = String(input.date ?? "").trim();
  const value = Number(input.value);
  const memo = String(input.memo ?? "").trim();
  const today = now.toISOString().slice(0, 10);
  if (!date || date > today) errors.push("날짜는 오늘 또는 이전이어야 합니다.");
  if (!Number.isFinite(value) || value <= 0 || value > 24) errors.push("학습시간은 0보다 크고 24 이하여야 합니다.");
  if (memo.length > 200) errors.push("메모는 200자 이하여야 합니다.");
  return { ok: errors.length === 0, payload: { date, value, memo }, errors };
}
