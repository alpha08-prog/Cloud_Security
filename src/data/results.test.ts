// Contract between the auditor (Python) and this app: the published results must
// match the generated schemas, reference only real taxonomy nodes and framework
// items, and produce the same scores when recomputed here.
import Ajv2020 from 'ajv/dist/2020'
import { describe, expect, it } from 'vitest'
import auditSchema from '../../schemas/audit-report.schema.json'
import experimentsSchema from '../../schemas/experiments.schema.json'
import { coverage, pairsFor } from '../lib/scoring'
import { AXES } from './axes'
import { VIRTUALIZATION_DEFENSE_NOTES } from './defenseNotes'
import { FRAMEWORKS } from './frameworks'
import { REQUIREMENTS } from './requirements'
import { AUDITS, CATALOGUE, CHECK_BY_ID, E1, E2, E3, PROFILES } from './results'
import { TAXONOMY_FIGURES, indexFigure } from './taxonomy'

const ajv = new Ajv2020({ strict: false, allErrors: true })
const validateAudit = ajv.compile(auditSchema)
const validateExperiment = ajv.compile(experimentsSchema)

const slug = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')

const listItems = (frameworkId: string, label?: string) => {
  const f = FRAMEWORKS.find((x) => x.id === frameworkId)!
  const list = label ? f.lists!.find((l) => l.label.startsWith(label))! : f.lists![0]
  return list.items
}

describe('published results match the schemas', () => {
  it.each(PROFILES)('audit-%s.json', (profile) => {
    const ok = validateAudit(AUDITS[profile])
    expect(validateAudit.errors ?? [], JSON.stringify(validateAudit.errors?.slice(0, 3))).toEqual([])
    expect(ok).toBe(true)
  })

  it.each([
    ['e1', E1],
    ['e2', E2],
    ['e3', E3],
  ])('%s.json', (_name, doc) => {
    const ok = validateExperiment(doc)
    expect(validateExperiment.errors ?? [], JSON.stringify(validateExperiment.errors?.slice(0, 3))).toEqual([])
    expect(ok).toBe(true)
  })
})

describe('catalogue references resolve', () => {
  const nodes = new Set(TAXONOMY_FIGURES.slice(1).flatMap((f) => [...indexFigure(f).keys()]))

  it('both profiles were audited with the same catalogue', () => {
    expect(AUDITS.insecure.catalogue).toEqual(AUDITS.hardened.catalogue)
    expect(CATALOGUE).toHaveLength(30)
  })

  it('every taxonomy id is a node of Figures 2-4', () => {
    for (const c of CATALOGUE) for (const t of c.taxonomy) expect(nodes.has(t), `${c.id}: ${t}`).toBe(true)
  })

  it('axes are exactly the Figure 11 sub-issues, each with at least three checks', () => {
    expect(new Set(CATALOGUE.map((c) => c.axis))).toEqual(new Set(AXES.map((a) => a.id)))
    for (const a of AXES) expect(CATALOGUE.filter((c) => c.axis === a.id).length).toBeGreaterThanOrEqual(3)
  })

  it('framework values come from the paper’s framework lists', () => {
    const threats = listItems('csa-top-threats').length
    const enisa = new Set(listItems('enisa').map(slug))
    const nist = new Set(listItems('nist').map(slug))
    const domains = new Set(listItems('csa-guidance', 'Domains').map(slug))
    for (const c of CATALOGUE) {
      for (const t of c.frameworks.csaTopThreats) expect(t >= 1 && t <= threats, c.id).toBe(true)
      for (const e of c.frameworks.enisa) expect(enisa.has(e), `${c.id}: ${e}`).toBe(true)
      for (const n of c.frameworks.nist) expect(nist.has(n), `${c.id}: ${n}`).toBe(true)
      for (const d of c.frameworks.csaDomains) expect(domains.has(d), `${c.id}: ${d}`).toBe(true)
    }
  })

  it('every requirement is served by a check, a detection or an experiment', () => {
    for (const r of REQUIREMENTS) {
      const checks = CATALOGUE.filter((c) => c.requirements.includes(r.id))
      expect(checks.length + r.detections.length, r.id).toBeGreaterThan(0)
    }
  })

  it('defense notes only point at real checks', () => {
    for (const [control, note] of Object.entries(VIRTUALIZATION_DEFENSE_NOTES)) {
      for (const id of note.implementedBy) expect(CHECK_BY_ID.has(id), `${control}: ${id}`).toBe(true)
      expect(note.implementedBy.length > 0 || Boolean(note.outOfScope), control).toBe(true)
    }
  })
})

describe('scores recomputed here match the auditor', () => {
  it.each(PROFILES)('%s', (profile) => {
    const report = AUDITS[profile]
    for (const s of report.scores.byAxis) {
      expect(coverage(s.key, pairsFor(CATALOGUE, report.results, (c) => c.axis === s.key))).toEqual(s)
    }
    for (const s of report.scores.byRequirement) {
      const pairs = pairsFor(CATALOGUE, report.results, (c) => c.requirements.includes(s.key as never))
      expect(coverage(s.key, pairs)).toEqual(s)
    }
    for (const s of report.scores.unweightedByAxis) {
      expect(coverage(s.key, pairsFor(CATALOGUE, report.results, (c) => c.axis === s.key), false)).toEqual(s)
    }
    expect(coverage('overall', pairsFor(CATALOGUE, report.results))).toEqual(report.scores.overall)
  })
})

describe('published results support what the app claims', () => {
  it('hardened passes its gate; insecure fails at least one check on every axis', () => {
    expect(AUDITS.hardened.gate.passed).toBe(true)
    for (const a of AXES) {
      const failing = AUDITS.insecure.results.filter(
        (r) => r.status === 'fail' && CHECK_BY_ID.get(r.checkId)!.axis === a.id,
      )
      expect(failing.length, a.id).toBeGreaterThan(0)
    }
  })

  it('E2: hardened closes every path and keeps every control open', () => {
    const s = E2.summary.find((x) => x.profile === 'hardened')!
    expect(s.openPaths).toBe(0)
    expect(s.controlsPassed).toBe(s.controls)
  })

  it('E3: every expected detection fired in time, with no false positives', () => {
    for (const s of E3.summary) {
      expect(s.detected, s.profile).toBe(s.expected)
      expect(s.falsePositives, s.profile).toBe(0)
    }
  })

  it('E1: every run on display is valid', () => {
    for (const r of E1.runs) expect(r.valid, `${r.profile} ${r.arm} ${r.repetition}`).toBe(true)
  })
})
