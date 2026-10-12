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
