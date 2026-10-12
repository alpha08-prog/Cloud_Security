// TypeScript port of the auditor's coverage formula (auditor/src/cloudaudit/scoring.py).
// A contract test recomputes every published score with it, so the number the web app
// explains and the number the auditor produced cannot quietly diverge.
//
//   coverage = sum(weight(severity) * credit(status)) / sum(weight(severity))
//   weights: critical 4, high 3, medium 2, low 1
//   credit:  pass 1, warn 0.5, fail/error 0; waived checks earn 0; skipped checks are excluded
import type { CheckResult, CheckSpec, Score, Severity, Status } from '../data/resultTypes'

export const WEIGHT: Readonly<Record<Severity, number>> = { critical: 4, high: 3, medium: 2, low: 1 }
export const CREDIT: Readonly<Record<Exclude<Status, 'skip'>, number>> = {
  pass: 1,
  warn: 0.5,
  fail: 0,
  error: 0,
}

export function coverage(
  key: string,
  pairs: readonly (readonly [CheckSpec, CheckResult])[],
  weighted = true,
): Score {
  let earned = 0
  let possible = 0
  let evaluated = 0
  let skipped = 0
  for (const [spec, result] of pairs) {
    if (result.status === 'skip') {
      skipped += 1
      continue
    }
    evaluated += 1
    const w = weighted ? WEIGHT[spec.severity] : 1
    possible += w
    earned += result.waived ? 0 : w * CREDIT[result.status]
  }
  return {
    key,
    score: possible ? Math.round((earned / possible) * 1e4) / 1e4 : null,
    earned,
    possible,
    evaluated,
    skipped,
    total: pairs.length,
  }
}

export function pairsFor(
  catalogue: readonly CheckSpec[],
  results: readonly CheckResult[],
  predicate: (spec: CheckSpec) => boolean = () => true,
): (readonly [CheckSpec, CheckResult])[] {
  const byId = new Map(results.map((r) => [r.checkId, r]))
  return catalogue
    .filter(predicate)
    .flatMap((spec) => {
      const result = byId.get(spec.id)
      return result ? [[spec, result] as const] : []
    })
}
