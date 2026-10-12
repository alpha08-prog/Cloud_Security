// One-line, data-derived evidence summaries reused across the Requirements and
// Results tabs. Everything here is computed from results/published.
import type { ProfileName, RequirementId } from '../data/resultTypes'
import { AUDITS, E1, E2, E3 } from '../data/results'

export const pct = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined ? '–' : `${(v * 100).toFixed(digits)}%`

export const ms = (v: number | null | undefined) =>
  v === null || v === undefined ? '–' : v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${v.toFixed(v < 10 ? 1 : 0)} ms`

export function requirementScore(profile: ProfileName, req: RequirementId) {
  return AUDITS[profile].scores.byRequirement.find((s) => s.key === req)!
}

export const e1Summary = (p: ProfileName) => E1.summary.find((s) => s.profile === p)
export const e2Summary = (p: ProfileName) => E2.summary.find((s) => s.profile === p)
export const e3Summary = (p: ProfileName) => E3.summary.find((s) => s.profile === p)

const factor = (p: ProfileName) => {
  const f = e1Summary(p)?.interferenceFactor
  return f === null || f === undefined ? '–' : `×${f.toFixed(1)}`
}

export const EVIDENCE: Readonly<Record<RequirementId, string[]>> = {
  R1: [
    `E3: ${pct(e3Summary('hardened')?.attributionAccuracy)} of detections attributed to the right tenant`,
    `Unattributed workloads detected (DET-05) in both profiles`,
  ],
  R2: [
    `E2: ${e2Summary('hardened')?.openPaths ?? '–'}/${e2Summary('hardened')?.probes ?? '–'} isolation paths open when hardened, ${e2Summary('insecure')?.openPaths ?? '–'}/${e2Summary('insecure')?.probes ?? '–'} insecure`,
    `E1: p99 latency under a noisy neighbour ${factor('hardened')} hardened vs ${factor('insecure')} insecure`,
  ],
  R3: [
    `Per-tenant CPU, throttling, memory and PSI sampled every 5 s`,
    `E3: noisy neighbour flagged in ${ms(
      E3.results.find((r) => r.profile === 'insecure' && r.triggerId === 'T7')?.latencyMs,
    )} (insecure); silent when hardened`,
  ],
  R4: [
    `E3: ${e3Summary('hardened')?.detected ?? '–'}/${e3Summary('hardened')?.expected ?? '–'} isolation-breaking actions detected, median ${ms(e3Summary('hardened')?.medianLatencyMs)}`,
    `${e3Summary('hardened')?.falsePositives ?? '–'} false positives in a ${E3.quietWindowSeconds} s quiet window`,
  ],
}
