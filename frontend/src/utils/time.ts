/** 时间格式化工具：分钟数与 HH:MM 互转的公共函数集。 */

/** 分钟数格式化为 "H:MM"（如 570 → "9:30"）；空/0 返回 '-'。 */
export function fmtMinutes(m: number | null | undefined): string {
  if (m == null || m <= 0) return '-'
  const h = Math.floor(m / 60)
  const min = Math.floor(m % 60)
  return `${h}:${String(min).padStart(2, '0')}`
}

/** 起止分钟数格式化为 "S:E" 区间（如 (480, 1020) → "8:00-17:00"）。全天（0-1440）映射为 "全天"。 */
export function fmtRange(start: number, end: number): string {
  if (start === 0 && end >= 1440) return '全天'
  const s = fmtMinutes(start)
  const e = fmtMinutes(end)
  return `${s}-${e}`
}
