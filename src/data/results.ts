// IsoLab results, imported at build time from results/published/ (written only by
// `python scripts/lab.py publish`, never by hand). Narrowed here so a wrong file
// or an incompatible schema major version fails loudly at build/test time.
import auditHardenedJson from '../../results/published/audit-hardened.json'
import auditInsecureJson from '../../results/published/audit-insecure.json'
import e1Json from '../../results/published/e1.json'
import e2Json from '../../results/published/e2.json'
import e3Json from '../../results/published/e3.json'
import manifestJson from '../../results/published/manifest.json'
import type {
  AuditReport,
  E1Result,
  E2Result,
  E3Result,
  Manifest,
  ProfileName,
} from './resultTypes'

export const SUPPORTED_SCHEMA_MAJOR = 1

function narrow<T extends { kind: string; schemaVersion: string }>(doc: unknown, kind: T['kind']): T {
  const d = doc as T
  if (d.kind !== kind) throw new Error(`expected a ${kind} result, got ${d.kind}`)
  const major = Number(d.schemaVersion.split('.')[0])
  if (major !== SUPPORTED_SCHEMA_MAJOR) {
    throw new Error(`${kind}: schema ${d.schemaVersion} is not supported (need ${SUPPORTED_SCHEMA_MAJOR}.x)`)
  }
  return d
}

export const AUDITS: Readonly<Record<ProfileName, AuditReport>> = {
  insecure: narrow<AuditReport>(auditInsecureJson, 'audit'),
  hardened: narrow<AuditReport>(auditHardenedJson, 'audit'),
}
export const E1 = narrow<E1Result>(e1Json, 'e1')
export const E2 = narrow<E2Result>(e2Json, 'e2')
export const E3 = narrow<E3Result>(e3Json, 'e3')
export const MANIFEST = manifestJson as Manifest

export const PROFILES: readonly ProfileName[] = ['insecure', 'hardened']

export const PROFILE_LABEL: Readonly<Record<ProfileName, string>> = {
  insecure: 'Insecure',
  hardened: 'Hardened',
}

/** The check catalogue is identical in both reports (a contract test enforces it). */
export const CATALOGUE = AUDITS.hardened.catalogue
export const CHECK_BY_ID = new Map(CATALOGUE.map((c) => [c.id, c]))
