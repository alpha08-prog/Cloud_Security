# IsoLab experiments: protocol and pre-registered hypotheses

This file was written **before** any experiment was run. Hypotheses, metrics and pass
criteria are fixed here so the results can't be tuned to fit afterwards. Any later change
to this file must be logged in the changelog at the bottom with a reason.

All three experiments run on the same testbed in two profiles:

- **insecure**: a deliberately weak baseline, typical of a quick "lift-and-shift" deployment
- **hardened**: the paper-derived controls (R1–R4, see `paper-content.md` §8)

Each profile is run on two platforms. Results are always reported per platform and never
pooled across them.

- `docker-desktop-wsl2`: the author's laptop, used for the full variant
- `github-ubuntu`: the CI runner, used for the smoke variant

Safety boundary: every experiment is defensive. Nothing here measures another tenant's
timing or cache behaviour, recovers secrets, or exploits anything.

---

## E1: Noisy neighbour (performance isolation, R2 + R3)

**Question.** If one tenant saturates the CPU, does another tenant's service on the same host
keep its latency SLO?

**Setup**

- **Victim:** tenant-a `payments-api`, endpoint `/work`. It runs a fixed CPU loop calibrated
  once to about 2 ms on the laptop; the iteration count is recorded in `testbed/policy.yaml`.
  The response carries `Server-Timing: work;dur=<ms>`, so server compute time is reported
  separately from queueing.
- **Noise:** the `tenant-b-job` container runs `stress-ng --cpu <N> --cpu-method matrixprod`.
  It is CPU only: no memory stressor, so it can't push the VM out of memory. The job spec is
  identical in every arm; only the platform's enforcement changes.
- **Load:** k6 with the `constant-arrival-rate` executor (an open model, which avoids
  coordinated omission). k6 is pinned to its own physical core with maximum CPU weight in
  every arm.

**Arms:** {insecure, hardened} × {baseline, noisy}. An optional fifth arm, hardened with
tenant-a and tenant-b on SMT siblings of the same physical core, is indicative only, because
Hyper-V maps vCPUs freely.

| Parameter | Full (laptop) | CI smoke |
|---|---|---|
| Arrival rate | 50 req/s | 20 req/s |
| Warm-up (discarded) | 15 s | 5 s |
| Measurement window | 90 s | 30 s |
| Repetitions | 3, arms interleaved | 1 |
| Cool-down between arms | 30 s | 5 s |

**Metrics**

- `http_req_duration` p50, p90, p95, p99 and max
- request failure rate
- `dropped_iterations`
- server `work` time p50 and p99
- per tenant, from the auditor's exporter: CPU cores used, CPU throttled seconds, and CPU
  pressure (PSI `some`)

**Derived metrics and validity**

- **Interference factor** IF = p99(noisy) / p99(baseline), taking the median across
  repetitions.
- **SLO:** p99 ≤ 25 ms at the full-variant rate. It may be adjusted once, after calibration
  and before the first measured run, with the change logged below.
- **A run is invalid,** and is repeated, if `dropped_iterations > 0`, if failures exceed 1%,
  or if tenant-b used less than 1 core during a noisy window (meaning the noise didn't
  happen).

**Hypotheses**

- **H1:** insecure IF ≥ 2.
- **H2:** hardened IF ≤ 1.25, and hardened keeps the SLO with noise.
- **H3:** (optional SMT arm) server-side p50 in the SMT-shared arm is higher than in
  hardened. This is indicative only.
- **H4:** the noisy-neighbour detection (DET-08) fires during insecure-noisy and stays silent
  during hardened-noisy.

E1 never gates CI on latency. CI only checks that the pipeline runs and that the noise was
real.

---

## E2: Segmentation and escape-surface matrix (R2)

**Question.** From inside a tenant, which isolation boundaries are actually open?

**Method.** One `docker exec` per tenant runs a stdlib-only probe script that prints JSON.
Each probe is read-only or a TCP connect, with a 2 s timeout. Each outcome is `allowed`,
`blocked` or `error`.

**Positive controls** (must be `allowed` in both profiles, proving "blocked" isn't just "the
network is broken"):

| Id | Probe |
|---|---|
| C1 | load generator → tenant-a `/healthz` |
| C2 | Prometheus → auditor `/healthz` |
| C3 | tenant-c → its own loopback listener |

**Probes** (P3 depends on the platform; all others are `allowed` in insecure):

| Id | Probe | Hardened expected |
|---|---|---|
| P1 | tenant-c → tenant-a by DNS name | blocked |
| P2 | tenant-c → tenant-a by IP | blocked |
| P3 | tenant-c → host gateway (`host.docker.internal`) | blocked |
| P4 | tenant-c → canary `metadata` | blocked |
| P5 | tenant-c → Prometheus API | blocked |
| P6 | tenant-c → internet egress (TCP connect only) | blocked |
| P7 | tenant-c sees tenant-a's processes | blocked |
| P8 | engine socket present and answers `_ping` | blocked |
| P9 | host files visible (`/host-etc/os-release`) | blocked |
| P10 | tenant-a's marker file readable (a non-secret marker) | blocked |
| P11 | non-zero effective capabilities (`CapEff`) | blocked |
| P12 | tenant-b → tenant-a | blocked |

**Hypotheses**

- **H5:** insecure has ≥ 10 of 12 open paths.
- **H6:** hardened has 0 of 12 open paths with all controls passing. This one gates CI.

---

## E3: Detection validation (R1 + R4)

**Question.** Does the platform notice isolation-breaking actions quickly and attribute them to
the right tenant, without false alarms?

**Method**

1. A quiet window under normal load (120 s full, 30 s CI). It must produce 0 detections.
2. Then benign triggers. Each one is a harmless command that has the *shape* of an
   isolation-breaking action, the same idea as Falco's event-generator.

| Id | Trigger | Expected rule | Latency SLO |
|---|---|---|---|
| T1 | `docker exec tenant-a true` | DET-01 TenantExec | ≤ 5 s |
| T2 | short-lived `--privileged` container running `true` | DET-02 PrivilegedStart | ≤ 5 s |
| T3 | short-lived container with the engine socket mounted, running `true` | DET-03 EngineSocketMount | ≤ 5 s |
| T4 | unlabelled container running `sleep 5` | DET-05 UnattributedWorkload | ≤ 5 s |
| T5 | `docker network connect` tenant-c onto the provider network | DET-06 CrossTenantAttach | ≤ 5 s |
| T6 | tenant-c sends one HTTP request to the canary, then is disconnected | DET-07 CanaryHit, attributed to tenant-c | ≤ 5 s |
| T7 | noisy job (reused from E1) | DET-08 NoisyNeighbour, insecure only | ≤ 90 s |
| T8 | short-lived `--pid host` container running `true` | DET-04 HostNamespaceJoin | ≤ 5 s |

**Measurement.** Every latency is computed from VM-side timestamps: the Docker event
`timeNano` or canary hit time, to the detection time. That makes it immune to clock skew
between Windows and the VM.

**Metrics:** detection rate, latency compared with the SLO, false positives in the quiet
window, and attribution correctness (detected tenant = expected tenant).

**Hypothesis**

- **H7:** detection rate is 100% with 0 false positives, and every latency is within its SLO.
  This gates CI for hardened.

---

## Changelog

- **2026-10-12: calibration, before any measured run.** The `/work` loop was set to 2500
  SHA-256 rounds, which measured about 2 ms of server time (6000 rounds measured 4.7 ms).
- **2026-10-12: DET-08 definition changed after the E1 smoke runs.**
  - The first definition flagged a noisy neighbour when the victim's CPU pressure (PSI) was
    above 10% while another tenant used more than 1.5 cores.
  - The smoke runs showed that a lightly loaded victim's PSI stays around 1% with or without
    a noisy neighbour: about 1.2% insecure vs 1.0% hardened under noise at 50 req/s. Its p99
    latency, meanwhile, tripled in the insecure profile. A victim-side PSI threshold would
    therefore be driven by noise.
  - DET-08 now flags the aggressor: a tenant that, for 30 s, uses more than
    max(1.5, host CPUs ÷ active tenants) cores on CPUs it shares with at least one other
    active tenant. The victims' PSI is still reported as evidence.
  - H4 is unchanged: DET-08 fires in insecure-noisy and is silent in hardened-noisy.
