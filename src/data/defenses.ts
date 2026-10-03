// Threat → defense matrix, mirrored from docs/paper-content.md §6.
//
// The paper names the concerns; these controls are current, published best
// practice that answer them — they are not taken from the paper itself.
import type { CategoryId } from './taxonomy'

export interface DefenseEntry {
  category: CategoryId
  controls: readonly string[]
}

export const DEFENSES: readonly DefenseEntry[] = [
  {
    category: 'network-security',
    controls: [
      'TLS everywhere + VPN/private link for data in transit',
      'Security groups and micro-segmentation',
      'Managed DDoS protection',
      'Review WAF/firewall rules for SSRF and egress',
      'IDS/IPS on east-west traffic',
    ],
  },
  {
    category: 'interfaces',
    controls: [
      'OAuth2/OIDC + MFA',
      'Least-privilege IAM, no standing admin credentials',
      'API gateway with rate limiting and schema validation',
      'Signed requests',
      'IMDSv2 (session-token metadata) to blunt SSRF → credential theft',
    ],
  },
  {
    category: 'data-security',
    controls: [
      'Encryption at rest and in transit',
      'Envelope encryption with a KMS and routine key rotation',
      'Crypto-shredding for disposal',
      'Verified, integrity-checked backups',
      'DLP on egress',
    ],
  },
  {
    category: 'virtualization',
    controls: [
      'Dedicated / bare-metal instances to avoid co-residency',
      'Placement hardening so an attacker can’t force co-location',
      'Cache partitioning (e.g. Intel CAT) and page coloring',
      'Constant-time cryptography',
      'Disable SMT/hyper-threading for sensitive workloads',
      'Minimal, promptly patched hypervisor (small TCB)',
      'Scrub memory on deallocation',
    ],
  },
  {
    category: 'governance',
    controls: [
      'Explicit shared-responsibility model',
      'CSPM for continuous config/drift detection',
      'Data classification and a live asset inventory',
      'Contractual right-to-audit',
    ],
  },
  {
    category: 'compliance',
    controls: [
      'SLAs that include security terms, not just uptime',
      'Automated audit trails and APIs (e.g. CloudTrail-style)',
      'Third-party attestations (SOC 2, ISO 27001)',
      'DR and redundancy',
      'Open standards and exportable formats to resist lock-in',
    ],
  },
  {
    category: 'legal-issues',
    controls: [
      'Region pinning / data-residency controls',
      'Jurisdiction clauses',
      'Client-side encryption so the provider cannot read data (limits subpoena and insider exposure)',
      'Privileged-access management with full logging',
      'An e-discovery readiness plan',
    ],
  },
]
