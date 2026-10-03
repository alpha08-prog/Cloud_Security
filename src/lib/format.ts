/** Signed percentage-point difference with a true minus sign, e.g. "+3 pts", "−9 pts". */
export function formatGap(points: number, unit = ' pts'): string {
  if (points === 0) return `0${unit}`
  return `${points > 0 ? '+' : '−'}${Math.abs(points)}${unit}`
}

export function formatPercent(value: number): string {
  return `${value}%`
}

/** Join truthy class names. */
export function cx(...names: (string | false | null | undefined)[]): string {
  return names.filter(Boolean).join(' ')
}
