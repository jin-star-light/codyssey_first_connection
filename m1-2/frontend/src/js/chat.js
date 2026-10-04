export function coldStartLabel(elapsedMilliseconds) {
  return elapsedMilliseconds >= 8000
    ? "무료 서버를 깨우는 중이에요. 최대 1분 정도 걸릴 수 있어요…"
    : "답변을 만들고 있어요…";
}
