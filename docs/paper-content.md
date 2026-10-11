# Source of truth — Gonzalez et al. (2012)

Everything the app displays is extracted here so no one has to re-read the PDF.
Treat this file as canonical. If a number in the UI disagrees with this file, this
file wins.

> Gonzalez, N., Miers, C., Redígolo, F., Simplício, M., Carvalho, T., Näslund, M.,
> & Pourzandi, M. (2012). *A quantitative analysis of current security concerns and
> solutions for cloud computing.* Journal of Cloud Computing: Advances, Systems and
> Applications, 1(11). Open Access (CC BY 2.0).

The paper is a **survey/taxonomy** built by counting citations across 200+ references
(academia, orgs: ENISA/CSA/NIST, vendors). For each reference it tallied two things:
did it raise a **concern**, and did it propose a **solution**. The headline finding:
**virtualization is the biggest unsolved gap** — 12% of concern citations but only 3%
of solution citations. Cross-VM / side-channel attacks live inside that gap.

---

## 1. Taxonomy — three dimensions (Figure 1)

```
Cloud security taxonomy
├── Architecture   → Network security, Interfaces, Virtualization
├── Compliance     → Governance (data/security control, lock-in), Compliance (SLA, loss of service, audit)
└── Privacy        → Data security, Legal issues
```

## 2. Architecture tree (Figure 2)

- **Network security**
  - Transfer security: Distributed architectures · Resource sharing · VM synchronization · Data in transit
  - Firewalling: VM isolation · Filtering · DoS prevention · Adapted solutions
  - Security configuration: Protocols · Systems · Technologies · Performance · Efficiency
- **Interfaces**
  - API: Access virtualized elements · Libraries
  - Administrative interface: Remote resources control · VM management · Coding · Deploying · Developing · User access control · Configurations
  - User interface: Service usage · Resource usage
  - Authentication: Enable access · Account types · Multi-tenancy
- **Virtualization**  ← the under-solved category
  - Isolation: Logical isolation · Physical isolation
  - Hypervisor vulnerabilities: Virtualization · Proprietary solutions
  - Data leakage: Confidentiality · Integrity
  - VM identification: Multiple processes · Multiple resources · Multiple users
  - Cross-VM attacks: **Cryptographic key stealing** · **VM placement / overlapping attacks**

## 3. Compliance tree (Figure 3)

- **Service**
  - SLA: Availability · Procedures · Policies
  - Loss of service: Service outage · Chain failures · Customer-side redundancy
  - Audit: Security assessments · Transparency · API
- **Provider** (this branch is the "Governance" category)
  - Data control: Redundancy · Location · File systems · Configurations
  - Security control: Mechanisms · Loss of control over policies · Gaps · Customer-side assessments
  - Lock-in: Standards · Migrations · Service termination

## 4. Privacy tree (Figure 4)

- **Data security**
  - Cryptography: Sensitive data · Regulations
  - Redundancy: Data loss · Data integrity · Data availability
  - Disposal: Data deletion · Data destruction · Log references · Hidden backups
- **Legal issues**
  - Data location: Multiple jurisdictions · Subpoena
  - E-discovery: Law-enforcement measures · Hardware sharing
  - Provider privilege: Malicious insiders · Privilege escalation

---

## 5. Quantitative data

### Grouped categories — EXACT, each sums to 100 (Figures 6 & 8)

Use these for the main dashboard. `gap = solution − concern` (negative = under-solved).

| Category         | Dimension   | Concern % | Solution % | Gap |
|------------------|-------------|-----------|------------|-----|
| Legal issues     | Privacy     | 24        | 27         | +3  |
| Compliance       | Compliance  | 22        | 29         | +7  |
| Governance       | Compliance  | 17        | 14         | −3  |
| Virtualization   | Architecture| 12        | 3          | **−9** |
| Data security    | Privacy     | 10        | 9          | −1  |
| Interfaces       | Architecture| 8         | 10         | +2  |
| Network security | Architecture| 7         | 8          | +1  |

**Story:** virtualization is the only large deficit. Everything institutional
(legal/compliance/governance) is well covered; the deep technical problem is not.

### Sub-categories (Figures 5 & 7) — read from charts, treat as approximate

Concerns (Fig 5), %: Legislation 10 · Service conformity 9 · Data control 9 ·
Isolation 7 · Audit 6 · Provider privilege 6 · Cryptography 6 · Security control 5 ·
Transfer security 5 · SLA 5 · Data location 5 · Hypervisor vulnerabilities 5 ·
e-Discovery 4 · Lock-in 3 · Authentication 3 · Redundancy 2 · Disposal 2 ·
User interface 2 · Administrative interface 2 · API 2 · Firewalling 2 ·
Security configuration 1 · Loss of service 1.

Solutions (Fig 7), %: Service conformity 12 · Legislation 12 · Audit 8 · Data control 8 ·
SLA 7 · Provider privilege 7 · Transfer security 5 · Data location 4 · Cryptography 4 ·
e-Discovery 4 · Security control 3 · Authentication 3 · User interface 3 · Lock-in 3 ·
Redundancy 3 · Administrative interface 2 · Disposal 2 · Firewalling 2 ·
Hypervisor vulnerabilities 2 · API 2 · Loss of service 1 · Isolation 1 ·
Security configuration 1.

### Virtualization radar (Figure 11) — approximate, scale ~0–25

| Sub-issue                 | Concern | Solution |
|---------------------------|---------|----------|
| Isolation                 | 22      | 3        |
| Cross-VM attacks          | 20      | 1        |
| Hypervisor vulnerabilities| 20      | 2        |
| Data leakage              | 18      | 1        |
| VM identification         | 15      | 1        |

Mark these as "approximate values read from Fig 11" in the UI.

---

## 6. Threat → Defense matrix (for the "remedies" section)

The paper names the concerns; these are the concrete modern controls that answer them.
Written as defenses — standard, published best practice.

- **Network security** — TLS everywhere + VPN/private link for data in transit; security
  groups and micro-segmentation; managed DDoS protection; review WAF/firewall rules for
  SSRF and egress; IDS/IPS on east-west traffic.
- **Interfaces** — OAuth2/OIDC + MFA; least-privilege IAM, no standing admin creds; API
  gateway with rate limiting and schema validation; signed requests; IMDSv2 (session-token
  metadata) to blunt SSRF→credential theft.
- **Data security** — encryption at rest and in transit; envelope encryption with a KMS and
  routine key rotation; crypto-shredding for disposal; verified, integrity-checked backups;
  DLP on egress.
- **Virtualization** (the gap) — dedicated / bare-metal instances to avoid co-residency;
  placement hardening so an attacker can't force co-location; cache partitioning (e.g. Intel
  CAT) and page coloring; constant-time cryptography; disable SMT/hyper-threading for
  sensitive workloads; minimal, promptly patched hypervisor (small TCB); scrub memory on
  deallocation.
- **Governance** — explicit shared-responsibility model; CSPM for continuous config/drift
  detection; data classification and a live asset inventory; contractual right-to-audit.
- **Compliance** — SLAs that include security terms, not just uptime; automated audit trails
  and APIs (e.g. CloudTrail-style); third-party attestations (SOC 2, ISO 27001); DR and
  redundancy; open standards and exportable formats to resist lock-in.
- **Legal issues** — region pinning / data-residency controls; jurisdiction clauses;
  client-side encryption so the provider cannot read data (limits subpoena and insider
  exposure); privileged-access management with full logging; an e-discovery readiness plan.

---

## 7. Frameworks (Tables 1 & 2)

- **CSA Guidance** — recommendations to reduce risk; one architectural + governance and
  operational domains; stresses cloud is not bound to virtualization but depends on it.
- **CSA Top Threats (7)** — abuse & nefarious use of cloud · insecure APIs · malicious
  insiders · shared-technology vulnerabilities · data loss & leakage · account/service/
  traffic hijacking · unknown risk profile (security obscurity).
- **CSA TCI Architecture** — trust via standards; four framework sets (security, NIST SPI,
  IT audit, legislative) and four architectural domains (SABSA, ITIL, Jericho, TOGAF);
  tri-dimensional: cloud delivery × trust × operation.
- **ENISA report** — benefits and risks of cloud; risks in four classes: policy &
  organizational · technical · legal · not-cloud-specific. Top recommendation: providers
  must give customers security assurances and a clear contract.
- **NIST taxonomy (SP 500-292)** — roles-first: cloud provider · consumer · carrier · broker
  · auditor; defines what services should provide rather than how to build them.
