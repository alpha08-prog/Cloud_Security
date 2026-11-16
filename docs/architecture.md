# IsoLab architecture

IsoLab implements the four requirements Gonzalez et al. (2012, p.16) set for the missing
virtualization-security solution (see `paper-content.md` §8). It does so on a small
multi-tenant "cloud" that runs on one container host.

## Components

```
container host (Docker Desktop VM / CI runner): one kernel + one engine = the "hypervisor"
├─ tenant plane (changed by the profile overlay)
│   tenant-a  payments-api      CPU-sensitive HTTP service; the E1 victim
│   tenant-b  batch-analytics   + tenant-b-job (stress-ng, CPU only): the E1 noisy neighbour
│   tenant-c  legacy-app        idle; the vantage point for E2's probes
└─ provider plane (identical in both profiles, itself hardened)
    socket-proxy   the only holder of docker.sock; read-only API subset, POST disabled
    auditor        cloudaudit: static checks, cgroup/PSI exporter, engine-event detections,
                   canary webhook, HTTP API (:8088), Prometheus exporter
    canary         decoy "metadata" service; any non-loopback request is a detection
    prometheus     scrapes the auditor; alert rules mirror the detections
    grafana        provisioned dashboard (:3000, anonymous viewer)
scripts/lab.py (host, standard library only): doctor, cpus, up/down, audit, gate, demo, e1-e3,
               run-all, publish, test, contract
```

## How the requirements map onto it

| Req | Paper phrase | Mechanisms | Verified by |
|---|---|---|---|
| R1 | "virtual machine identification" | Identity labels on containers, networks and volumes; digest-pinned images with provenance labels; detection of unattributed workloads; canary hits traced to a tenant by source IP | ID-01…05, DET-05, DET-07, E3 attribution |
| R2 | "adequate separation of dedicated resources" | Physical-core CPU sets from the real topology; CPU quota; memory = swap limit; PID limit; one internal network and one volume per tenant; uid 10001, no capabilities, no-new-privileges, seccomp, read-only root | ISO-*, DL-01…04, XVM-01…06, E1, E2 |
| R3 | "constant observation of shared ones" | cgroup v2 counters + PSI every 5 s per workload, exported to Prometheus; fair-share noisy-neighbour rule (DET-08); host posture (CPU-flaw mitigations, kernel hardening, engine patch level) | HV-02/03/06, ID-05, DET-08, E1, E3 |
| R4 | "examine any attempt of exploiting cross-VM and data leakage" | Engine-event watcher (privileged starts, engine-socket mounts, host-namespace joins, cross-tenant attaches, execs); canary; tripwire self-check | DET-01…07, XVM-07, DL-05, E3 |

## Data flow and contracts

1. `cloudaudit` takes one **snapshot**: engine info, running containers, networks, volumes and
   images through the proxy, plus host facts from `/sys` and `/proc`.
2. The 30 checks are pure functions of that snapshot. Waivers are applied, then scores and the
   gate are computed (`scoring.py`).
3. The output is an `AuditReport` (pydantic). `cloudaudit schema` writes it to
   `schemas/audit-report.schema.json`, along with `detection.schema.json` and
   `experiments.schema.json`.
4. `lab.py publish` merges both profiles' runs into `results/published/`, evaluates the
   pre-registered hypotheses, and validates every file against the schemas.
5. The web app imports `results/published/*.json` at build time. `src/data/results.test.ts`
   checks four things:
   - every file validates against the schemas (ajv);
   - every taxonomy and framework reference resolves;
   - every score recomputed in TypeScript equals the Python one;
   - the results support the claims made on the page.

## Scoring

```
coverage = Σ weight(severity) × credit(status) / Σ weight(severity)
weights: critical 4 · high 3 · medium 2 · low 1
credit:  pass 1 · warn 0.5 · fail/error 0 · waived 0 · skip excluded
```

Coverage is computed per Figure 11 axis, per requirement and overall. The unweighted pass rate
is published alongside it. The Results tab shows Figure 11 and our coverage radar as two panels
with a "different units" caption, never on one shared scale.

## Design decisions worth defending

- **Containers stand in for VMs.** The CSA guidance quoted in the paper (p.12) names
  multi-tenancy as the essential characteristic, and segmentation and isolation are required
  either way. A shared kernel is the harder case.
- **The auditor never holds the engine socket.** It uses a read-only proxy on an internal
  network. The provider plane is held to its own policy, and its two exceptions are
  documented in `policy.yaml`.
- **DET-08 flags the aggressor, not the victim's pressure.** Measured on the testbed, a lightly
  loaded victim's PSI stays around 1% with or without contention while its p99 latency triples
  (see the changelog in `experiments.md`).
- **Waivers earn no coverage.** An accepted host limitation is visible, time-boxed and
  attributed, and it lowers the score instead of hiding.
- **Every timing is on the VM's own clock.** Detection latency is engine event time to
  detection time, so clock skew between Windows and the VM cannot distort it.

## The replication pipeline

A second, independent study re-applies the survey's own method to newer literature
(`docs/replication.md`). It shares the result contract and the site, nothing else.

```
rep fetch / cve-fetch   OpenAlex seeded samples, NVD candidates + quarterly totals
        │               -> replication/{corpus,nvd}/*.jsonl.gz (sha256 over the uncompressed bytes)
corpus.py               rebuild abstracts, filter (50-600 words, stubs), dedupe -> flow table
classify.py + lexicon.py  relevance gate, type (survey / solution / concern), 23 Fig-5 sub-categories,
        │               5 Fig-11 sub-issues folded into Fig 5's two virtualization rows, solution window
rep freeze              sha256 of lexicon.py + classify.py -> replication/freeze.json (every later step checks it)
rep sample              100 stratified items + 10 hidden repeats, drawn after the freeze
rep annotate            ThreadingHTTPServer on 127.0.0.1: token + Host check, one screen at a time,
        │               atomic save -> replication/labels/test.json
validate.py             design-weighted P/R/F1/kappa vs the labels, stratified bootstrap, HR5 gate
analysis.py             per-era and pooled shares, cluster bootstrap over abstracts (one resample
        │               drives the main rule and RB1-RB4), Fig 5/7/11 analogues, HR1-HR4
cve.py                  CVE axes per year per 10k published CVEs (+ deviation D1)
rep publish             -> results/published/replication.json, validated against experiments.schema.json
```

Design decisions:
- **Counting unit as in the paper.** One entry per (abstract, sub-category), shares of all
  entries, gap = solution share − concern share. The fold of Figure 11 into Figure 5
  (Isolation 7 + Hypervisor 5 = 12) is reproduced, not reinvented.
- **Rules, not a model.** Every decision traces to a term in `lexicon.py` and a line in
  `classify.py`, so a reviewer can audit and re-run it, and the freeze hash means exactly
  those rules produced the numbers.
- **Precision is bought with context.** Hypervisor mentions count only next to a threat word,
  generic side channels only next to a VM word, and a relevance gate needs a sentence that
  names both the cloud and security.
- **Validated where it matters.** The validation sample over-weights virtualization
  (stratum A) because every hypothesis depends on it. Inverse-probability weights restore
  corpus-level estimates.
# November 2026 research extension

The current research entry point is [the two-paper implementation and demo](research/DEMO.md).
The original R1–R4 architecture above retains its Gonzalez 2012 provenance. A new hardened
startup launcher verifies SHA-256 allowlists for the interpreter, application, probe and launcher;
the batch image also verifies stress-ng. The image builder creates manifests before dropping
to user 10001. The hardened Compose overlay enables enforcement for all tenants and the noisy
batch job. Invalid startup files cause exit 78. This implements a selected startup aspect of
ACM 2025 mitigation M2, with a trusted builder/manifest/engine and no continuous attestation.

`cloudaudit research` runs E4 snapshot faults and E5 isolated subprocess challenges. The
`lab.py research` wrapper uses the dev container, while `lab.py integrity` checks clean and
altered-file cases in the three built tenant images. Generated research evidence is separate
from the historical E1–E3 publisher contract. The frontend's Research tab uses this evidence.
