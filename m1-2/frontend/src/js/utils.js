export function normalizeBaseUrl(value) {
  return String(value ?? "").trim().replace(/\/+$/, "");
}

export function formatHours(value) {
  return `${Number(value).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}시간`;
}

export function formatDate(value) {
  const [year, month, day] = String(value).split("-").map(Number);
  return new Intl.DateTimeFormat("ko-KR", { timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, day)),
  );
}
