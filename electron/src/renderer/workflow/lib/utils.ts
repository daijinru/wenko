export { cn } from "@shared/lib/utils"

export function formatTime(isoString: string | null | undefined): string {
  if (!isoString) return '';
  // Backend stores UTC time without timezone suffix, append 'Z' to parse as UTC
  const normalized = isoString.endsWith('Z') || isoString.includes('+') ? isoString : isoString + 'Z';
  const date = new Date(normalized);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}
