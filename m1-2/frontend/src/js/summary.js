import { formatDate, formatHours } from "./utils.js";

const trendLabels = {
  no_data: "데이터 없음",
  insufficient_data: "분석 대기",
  increase: "증가 중",
  decrease: "감소 중",
  maintain: "유지 중",
};

export function summaryViewModel(summary) {
  if (!summary?.metrics) {
    return { empty: true, count: summary?.count ?? 0, trendLabel: trendLabels[summary?.trend?.status] ?? "분석 대기" };
  }
  return {
    empty: false,
    count: summary.count,
    period: `${formatDate(summary.period.start)} ~ ${formatDate(summary.period.end)}`,
    total: formatHours(summary.metrics.total),
    average: formatHours(summary.metrics.average),
    latest: formatHours(summary.metrics.latest.value),
    change: `${summary.metrics.total_change > 0 ? "+" : ""}${summary.metrics.total_change}시간`,
    trendLabel: trendLabels[summary.trend.status] ?? "분석 대기",
  };
}
