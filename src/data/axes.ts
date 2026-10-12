// Figure 11's five virtualization sub-issues, used as the axes of every IsoLab
// coverage chart. Ids are slugs of the taxonomy labels (Figure 2) and match the
// auditor's `axis` values exactly (contract-tested).
import type { Axis } from './resultTypes'
import { VIRTUALIZATION_RADAR } from './stats'

export interface AxisInfo {
  id: Axis
  label: string
  /** Approximate citation counts read from Figure 11. */
  paperConcern: number
  paperSolution: number
  /** What the auditor checks on this axis, in a phrase. */
  checks: string
}

const slug = (label: string) =>
  label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')

const WHAT: Record<Axis, string> = {
  'hypervisor-vulnerabilities': 'engine API exposure, patch level, CPU-flaw mitigations, kernel hardening',
  'cross-vm-attacks': 'shared networks, host network, published ports, SMT siblings, KSM, live tripwires',
  isolation: 'privileges, capabilities, seccomp, namespaces, limits, dedicated CPU sets',
  'data-leakage': 'host mounts, shared volumes, shared IPC, read-only root, secrets in env',
  'vm-identification': 'identity labels, unattributed workloads, placement, image provenance, observation',
}

/** In Figure 11's clockwise order, starting at the top. */
export const AXES: readonly AxisInfo[] = VIRTUALIZATION_RADAR.map((v) => {
  const id = slug(v.issue) as Axis
  return { id, label: v.issue, paperConcern: v.concern, paperSolution: v.solution, checks: WHAT[id] }
})

export const AXIS_LABEL: Readonly<Record<Axis, string>> = Object.fromEntries(
  AXES.map((a) => [a.id, a.label]),
) as Record<Axis, string>
