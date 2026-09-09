/**
 * Reusable metric formatting helpers.
 *
 * CRITICAL RULE (Specification Section 3 & 40):
 * NEVER display fake zeros for missing/uncollected metrics.
 * null, undefined, NaN, or failed collection MUST display as "-".
 */

export function formatMetric(
  value: number | null | undefined,
  suffix: string = "",
  decimals: number = 1
): string {
  if (value === null || value === undefined || isNaN(Number(value))) {
    return "-";
  }
  return `${Number(value).toFixed(decimals)}${suffix}`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || isNaN(Number(bytes))) {
    return "-";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let b = Number(bytes);
  let i = 0;
  while (b >= 1024 && i < units.length - 1) {
    b /= 1024;
    i++;
  }
  return `${b.toFixed(1)} ${units[i]}`;
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "-";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "-";
  }
}
