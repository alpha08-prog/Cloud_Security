// The four requirements IsoLab implements, from the paper's "Considerations and
// future work" (p.16) - see docs/paper-content.md §8. The paper phrase is quoted;
// the interpretation and mechanisms are ours.
import type { RequirementId } from './resultTypes'

export interface Requirement {
  id: RequirementId
  short: string
  /** Verbatim from the paper (p.16). */
  phrase: string
  interpretation: string
  mechanisms: readonly string[]
  /** Runtime detections that serve the requirement. */
  detections: readonly string[]
  /** Experiments that produce its evidence. */
  experiments: readonly ('E1' | 'E2' | 'E3')[]
  /** Shown under the coverage figures when they need explaining. */
  coverageNote?: string
}

export const PAPER_QUOTE =
  'It is strategic to develop new mechanisms that provide the required security level by isolating virtual machines and the associated resources while following best practices in terms of legal regulations and compliance to SLAs. Among other requirements, such solutions should employ virtual machine identification, provide an adequate separation of dedicated resources combined with a constant observation of shared ones, and examine any attempt of exploiting cross-VM and data leakage.'

export const REQUIREMENTS: readonly Requirement[] = [
  {
    id: 'R1',
    short: 'Identification',
    phrase: 'employ virtual machine identification',
    interpretation:
      'Every workload carries a verifiable tenant identity, nothing runs unattributed, and every alert names a tenant.',
    mechanisms: [
      'Identity labels on every container, network and volume',
      'Images pinned by digest or built from a pinned base with provenance labels',
      'Detection of unattributed workloads; canary hits traced to a tenant by source IP',
    ],
    detections: ['DET-05', 'DET-07'],
    experiments: ['E3'],
  },
  {
    id: 'R2',
    short: 'Separation',
    phrase: 'provide an adequate separation of dedicated resources',
    interpretation:
      'Each tenant gets its own CPU cores, memory and PID limits, network and storage, and shares no kernel namespace or privilege.',
    mechanisms: [
      'Physical-core CPU sets planned from the real topology (no SMT sibling shared across tenants)',
      'CPU quota, memory = swap limit, PID limit per tenant',
      'One internal network and one volume per tenant',
      'Non-root, all capabilities dropped, no-new-privileges, seccomp, read-only root filesystem',
    ],
    detections: ['DET-02'],
    experiments: ['E1', 'E2'],
  },
  {
    id: 'R3',
    short: 'Observation',
    phrase: 'combined with a constant observation of shared ones',
    interpretation:
      'The shared host is watched per tenant, continuously: CPU, throttling, memory, network and pressure stall, with a noisy-neighbour alert.',
    mechanisms: [
      'cgroup v2 counters and pressure-stall information (PSI) every 5 s, exported to Prometheus',
      'Fair-share noisy-neighbour rule on shared CPUs',
      'Host posture checks: CPU-flaw mitigations, kernel hardening, engine patch level',
    ],
    detections: ['DET-08', 'DET-09'],
    experiments: ['E1', 'E3'],
    coverageNote:
      'Same in both profiles by design: observation is the provider’s job, and the provider plane does not change between them.',
  },
  {
    id: 'R4',
    short: 'Examination',
    phrase: 'examine any attempt of exploiting cross-VM and data leakage',
    interpretation:
      'Actions that break tenant isolation are detected live, within seconds, from the engine event stream and a decoy service.',
    mechanisms: [
      'Engine-event watcher: privileged starts, engine-socket mounts, host-namespace joins, cross-tenant attaches, execs',
      'Canary "metadata" decoy on the provider network',
      'Tripwire self-check (watcher heartbeat, canary health, alert rules loaded)',
    ],
    detections: ['DET-01', 'DET-03', 'DET-04', 'DET-06', 'DET-07'],
    experiments: ['E3'],
  },
]

export const DETECTION_RULES: Readonly<Record<string, string>> = {
  'DET-01': 'Interactive exec into a tenant',
  'DET-02': 'Privileged workload started',
  'DET-03': 'Engine socket mounted into a workload',
  'DET-04': 'Workload joined a host namespace',
  'DET-05': 'Unattributed workload started',
  'DET-06': "Workload attached to another tenant's network",
  'DET-07': 'Decoy metadata service contacted',
  'DET-08': 'Noisy neighbour on shared CPUs',
  'DET-09': 'Workload killed by its memory limit',
}
