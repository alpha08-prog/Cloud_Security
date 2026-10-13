# Replication of Gonzalez et al. (2012)'s counting method, 2013–2026

**Status: pre-registration.** This protocol was written before any classifier ran on the test
set, and before the test set was drawn. Later changes go in the changelog at the bottom, with
a reason, before the data they affect. Paper facts are cited from `paper-content.md`.

## 1. Question and the method being replicated

Gonzalez et al. analysed 200+ references (academic papers, organisational reports, vendor white
papers). For each reference they recorded every security **concern** it raised and every
**solution** it provided, by sub-category; one reference can yield several entries. They then
reported:

- each category's share of all concern entries and of all solution entries (Figs 5–8);
- radars comparing the two (Figs 9–11).

The headline result: **virtualization has 12% of concern entries but 3% of solution entries**
(gap −9 points), the only large deficit. Within it, isolation and cross-VM attacks are the least
answered (Fig 11).

We apply the same counting method to the cloud-security literature of 2013–2026 and ask:
**is the virtualization gap still there?**

What stays identical:
- the unit (one entry per reference × sub-category, concerns and solutions counted separately);
- the 23 sub-categories and their 7 categories (`paper-content.md` §5, pp.2–4);
- the metrics (category share of entries; gap = solution share − concern share; Fig 11 per
  virtualization sub-issue).

What differs (reported as limitations):

| Paper (2012) | This replication |
|---|---|
| 200+ references, mixed academic and industry | a seeded random sample of academic works indexed by OpenAlex |
| full documents, read by the authors | titles and abstracts, classified by frozen keyword rules |
| one analysis pass | rules validated against a blind human-labelled sample |

## 2. Corpus

- **Source:** OpenAlex works API (CC0). The raw records are committed under
  `replication/corpus/` with the query, filters, seeds, OpenAlex `meta.count` and retrieval
  date. The committed snapshot, not a re-query, is what the study analyses.
- **Search:** `title_and_abstract.search` for
  `cloud AND (security OR privacy)`, excluding these phrases: "point cloud", "point clouds",
  "cloud cover", "cloud seeding", "cloud droplet", "cloud microphysics", "molecular cloud",
  "electron cloud", "word cloud", "tag cloud", "cloud forest", "food security",
  "energy security", "water security", "social security", "job security".
- **Filters:** has abstract; language en; type ∈ {article, conference-paper, review,
  book-chapter, preprint, report}; not retracted; not paratext.
- **Eras and sample:** 2013–2017 (seed 2013), 2018–2022 (seed 2018), 2023–2026 (seed 2023;
  2026 is partial). 2,500 works sampled per era with OpenAlex `sample` + `seed`.
- **Normalisation and exclusions,** each counted per era in a flow table:
  - abstract rebuilt from the inverted index; replacement characters → space;
  - kept if 50–600 words and not a stub ("abstract not available", "retracted", …);
  - deduplicated by OpenAlex id, then by normalised title + first 100 characters of the
    abstract (keeping the non-preprint version, else the earliest year, else the lowest id).
- **Dev set:** 150 works (50 per era, seed 7), used only to tune the rules and excluded from the
  analysis. Labelled by the implementer; labels committed.

## 3. Classifier (frozen before the test set is drawn)

Keyword/regex rules in `experiments/replication/lexicon.py` (data) and `classify.py` (logic).
Both are hashed into `replication/freeze.json` (sha256 of the LF-normalised files) before
`rep sample`. After the freeze, any hash mismatch aborts the analysis.

**Terms.**
- Word-boundary matches; `stem*` matches word stems.
- Spaces in a term match spaces or hyphens; plurals are allowed.
- ALL-CAPS acronyms are case-sensitive.
- Each sub-category has its own terms plus exclusions (masked first).
- Generic words ("security", "privacy", "secure", "trust") never count as a sub-category hit.

**False friends masked globally:** isolation forest, isolation level, Java virtual machine / JVM
/ EVM, plus the excluded phrases above.

**Virtualization context.** Terms marked "virtualization context" count only if a context term
is in the same sentence: VM, virtual machine, hypervisor, guest, host OS/kernel, tenant,
container, Docker, Kubernetes, co-resident, co-located, shared hardware, serverless, enclave/TEE.
Generic side channels count as cross-VM only in such a sentence.

**Threat context.** A hypervisor, VMM, container runtime or product name (Xen, KVM, QEMU, ESXi, …)
counts as a *hypervisor vulnerability* only if a threat word (vulnerability, attack, exploit,
flaw, compromise, hijack, malicious, escape, untrusted, TCB, risk, …) is in the same sentence;
naming the platform a system runs on is not a concern about it.

**Scope.** Containers, serverless and trusted execution environments count as virtualization.
Justification: the CSA guidance quoted by the paper (p.12) names multi-tenancy, not
virtualization, as the essential characteristic. RB3 reruns the analysis without them.

**Relevance gate.** An abstract is in scope only if all three hold:
1. a cloud term (cloud, IaaS, PaaS, SaaS, multi-cloud, edge-cloud, fog, data centre, virtual
   machine, container) in the title, or at least 2 in the abstract;
2. a security/privacy/compliance term in the title, or at least 2 in the abstract;
3. at least one sentence (the title counts) that contains both a cloud term and a security term;
4. at least one sub-category hit.

**Type.**
- **Survey** (counts as concern-only): a survey cue (survey, review, systematic literature/mapping,
  state of the art, overview, open issues/challenges, research directions, tutorial, SoK,
  taxonomy) in the title or the first two sentences.
- **Solution:** at least one *contribution sentence*. That means either
  - a subject cue (we, our, this paper/work/article/study, the proposed) plus a proposing verb
    (propose, present, introduce, develop, design, build, implement, construct, …; whole words)
    plus an artifact noun (scheme, framework, protocol, mechanism, system, approach, architecture,
    model, method, technique, algorithm, tool, solution, prototype, countermeasure, defence,
    mitigation, platform, construction, policy, middleware, process, structure, …) in the same
    sentence; or
  - a present-tense passive ("X is proposed / presented / developed", "has been developed").

  Before the test, other people's work and claims are masked: "proposed by", "was/were/recently
  proposed", "et al. proposed", "show/suggest that", "existing scheme/method", "need for/to …".
  A sentence presenting an attack or exploit is not a contribution unless it also has a defensive
  cue (defen*, mitigat*, countermeasure*, detect*, prevent*, protect*, thwart*, resist*).
- **Concern-only** otherwise. This covers measurement, attack and position papers.

**Counting (rule B, "scoped").**
- Each unique (abstract, Fig-5 sub-category) hit is one **concern entry**.
- A solution-type abstract also gets one **solution entry** per sub-category hit in its title or
  from its first contribution sentence onward (the *solution window*). If no Fig-5 sub-category
  is hit inside the window, the window becomes the whole abstract. The Fig-11 sub-issues use the
  same window, so a sub-issue named only in the problem statement is never a solution on its own.
- **Virtualization fold.** The five Fig-11 sub-issues are tagged separately and folded into the
  Fig-5 rows as the paper did (`paper-content.md` §5):
  - hypervisor vulnerabilities → *Hypervisor vulnerabilities*;
  - isolation, cross-VM attacks, data leakage, VM identification → *Isolation*.

  Fig-11 counts are (abstract, sub-issue) entries, counted the same way.
- **Shares:** category share = category entries ÷ all entries of that kind (concern or solution),
  per era. Gap = solution share − concern share, in percentage points.

## 4. Validation (blind human labels)

**Sample.** Drawn after the freeze, from analysed works outside both dev sets, with seed 11.
100 items, stratified per era by classifier output:

| Stratum | 2013–17 | 2018–22 | 2023–26 |
|---|---|---|---|
| A: in scope, virtualization tagged | 9 | 9 | 9 |
| B: in scope, no virtualization | 19 | 18 | 18 |
| C: failed the relevance gate | 6 | 6 | 6 |

Inverse-probability weights N_h / n_h correct for the stratification. 10 items are shown twice
under new ids (110 screens) to measure self-agreement.

**Annotator.** One annotator, the project author, labels in a local form. The form shows only
the title and abstract: no year, venue, id, stratum or classifier output. Order is shuffled
(seed 11). The annotator does not read `lexicon.py`, `classify.py` or `replication/samples/`
before finishing (honour system; listed as a limitation).

**Annotation guidelines** (shown in the form):

1. Judge only the title and abstract. Do not look the paper up.
2. **Off topic** if the work is not about the security, privacy or compliance of cloud computing.
   Edge or fog computing that uses a cloud counts.
3. **Proposes a solution** if the authors present their own scheme, system, framework, protocol,
   method, tool, architecture or policy that addresses a security, privacy or compliance problem,
   including detection and mitigation. Surveys, reviews, attack papers without a countermeasure,
   measurement studies and position papers are **concern only**.
4. **Per category:**
   - **Concern** when the abstract raises a specific problem in that category. A generic
     "security and privacy" phrase does not count.
   - **Solution** when the proposed contribution addresses it (Solution implies Concern).

   Categories, with their sub-categories from the paper:
   - Network security: transfer, firewalling/IDS/DoS, security configuration
   - Interfaces: API, administrative interface, user interface, authentication/access control
   - Data security: cryptography/confidentiality, redundancy/integrity/backup, disposal/deletion
   - Virtualization: see 5
   - Governance: data control, security control/risk management, lock-in/portability
   - Compliance: SLA, loss of service/availability, audit/accountability, service conformity/
     certification
   - Legal issues: data location/jurisdiction, e-discovery/forensics, provider privilege/
     insiders, legislation/regulation
5. **Virtualization sub-issues:**
   - hypervisor vulnerabilities: flaws in the hypervisor, VMM, container runtime or shared kernel
   - isolation: separation between VMs/tenants/containers, escape, noisy neighbour, TEEs
   - cross-VM attacks: one tenant attacking a co-resident tenant, side channels, placement
   - data leakage: data crossing a VM/tenant boundary
   - VM identification: identifying, attributing or attesting workloads
6. When unsure, choose the less specific option and tick **unsure**.

**Metrics** (design-weighted; unweighted values reported alongside):
- Per category: precision, recall, F1 and binary Cohen's κ, separately for concern presence and
  solution presence.
- Macro- and micro-F1 over the 7 categories.
- Type κ and confusion matrix (off-topic items excluded and counted).
- Relevance gate precision/recall against the off-topic flag.
- Per-axis precision/recall for virtualization (small n; descriptive).
- Self-agreement κ from the 10 repeats.
- Dev-set metrics (labelled "tuning set, optimistic").
- 95% CIs: stratified bootstrap, B = 2000, seed 2012.

## 5. Analysis

- **Category shares per era.** Concern %, solution % and gap, with 95% CIs from a cluster
  bootstrap over abstracts (B = 2000, seed 2012).
  - The pooled 2013–2026 estimate weights eras by their OpenAlex population.
  - The 2012 values are the exact Figs 6/8 numbers.
- **Sub-categories:** a Fig 5/7 analogue (23 sub-categories) per era.
- **Fig 11 analogue** per era and pooled: concern and solution entries per sub-issue, and the
  solution/concern ratio with CI. The ratio is what is compared with 2012, because Fig 11's
  absolute scale is unknown.

**Hypotheses.** G_v(e) is the virtualization gap in era e (rule B), with its 95% CI. Verdicts are
computed by `rep publish`.

| Id | Statement | Supported | Not supported | Otherwise |
|---|---|---|---|---|
| HR1 | The gap persists: G_v(2023–26) < 0 | CI upper bound < 0 | CI lower bound ≥ 0 | inconclusive |
| HR2 | It is narrower than in 2012: G_v(2023–26) > −9 | CI lower bound > −9 | CI upper bound < −9 | inconclusive |
| HR3 | Virtualization is still the most negative category in 2023–26 | in ≥ 90% of bootstrap replicates | in ≤ 10% | inconclusive |
| HR4 | Isolation + cross-VM are the least answered: pooled solution/concern ratio r(isolation + cross-VM) − r(hypervisor + data leakage + VM identification) < 0 (2012: 0.10 vs 0.29) | CI upper bound < 0 | CI lower bound > 0 | inconclusive |
| HR5 | Validity gate: macro-F1 (concern) ≥ 0.70, virtualization F1 (concern) ≥ 0.70, mean κ (concern, 7 categories) ≥ 0.60, type κ ≥ 0.60, all point estimates | all four met | any missed | n/a |

- **Method bridge for HR2.** G_v(2013–17) is reported next to HR2. If it differs from −9 by more
  than 5 points, the HR2 detail adds that the 2012 comparison is dominated by method differences.
- **If HR5 fails,** HR1–HR4 are still published, prefixed "Classifier validity gate not met", and
  the site shows a warning.

**Robustness checks** (virtualization gap per era):

| Id | Variation |
|---|---|
| RB1 | count per (abstract, category) instead of per sub-category |
| RB2 | broadcast solutions to every hit (rule A) instead of the scoped rule B |
| RB3 | "classic" virtualization only: no container, serverless or TEE terms |
| RB4 | peer-reviewed types only (article, conference-paper, review) |

## 6. CVE supplement (descriptive, no hypothesis)

**Source:** NVD CVE API 2.0 (public domain), rejected CVEs excluded. Snapshot committed under
`replication/nvd/`.

**Candidate queries:**
- product keywords: hypervisor, hypervisors, Xen, KVM, QEMU, ESXi, Hyper-V, VirtualBox, bhyve,
  Firecracker, runc, containerd, CRI-O, LXC, gVisor, Kata Containers, Docker;
- exact phrases: virtual machine escape, VM escape, guest-to-host, container escape, guest OS,
  guest kernel, side channel, side-channel, speculative execution, transient execution,
  cross-tenant, co-resident, another guest.

**Normalisation.** Yearly NVD totals come from quarterly publication windows. Each axis is
reported as CVEs per 10,000 published CVEs, 2008–2026 (2026 partial).

**Axes,** classified from the English description; a virtualization context is required, and
"JVM", "memory leak" and "guest user/account/network" are masked. The context is
virtualization-specific (hypervisor, virtual machine, VM, guest, a hypervisor or container-runtime
product, container escape/isolation/runtime, enclave/SGX/TDX/SEV); plain "host", "container" and
"tenant" do not count, because they match application CVEs (web hosts, servlet containers,
multi-tenant SaaS authorisation bugs):

| Axis | Matches |
|---|---|
| virtualization layer | a hypervisor, VMM or container runtime/engine is the affected component |
| isolation | escape, breakout, guest-to-host, code execution on the host |
| cross-VM attacks | side channel, speculative/transient execution, another guest or tenant |
| data leakage | information disclosure, reading host/guest/uninitialised memory |
| VM identification | no defensible proxy; reported as not measured |

**Spot check:** 20 random CVEs per axis, labelled by the implementer after the freeze and reported
as indicative precision.

## 7. Reporting

`results/published/replication.json` (schema `experiments.schema.json`, `kind: "replication"`)
holds:
- the protocol and its hashes;
- the corpus flow table;
- category and sub-category shares;
- Fig 11 rows;
- validation metrics;
- robustness checks;
- the CVE series;
- HR1–HR5 verdicts.

Rebuilt abstracts are never published. The site's Results → Replication view and the research
paper report all of it, including the limitations in §1.

## Changelog

All entries before the freeze come from the dev sets only; the test sample had not been drawn.

- **2026-10-14 — virtualization dev supplement (§3, §4).** The random dev set (150) held only 3
  virtualization abstracts, too few to check the rules every hypothesis depends on. Added a
  supplement of 30 works the pre-freeze classifier tagged as virtualization (10 per era, seed
  `devvirt-7-<era>`, dev items excluded), labelled by the implementer blind to the per-item
  output. Stored as `replication/samples/dev-virt.json` and `replication/labels/dev-virt.json`;
  excluded from the test draw. Because it is selected on classifier output, only its
  precision-type readings are reported.
- **2026-10-14 — dev tuning of the rules (§3).** Changes made after reading the dev
  disagreements, before the freeze:
  - Relevance gate: added condition 3 (one sentence names both a cloud and a security term).
    On dev it removed 6 off-topic works and lost 1 on-topic one.
  - Type: present-tense passive contributions; whole-word proposing verbs ("implementation" is
    not "implement", "provider" is not "provide"); others' work and claims masked; "process" and
    "structure" added as artifacts; "vulnerability" removed from the attack cues (risk-analysis
    tools are defensive); survey title cues "an introduction", "introduction to", "current/key
    challenges", "a primer" added; "state of the art" dropped from the survey lead cues.
  - Sentence splitting also splits "end.Next" (abstracts that lost the space after a full stop).
  - Solution window decided once and shared by the Fig-11 sub-issues (see Counting).
  - Hypervisor sub-issue needs a threat word (see Threat context); generic side channels need a
    virtualization context; "pod" dropped from the virtualization context (scheme names such as
    POD matched it); co-location added; "VM hopping", "malicious tenant/VM", "co-tenant" added to
    cross-VM.
  - Terms removed as generic on dev: data owner (Data control), transparency (Audit), high
    availability and resilience (Loss of service), bare "governance" and "security requirement"
    (Security control).
  - Terms added: untrusted/malicious/dishonest server or provider (Provider privilege); "no/limited
    control over" (Data control); security risk, threat model/assessment, cloud/IT governance
    (Security control); threat detection (Firewalling).
  - CVE supplement (§6): the virtualization context dropped plain "host", "container", "Docker"
    and "tenant" after a look at random candidate hits (application CVEs matched them).
  - Dev metrics after tuning (optimistic, tuning sets): random dev macro-F1 0.74, mean κ 0.69,
    type κ 0.63; virtualization supplement category precision 0.96.
- **Freeze — 2026-10-13T18:57Z.** `lexicon.py` sha256 `4dc7168d…`, `classify.py` sha256
  `1329f6f2…` (full hashes and the hashes of the dev inputs in `replication/freeze.json`). From here
  on the rules are fixed; any change is a deviation and is reported as one.
