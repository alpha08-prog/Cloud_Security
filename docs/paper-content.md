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

### Virtualization radar (Figure 11) — approximate, scale 0–25

Measured from the figure rendered at 900 dpi (5 scale units ≈ 245 px; values read
along each axis from the centre). Listed in the figure's clockwise axis order,
starting at the top.

| Sub-issue                 | Concern | Solution |
|---------------------------|---------|----------|
| Hypervisor vulnerabilities| 21      | 8        |
| Cross-VM attacks          | 21      | 1        |
| Isolation                 | 20      | 3        |
| Data leakage              | 16      | 5        |
| VM identification         | 15      | 2        |

Mark these as "approximate values read from Fig 11" in the UI. This matches the
paper's text (p.10): "The contrast related to isolation and cross-VM attacks is
more evident than for the other issues."

### Notes on the source figures

- The paper's text swaps the Figure 7 and Figure 8 references. The *image* captioned
  Figure 8 is the grouped-category solutions pie; the image captioned Figure 7 is the
  sub-category solutions pie. This file and the app cite the images.
- The p.9 text gives grouped solution shares as legal 29% / compliance 27%; the Figure 8
  chart shows Compliance 29% / Legal issues 27%. We use the chart values.

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
  The paper (p.12) lists its thirteen domains as:
  1. Governance and risk management · 2. Legal issues · 3. Compliance and audit ·
  4. Information management and data security · 5. Portability and interoperability ·
  6. Traditional security, business continuity and disaster recovery ·
  7. Data center operations · 8. Incident response, notification and remediation ·
  9. Application security · 10. Encryption and key management ·
  11. Identity and access management · 12. Virtualization · 13. Security as a service.
  On multi-tenancy (p.12): the guidance "denotes multi-tenancy as the essential cloud
  characteristic while virtualization can be avoided when implementing cloud
  infrastructures … even if virtualization-related issues can be circumvented,
  segmentation and isolated policies for addressing proper management and privacy are
  still required."
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

Further quotes used by the app:

- CSA Top Threat 4, *Shared technology vulnerabilities* (p.13): "scalability provided by
  cloud solutions are based on hardware and software components which are not originally
  designed to provide isolation. Even though hypervisors offer an extra granularity layer,
  they still exhibit flaws which are exploited for privilege escalation".
- ENISA (p.12): "Key points to be developed include breach reporting, better logging
  mechanisms and engineering of large scale computer systems, which encompass the
  isolation of virtual machines, resources and information."

---

## 8. Discussion and future work (pp.15–16) — the brief for IsoLab

Verbatim from the paper:

- p.15: the new problems "are summarized by isolation and hypervisor vulnerabilities (the
  main technical concerns according to the studies and graphics presented)".
- p.16: "the impact of such issues is intensified in cloud computing due to characteristics
  such as multi-tenancy and resource sharing, since actions from a single customer can
  affect all other users that inevitably share the same resources and interfaces."
- p.16: "It is strategic to develop new mechanisms that provide the required security
  level by isolating virtual machines and the associated resources while following best
  practices in terms of legal regulations and compliance to SLAs. Among other
  requirements, such solutions should employ virtual machine identification, provide an
  adequate separation of dedicated resources combined with a constant observation of
  shared ones, and examine any attempt of exploiting cross-VM and data leakage."
- p.16: "A secure cloud computing environment depends on several security solutions
  working harmoniously together. … Thus, cloud providers need to orchestrate / harmonize
  security solutions from different places in order to achieve the desired security
  level."
- p.16: "In order to verify these conclusions in practice, we deployed testbeds using
  OpenNebula (based on KVM and XEN) and analyzed its security aspects; we also analyzed
  virtualized servers based on VMWARE using our testbed networks."

**Our reading (not the paper's words)** — the four requirements IsoLab implements:

| Id | Paper phrase | Our interpretation |
|----|--------------|--------------------|
| R1 | "virtual machine identification" | Every workload carries a verifiable tenant identity; nothing runs unattributed; every alert names a tenant. |
| R2 | "adequate separation of dedicated resources" | Each tenant gets its own CPU cores, memory/PID limits, network and storage, and no shared kernel namespaces or privileges. |
| R3 | "constant observation of shared ones" | Continuous per-tenant telemetry of the shared host (CPU, throttling, memory, network, pressure stall) with a noisy-neighbour alert. |
| R4 | "examine any attempt of exploiting cross-VM and data leakage" | Runtime detection of isolation-breaking actions (privileged starts, engine-socket mounts, host-namespace joins, cross-tenant attaches, canary hits). |

In IsoLab a tenant is a container rather than a VM. The CSA guidance quoted in §7 is the
justification: multi-tenancy, not virtualization, is the essential characteristic, and
segmentation and isolation are required either way. Containers share a kernel, so they
are the *harder* isolation case.
