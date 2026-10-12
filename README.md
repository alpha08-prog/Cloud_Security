# IsoLab: Cloud Isolation Lab

[![CI](https://github.com/alpha08-prog/Cloud_Security/actions/workflows/ci.yml/badge.svg)](https://github.com/alpha08-prog/Cloud_Security/actions/workflows/ci.yml)
**Live site: https://alpha08-prog.github.io/Cloud_Security/**

**Gonzalez et al. (2012)**, *A quantitative analysis of current security concerns and solutions
for cloud computing* (Journal of Cloud Computing 1:11), counted 200+ references and found one
area where solutions lag concerns: **virtualization**, with 12% of concern citations but 3% of
solution citations. Within it, isolation and cross-VM attacks are almost unanswered (Figure 11).
The paper's future-work section (p.16) says what the missing solution should do:

> "…employ **virtual machine identification** [R1], provide an **adequate separation of
> dedicated resources** [R2] combined with a **constant observation of shared ones** [R3], and
> **examine any attempt of exploiting cross-VM and data leakage** [R4]."

IsoLab builds that solution on a small multi-tenant cloud and measures it.

![The Results tab: Figure 11 revisited](docs/screenshots/results.png)

## What's in it

| Part | What it does |
|---|---|
| `testbed/` | A Docker Compose multi-tenant cloud: three tenants and a hardened provider plane, in two profiles (**insecure** lift-and-shift vs **hardened**, the paper-derived controls). CPU sets are planned from the host's real core/thread topology so no two tenants share a physical core. |
| `auditor/` | **cloudaudit** (Python, FastAPI, pydantic). It has: <ul><li>**30 checks**, each mapped to a Figure 11 axis, to R1–R4, to the paper's taxonomy nodes, and to CSA / ENISA / NIST</li><li>severity-weighted coverage scores, time-boxed waivers and a policy gate</li><li>JSON, SARIF and a console report</li><li>a per-tenant **cgroup v2 + pressure-stall (PSI)** exporter</li><li>**live detections** from the engine event stream</li><li>a **canary** decoy</li></ul> It only talks to the engine through a read-only socket proxy. |
| `monitor/` | Prometheus rules and a provisioned Grafana dashboard: the live view during a demo. |
| `scripts/lab.py` + `experiments/` | A standard-library orchestrator for the whole lab, and three pre-registered experiments: **E1** noisy neighbour (SLO under CPU contention), **E2** segmentation and escape-surface matrix, **E3** detection validation. |
| `src/` | The site, one tab per step: **The gap → Requirements → The system → Results**, plus the paper in an appendix. It imports the published results at build time. |
| `.github/workflows/ci.yml` | Lint and contract tests, then both profiles run on a fresh runner with their gates (the hardened gate blocks the deploy). Uploads SARIF to code scanning and deploys to Pages. |

## Results

From `results/published/`, measured on a 6-core/12-thread laptop (Docker Desktop, WSL2). The
Results tab shows them in full.

| | Insecure | Hardened |
|---|---|---|
| Policy gate (fail on ≥ high) | fails: 15 blocking checks | **passes** (2 waived host issues) |
| Isolation coverage, 30 checks | 20% | **94%** |
| E2: isolation paths open | 12 / 12 | **0 / 12** (controls 3/3) |
| E1: tenant A p99 alone → with a noisy neighbour | 4.3 → 16.5 ms (×3.8) | **4.6 → 5.6 ms (×1.22)** |
| E3: isolation-breaking actions detected | 8/8, 0 false positives | **7/7**, 0 false positives, median 95 ms |

Published run: full variant: E1 at 50 req/s, 15 s warm-up + 90 s measured, 3 interleaved repetitions per arm; E3 quiet window 120 s. Commit `dffa2c70c553`. Pre-registered hypotheses: 6 of 7 supported (H3 inconclusive: optional arm not run).

Hypotheses and pass criteria were written down before any run (`docs/experiments.md`); verdicts
are computed by `lab.py publish`.

## Run it

You need Docker Desktop (or Docker Engine with cgroup v2), Python 3.10 or newer (standard
library only), and Node 22.12+ for the site.

```bash
python scripts/lab.py doctor             # Docker, cgroup v2, ports, CPU topology
python scripts/lab.py up hardened         # or: up insecure (read testbed/README.md first)
python scripts/lab.py audit hardened      # 30 checks -> console + results/runs/.../audit.{json,sarif}
python scripts/lab.py demo canary         # one benign trigger, live (also: exec, drift, noisy, ...)
# Grafana: http://127.0.0.1:3000 (anonymous viewer)
python scripts/lab.py run-all             # both profiles: audit, E3, E2, E1, gates (~45 min)
python scripts/lab.py publish             # merge, test hypotheses, validate -> results/published
python scripts/lab.py down

python scripts/lab.py test                # ruff + pytest (auditor, orchestrator), in a container
npm install && npm test && npm run dev    # the site, at http://localhost:5173/
```

## How it's kept honest

- **Pre-registered experiments.** Protocol changes go in a changelog with a reason before the
  data they affect. Runs that break the validity rules are discarded: dropped iterations, more
  than 1% failures, or noise that didn't happen.
- **Controls in both directions.** The insecure profile is a negative control: CI fails if the
  auditor stops catching it. E2 includes positive controls, so "blocked" can't just mean
  "broken".
- **One contract, two languages.** The pydantic models generate JSON Schemas. The site validates
  every published file against them, resolves every taxonomy and framework reference, and
  recomputes every score in TypeScript, which must equal the Python result.
- **Waivers are visible.** Two host-level issues on Docker Desktop (CPU microcode, user
  namespaces) are waived with a reason and an expiry. They earn no coverage credit.
- **Defensive only.** Configuration auditing, load testing of the victim's own latency,
  read-only reachability probes and benign detection triggers. There is no attack code, no
  side-channel measurement and no secret recovery (see `CLAUDE.md` and `testbed/README.md`).

## Docs

- `docs/paper-content.md`: everything taken from the paper (figures, quotes, the p.16 brief).
- `docs/architecture.md`: components, the requirement mapping, the data contract, design
  decisions.
- `docs/experiments.md`: E1–E3 protocol, hypotheses and changelog.
- `docs/checks.md`: the generated check catalogue.
- `docs/viva-notes.md`: the demo script and expected questions.

## Limitations

- **Containers stand in for VMs.** The CSA guidance cited by the paper treats multi-tenancy as
  the essential characteristic, and a shared kernel is the harder isolation case.
- **One host.** On Docker Desktop the "host" is a Hyper-V VM, so SMT topology is indicative and
  microcode is out of reach.
- **Different units.** The paper's Figure 11 counts citations; IsoLab's radar is check coverage.
  The site never plots them on one scale.
- **CI E1 is a smoke test.** Two-core runners can't separate tenants onto physical cores
  (waived there), so CI latency numbers are informative only.

## Credit

Based on the open-access (CC BY 2.0) paper by Gonzalez, Miers, Redígolo, Simplício, Carvalho,
Näslund and Pourzandi (2012). Paper content is attributed in `docs/paper-content.md`; the
requirements' interpretation, the system and all measurements are this project's.
