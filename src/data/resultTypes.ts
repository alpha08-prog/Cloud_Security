// TypeScript view of the IsoLab results contract. The source of truth is the
// pydantic models in auditor/src/cloudaudit (generated into schemas/*.schema.json);
// results.test.ts validates every published file against those schemas, so these
// types and the data cannot drift apart unnoticed.
import type { CategoryId } from './taxonomy'

export type Axis =
  | 'hypervisor-vulnerabilities'
  | 'cross-vm-attacks'
  | 'isolation'
  | 'data-leakage'
  | 'vm-identification'
export type Status = 'pass' | 'warn' | 'fail' | 'error' | 'skip'
export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type RequirementId = 'R1' | 'R2' | 'R3' | 'R4'
export type ProfileName = 'insecure' | 'hardened'
export type Verdict = 'supported' | 'not-supported' | 'inconclusive'

export interface CheckSpec {
  id: string
  title: string
  description: string
  axis: Axis
  requirements: RequirementId[]
  severity: Severity
  scope: 'container' | 'network' | 'volume' | 'fleet' | 'host' | 'self'
  taxonomy: string[]
  frameworks: { csaTopThreats: number[]; csaDomains: string[]; enisa: string[]; nist: string[] }
  remediation: string
  platformNotes: string | null
}

export interface Target {
  kind: string
  ref: string
  tenant: string | null
  workloadId: string | null
  status: Status
  message: string
  evidence: Record<string, unknown>
  location: { file: string; line: number } | null
}

export interface CheckResult {
  checkId: string
  status: Status
  waived: boolean
  waiver: { reason: string; expires: string; approvedBy: string; platform: string } | null
  message: string
  targets: Target[]
}

export interface Score {
  key: string
  score: number | null
  earned: number
  possible: number
  evaluated: number
  skipped: number
  total: number
}

export interface Environment {
  platform: string
  dockerServerVersion: string
  kernelVersion: string
  operatingSystem?: string
  logicalCpus: number
  physicalCores: number
}

export interface AuditReport {
  schemaVersion: string
  kind: 'audit'
  generatedAt: string
  profile: ProfileName
  tool: { name: string; version: string; gitSha: string | null }
  environment: Environment & { cgroupVersion: string; cgroupDriver: string; smtActive: boolean | null }
  policySha256: string
  catalogue: CheckSpec[]
  results: CheckResult[]
  scores: { byAxis: Score[]; byRequirement: Score[]; overall: Score; unweightedByAxis: Score[] }
  gate: { failOn: Severity; passed: boolean; blocking: string[]; waived: string[]; expiredWaivers: string[] }
}

export interface Hypothesis {
  id: string
  statement: string
  verdict: Verdict
  detail: string
}

interface RunEnvironment extends Environment {
  gitSha: string | null
  placement: Record<string, string>
}

interface ExperimentBase {
  schemaVersion: string
  generatedAt: string
  variant: 'full' | 'ci'
  environment: RunEnvironment
  hypotheses: Hypothesis[]
}

export interface Percentiles {
  avg: number
  min: number
  med: number
  p90: number
  p95: number
  p99: number
  max: number
}

export interface E1Run {
  profile: ProfileName
  arm: 'baseline' | 'noisy'
  repetition: number
  startedAt: string
  latencyMs: Percentiles
  serverWorkMs: Percentiles | null
  failedRate: number
  droppedIterations: number
  iterations: number
  noisyCoresUsed: number | null
  victimCpuPressurePct: number | null
  throttledSeconds: Record<string, number>
  valid: boolean
  invalidReason: string | null
}

export interface E1Result extends ExperimentBase {
  kind: 'e1'
  config: {
    ratePerSecond: number
    warmupSeconds: number
    measureSeconds: number
    repetitions: number
    stressWorkers: number
    workIterations: number
    sloP99Ms: number
  }
  runs: E1Run[]
  summary: {
    profile: ProfileName
    baselineP99Ms: number | null
    noisyP99Ms: number | null
    interferenceFactor: number | null
    sloMetUnderNoise: boolean | null
    validRuns: number
    totalRuns: number
  }[]
}

export interface E2Probe {
  id: string
  description: string
  source: string
  destination: string
  control: boolean
  axis: Axis
  expected: Record<ProfileName, 'allowed' | 'blocked' | 'platform-dependent'>
}

export interface E2Result extends ExperimentBase {
  kind: 'e2'
  probes: E2Probe[]
  results: {
    profile: ProfileName
    probeId: string
    outcome: 'allowed' | 'blocked' | 'error'
    detail: string
    asExpected: boolean
  }[]
  summary: { profile: ProfileName; openPaths: number; probes: number; controlsPassed: number; controls: number }[]
}

export interface E3Trigger {
  id: string
  description: string
  expectedRule: string
  expect: Record<ProfileName, 'detect' | 'silent'>
  expectedTenant: Record<ProfileName, string | null>
  sloMs: number
  requirements: RequirementId[]
}

export interface E3Result extends ExperimentBase {
  kind: 'e3'
  quietWindowSeconds: number
  triggers: E3Trigger[]
  results: {
    profile: ProfileName
    triggerId: string
    expected: 'detect' | 'silent'
    detected: boolean
    rule: string | null
    tenant: string | null
    latencyMs: number | null
    withinSlo: boolean
    attributionCorrect: boolean | null
    asExpected: boolean
  }[]
  falsePositives: { profile: ProfileName; rule: string; tenant: string | null; message: string }[]
  summary: {
    profile: ProfileName
    detectionRate: number
    detected: number
    expected: number
    falsePositives: number
    medianLatencyMs: number | null
    maxLatencyMs: number | null
    attributionAccuracy: number | null
  }[]
}

export interface Manifest {
  generatedAt: string
  platform: string
  gitSha: string
  files: string[]
  replicationGeneratedAt?: string
}

// ---------------------------------------------------------------------------
// Replication of the survey's counting method (docs/replication.md).

/** 95% interval [low, high]. */
export type Interval = [number, number]
/** "2012" (the survey's Figures 6/8), an era id such as "2013-2017", or "pooled". */
export type Period = string

export interface RepEra {
  id: string
  label: string
  seed: number
  firstYear: number
  lastYear: number
  partial: boolean
}

export interface RepCategory {
  era: Period
  category: CategoryId
  concernPct: number | null
  solutionPct: number | null
  gapPts: number | null
  concernCi: Interval | null
  solutionCi: Interval | null
  gapCi: Interval | null
  concernEntries: number | null
  solutionEntries: number | null
}

export interface RepSubcategory {
  era: Period
  subcategory: string
  category: CategoryId
  concernPct: number | null
  solutionPct: number | null
  concernEntries: number | null
  solutionEntries: number | null
}

export interface RepAxis {
  era: Period
  axis: Axis
  concernEntries: number | null
  solutionEntries: number | null
  ratio: number | null
  ratioCi: Interval | null
}

export interface RepRobustness {
  id: 'main' | 'RB1' | 'RB2' | 'RB3' | 'RB4'
  label: string
  era: Period
  gapPts: number | null
  gapCi: Interval | null
}

export interface RepScores {
  tp: number
  fp: number
  fn: number
  tn: number
  precision: number | null
  recall: number | null
  f1: number | null
  kappa: number | null
}

export interface RepGate {
  met: boolean
  checks: Record<string, { value: number | null; threshold: number; met: boolean }>
}

export interface RepAgreement {
  n: number
  gate: RepScores
  concern: Record<CategoryId, RepScores>
  solution: Record<CategoryId, RepScores>
  axes: Record<Axis, RepScores>
  macroF1: { concern: number | null; solution: number | null }
  microF1: { concern: number | null; solution: number | null }
  meanKappa: number | null
  typeKappa: number | null
  typeConfusion: Record<string, number>
  offTopic: number
  validityGate: RepGate
  ci?: Record<string, Interval | null> | null
}

export interface RepCveYear {
  year: number
  total: number
  partial: boolean
  counts: Record<string, number>
  per10k: Record<string, number | null>
}

export interface ReplicationResult {
  schemaVersion: string
  kind: 'replication'
  generatedAt: string
  protocol: {
    document: string
    query: string
    eras: RepEra[]
    samplePerEra: number
    frozenAt: string
    rulesSha256: Record<string, string>
    corpusSha256: Record<string, string>
    nvdSha256: string
    bootstrapB: number
    bootstrapSeed: number
    unit: string
    solutionRule: string
    deviations: string[]
  }
  hypotheses: Hypothesis[]
  validityGateMet: boolean
  flow: {
    era: string
    population: number
    sampled: number
    unique: number
    excluded: Record<string, number>
    analysed: number
    inScope: number
  }[]
  categories: RepCategory[]
  subcategories: RepSubcategory[]
  axes: RepAxis[]
  robustness: RepRobustness[]
  validation: {
    n: number
    screens: number
    repeats: number
    unsure: number
    completedAt: string | null
    weighted: RepAgreement
    unweighted: RepAgreement
    selfAgreement: {
      pairs: number
      onTopicAgreement: number | null
      categoryKappa: number | null
      typeKappa: number | null
    }
    dev: Record<string, RepAgreement>
  }
  publishers: { publisher: string; works: number }[]
  cve: {
    source: string
    retrievedAt: string
    sha256: string
    candidates: number
    axes: string[]
    notMeasured: string[]
    deviations: string[]
    years: RepCveYear[]
    spotCheck: Record<
      string,
      {
        n: number
        correct: number
        precision: number | null
        nWithD1: number
        correctWithD1: number
        precisionWithD1: number | null
      }
    > | null
  }
  limitations: string[]
}
