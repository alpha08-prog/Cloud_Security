# Viva notes

## The one-sentence pitch
The paper found that virtualization isolation is the cloud-security problem with the fewest
solutions, and its future-work section lists four things a solution must do. I built that
solution on a small multi-tenant testbed and measured that it works.

## 5-minute demo script
Before the demo:

```bash
python scripts/lab.py up hardened
```

Open the site (`npm run preview`, or GitHub Pages) and Grafana at http://127.0.0.1:3000.

1. **The gap** tab (30 s). The −9 pt hero, then Figure 11: isolation and cross-VM attacks have
   almost no solutions. Read the p.16 brief aloud; it names R1–R4.
2. **Requirements** (45 s). One card per requirement: the paper's phrase, what it became in
   code, and the measured evidence. Point at the traceability table.
3. **The system** (60 s). The architecture diagram: three tenants on their own cores, the
   provider plane, the read-only socket proxy. Open one check in the catalogue (e.g.
   `XVM-05`) to show it is traced to the paper's taxonomy and to CSA/ENISA/NIST.
4. **Live** (90 s), in a terminal next to Grafana:
   ```bash
   python scripts/lab.py audit hardened   # gate passes; hypervisor axis lowest (waived host issues)
   python scripts/lab.py demo canary      # DET-06 + DET-01 + DET-07, attributed to tenant c, ~100 ms
   python scripts/lab.py demo noisy       # hardened: the job is throttled, DET-08 silent
   ```
   Optional, if there's time: `lab.py up insecure`, then `lab.py audit insecure` (gate fails
   with 15 blocking findings) and `lab.py demo noisy` (DET-08 fires in ~40 s).
5. **Results** (60 s). Figure 11 revisited (two panels, different units). Noisy neighbour:
   p99 ×3 insecure vs ×1.1 hardened. Segmentation: 12/12 paths open vs 0/12. Detection: every
   trigger caught, 0 false positives. Hypotheses: pre-registered, verdicts computed.

## Questions to expect

**"Containers aren't VMs. Does this answer the paper?"**
The paper's own source, the CSA guidance (p.12), says multi-tenancy, not virtualization, is
the essential cloud characteristic, and that segmentation and isolation are needed either way.
Containers share one kernel, which makes them the harder case. The same five sub-issues
(Figure 11) apply; the "hypervisor" axis becomes the engine plus the shared kernel.

**"Why is the hypervisor axis still low when hardened?"**
Two host-level issues no tenant can fix:
- the WSL2 kernel reports SRSO as "Vulnerable: no microcode", because microcode comes from the
  physical host's firmware;
- Docker Desktop offers no user namespaces.

Both are waived with a reason and an expiry, and waived checks earn no credit. That is the
paper's transparency point: tenants depend on a provider layer they can't inspect or fix.

**"How do you know the checks aren't just passing?"**
Four things guard against that:
- The insecure profile is a negative control: CI fails if ISO-01, HV-01, XVM-01 or ID-01 stop
  failing there, or if any axis has no failing check.
- 63 unit tests run every check against real snapshots of both profiles.
- E2 checks reality rather than configuration (12 live probes), with three positive controls
  so "blocked" can't mean "network broken".
- Scores are recomputed in TypeScript and must match the Python exactly.

**"Isn't the noisy-neighbour experiment just a benchmark?"**
It's an SLO test of performance isolation, an availability concern the paper files under
SLA / loss of service. It uses an open-model load (no coordinated omission) and puts the load
generator on its own physical core at maximum CPU weight in every arm. A run is invalid if any
iteration was dropped, more than 1% of requests failed, or the noise didn't actually happen.

**"Why did you change DET-08?"**
The first version keyed on the victim's CPU pressure (PSI). The smoke runs showed that a lightly
loaded victim's PSI stays around 1% with or without a noisy neighbour, while its p99 triples.
So the signal was too weak. The rule now flags the aggressor: a tenant using more than its fair
share of CPUs it actually shares with an active tenant. The change is logged, with the reason,
in `docs/experiments.md` before the full run.

**"What would you need for real VMs?"**
The same auditor model with a libvirt/KVM snapshot source instead of the Docker API, plus
features this testbed can't reach:
- cache partitioning (Intel RDT via resctrl)
- dedicated hosts
- SMT disabled per host

The design keeps checks as pure functions of a snapshot, so a new snapshot source plugs in.

**"Did you attack anything?"**
No. The boundary is written down in `CLAUDE.md` and `testbed/README.md`. Validation is
configuration auditing, load testing of the victim's own latency, read-only reachability
probes, and benign triggers shaped like isolation-breaking actions. There is no
cache/timing measurement, no exploit code, and no secret recovery anywhere.

## Numbers to remember
They come from `results/published/` (the latest full run), and the Results tab shows them live:
- coverage: 94% hardened vs 20% insecure
- the gate fails insecure with 15 blocking findings
- E2: 0/12 paths open hardened vs 12/12 insecure
- E1: p99 slowdown ×1.1 hardened vs ×3.0 insecure in the published smoke run (20 req/s, 30 s).
  An interrupted full-length run (50 req/s, 90 s) measured insecure p99 12.6 → 17.9 ms (×1.4) on
  its first repetition: the effect is still there, but smaller, because the baseline tail is
  already higher at 50 req/s. If the full run confirms it, H1 (≥ ×2) will be "not supported", and
  that is a result worth reporting, not hiding.
- E3: every trigger detected in both profiles, 0 false positives, median detection ~0.1–0.3 s,
  DET-08 at ~40 s by design (30 s sustain)
