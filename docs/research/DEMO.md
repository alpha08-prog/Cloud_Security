# Revised research implementation and demo

Authors: Atharva Agrawal (23bds010@iiitdwd.ac.in) and Niti Priya (23bcs087@iiitdwd.ac.in).

## What the recent papers contribute

| Source | IsoLab implementation | Limit |
| --- | --- | --- |
| Horchulhack et al., 2024, DOI 10.1016/j.jnca.2024.103839 | Provider-side resource observation, deterministic shared-CPU detection, contention/latency comparison | The autoencoder, RNN and distributed Spark/Kubernetes experiments are not reproduced |
| Jarkas et al., ACM 2025, DOI 10.1145/3715001 | Selected host-mount restriction (M1), startup hashing/allowlisting (M2), filesystem immutability (M3), and defensive associations with privilege, namespaces, syscall and resource attack surfaces | Not the complete mitigation catalog, exploit taxonomy or a CVE benchmark |
| IsoLab extension | Executable survey/check crosswalk; independent E4 mutations; startup enforcement and E5 counterexamples; evidence gates; combined security/reliability presentation | A scoped engineering contribution, without a claim to outperform either paper |

Gonzalez 2012 remains background for the original R1–R4 labels and five-axis grouping.

## Commands from PowerShell

```powershell
cd C:\Users\agraw\Cloud_Security
$Py = "C:\Users\agraw\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $Py scripts/lab.py doctor
& $Py scripts/lab.py up hardened
& $Py scripts/lab.py research
& $Py scripts/lab.py integrity
npm.cmd run dev
```

Open the Vite URL printed in the terminal; start with the Research tab. Grafana is at
http://127.0.0.1:3000 and the auditor at http://127.0.0.1:8088/report.

## Seven-minute presentation

1. **Research basis (one minute).** Explain that noisy neighbors affect reliability and shared kernels create security exposure. Identify the different roles of the two recent papers. Explain the implemented scope rather than claiming to reproduce every method.
2. **Architecture (one minute).** Show three tenant workloads, separate networks/volumes and CPU allocations, provider auditor, restricted socket proxy, PSI/resource monitoring and metadata canary. Labels identify workloads administratively.
3. **New defense (one minute).** Run `& $Py scripts/lab.py integrity`. It starts disposable, network-disabled containers. Each clean image passes; an altered application file is refused with exit 78. Show `results/research/container-integrity.json`. The command uses the launcher's check mode; E5 below separately verifies actual application execution/refusal with marker files.
4. **Research validation (one minute).** Run `& $Py scripts/lab.py research`. E4 must detect 10/10 configuration faults. Show one row: disabling seccomp changes ISO-03 from pass to fail. E5 must pass 5/5 decisions: one valid application runs and four invalid inputs are rejected. No running tenant is deliberately weakened.
5. **Measured results (one minute).** In Results, show the historical noisy-arm p99 medians, 16.463 versus 5.617 ms, and 12 closed paths with 3 passing controls. Both latency profiles satisfy 25 ms. These October runs predate the new November integrity launcher; they are not its performance evaluation.
6. **Live observation (one minute).** Use `& $Py scripts/lab.py demo --help` to select an existing benign trigger, then show its detection and attribution in Grafana/auditor. For a fresh full detection/boundary validation, run E3 before E2 as below.
7. **Contribution and limits (one minute).** Explain the connection from a survey defense to enforcement, an executable check and a counterexample test, with complementary reliability evidence. State that ML replication, continuous attestation, arbitrary-exec mediation, multi-host evaluation and broad exploit testing remain future work.

## Fresh verification and measurements

Keep smoke results separate from the historical published package:

```powershell
& $Py scripts/lab.py e3 hardened --variant ci --out results/runs/revision-demo
& $Py scripts/lab.py e2 hardened --variant ci --out results/runs/revision-demo
& $Py scripts/lab.py audit hardened --strict --out results/runs/revision-demo
& $Py scripts/lab.py test
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

For a complete new E1–E3 benchmark of both profiles, allow time for the full protocol:

```powershell
& $Py scripts/lab.py run-all --variant full --keep --out results/runs/new-study
```

That command switches profiles and replaces lab containers. Published measurements are updated only
through the validated publisher after reviewing a complete run. Do not manually edit published JSON.

## Enforcement boundary

SHA-256 manifests are generated inside each image from the interpreter, launch script, application,
probe script and (batch only) stress-ng executable. The hardened Compose overlay enables enforcement;
the insecure profile leaves it disabled. Python launch commands must name an allowlisted script;
inline `-c` and module `-m` execution through the launcher are rejected. Hashes are checked before
startup, then the launcher replaces itself with the application process. Other files, dynamic
libraries, commands started through another entrypoint or Docker exec, and post-start modification
are not continuously checked. The trusted builder, manifest, launcher and engine are prerequisites.

## Evidence provenance

`results/research/study.json` records input paths and SHA-256 hashes, six theme verdicts, E4 rows,
and E5 subprocess outcomes. `container-integrity.json` separately records image IDs and six real
container check outcomes. E4 is a snapshot sensitivity study; E5 is an isolated enforcement study.
Neither is a measure of attack prevalence, detection accuracy on an unseen dataset or coverage of
all ACM exploits. The separate blind literature-labeling extension is unfinished and excluded.

The November 11 hardened smoke run is summarized in `results/research/revision-smoke.json`:
E2 blocked 12/12 paths and allowed 3/3 controls; E3 detected 7/7 expected events with zero alerts
in the shortened 30-second quiet window; the audit gate passed with HV-03/HV-04 waived.
The summary retains per-probe/per-trigger outcomes and hashes of the original local run files.
To summarize a later run, use `python scripts/revision_smoke_summary.py results/runs/revision-demo`.
