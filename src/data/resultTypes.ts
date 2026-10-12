// TypeScript view of the IsoLab results contract. The source of truth is the
// pydantic models in auditor/src/cloudaudit (generated into schemas/*.schema.json);
// results.test.ts validates every published file against those schemas, so these
// types and the data cannot drift apart unnoticed.

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
}
