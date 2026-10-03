// Framework summaries (Tables 1 & 2), mirrored from docs/paper-content.md §7.

export type FrameworkOrg = 'CSA' | 'ENISA' | 'NIST'

export interface FrameworkList {
  label: string
  items: readonly string[]
}

export interface Framework {
  id: string
  org: FrameworkOrg
  name: string
  points: readonly string[]
  lists?: readonly FrameworkList[]
}

export const FRAMEWORKS: readonly Framework[] = [
  {
    id: 'csa-guidance',
    org: 'CSA',
    name: 'CSA Guidance',
    points: [
      'Recommendations to reduce risk.',
      'One architectural domain plus governance and operational domains.',
      'Stresses that cloud is not bound to virtualization, but depends on it.',
    ],
  },
  {
    id: 'csa-top-threats',
    org: 'CSA',
    name: 'CSA Top Threats',
    points: ['Seven top threats to cloud computing.'],
    lists: [
      {
        label: 'Threats',
        items: [
          'Abuse & nefarious use of cloud',
          'Insecure APIs',
          'Malicious insiders',
          'Shared-technology vulnerabilities',
          'Data loss & leakage',
          'Account/service/traffic hijacking',
          'Unknown risk profile (security obscurity)',
        ],
      },
    ],
  },
  {
    id: 'csa-tci',
    org: 'CSA',
    name: 'CSA TCI Architecture',
    points: [
      'Trust via standards.',
      'Tri-dimensional: cloud delivery × trust × operation.',
    ],
    lists: [
      { label: 'Framework sets', items: ['Security', 'NIST SPI', 'IT audit', 'Legislative'] },
      { label: 'Architectural domains', items: ['SABSA', 'ITIL', 'Jericho', 'TOGAF'] },
    ],
  },
  {
    id: 'enisa',
    org: 'ENISA',
    name: 'ENISA report',
    points: [
      'Benefits and risks of cloud computing.',
      'Top recommendation: providers must give customers security assurances and a clear contract.',
    ],
    lists: [
      {
        label: 'Risk classes',
        items: ['Policy & organizational', 'Technical', 'Legal', 'Not cloud-specific'],
      },
    ],
  },
  {
    id: 'nist',
    org: 'NIST',
    name: 'NIST taxonomy (SP 500-292)',
    points: [
      'Roles-first.',
      'Defines what services should provide rather than how to build them.',
    ],
    lists: [
      { label: 'Roles', items: ['Cloud provider', 'Consumer', 'Carrier', 'Broker', 'Auditor'] },
    ],
  },
]
