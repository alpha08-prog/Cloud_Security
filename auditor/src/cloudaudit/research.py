"""Selected survey defenses as executable configuration evidence, not CVE coverage.

E4 mutates independent copies of a saved snapshot. It never starts a vulnerable
container, changes the host, or treats the old E1--E3 measurements as new runs.
"""
from __future__ import annotations

import hashlib
import json
import runpy
from datetime import UTC, datetime
from pathlib import Path

from .engine import run_checks
from .models import AuditReport
from .policy import Policy, load_policy
from .snapshot import Snapshot, service

ACM_DOI = "https://doi.org/10.1145/3715001"
QOS_DOI = "https://doi.org/10.1016/j.jnca.2024.103839"

# Our engineering associations are not additional mappings claimed by Table 3.
# In particular, E30 describes the filesystem attack surface, whereas M1 and M3
# have their own exploit associations in the source survey.
THEMES = [
    {"id": "mounts", "title": "Restrict sensitive host mounts",
     "source": "M1 (selected host-volume aspect); E30 context",
     "checks": ["DL-01", "HV-01"], "boundary": "E2 host and engine-access probes", "runtime": "DET-03"},
    {"id": "immutability", "title": "Read-only container root filesystems", "source": "M3",
     "checks": ["DL-04"], "boundary": "Configuration evidence only", "runtime": "Not directly observed"},
    {"id": "privilege", "title": "Least privilege and non-root execution", "source": "E18, E32 (defensive association)",
     "checks": ["ISO-01", "ISO-02", "ISO-04"], "boundary": "Configuration evidence only", "runtime": "DET-02"},
    {"id": "process", "title": "Private process namespaces", "source": "A6.1, E23 (defensive association)",
     "checks": ["ISO-05"], "boundary": "E2 process-visibility probe", "runtime": "DET-04"},
    {"id": "syscalls", "title": "Seccomp and no-new-privileges", "source": "A7 (attack-surface reduction)",
     "checks": ["ISO-03"], "boundary": "Configuration evidence only", "runtime": "No syscall-level detector"},
    {"id": "resources", "title": "Resource limits and dedicated allocations", "source": "E34 (defensive association)",
     "checks": ["ISO-06", "ISO-07"], "boundary": "E1 CPU-contention experiment", "runtime": "DET-08"},
]

# id, theme, expected check, mutation. All target the same workload independently.
FAULTS = [
    ("F01", "privilege", "ISO-01", "privileged"),
    ("F02", "privilege", "ISO-02", "capabilities"),
    ("F03", "syscalls", "ISO-03", "seccomp"),
    ("F04", "privilege", "ISO-04", "root"),
    ("F05", "process", "ISO-05", "host-pid"),
    ("F06", "resources", "ISO-06", "unlimited-cpu"),
    ("F07", "immutability", "DL-04", "writable-root"),
    ("F08", "mounts", "DL-01", "host-bind"),
    ("F09", "mounts", "HV-01", "engine-socket"),
    ("F10", "resources", "ISO-07", "unplaced-cpu"),
]


def mutate(snap: Snapshot, mutation: str) -> None:
    matches = [c for c in snap.containers if service(c) == "tenant-a"]
    if len(matches) != 1:
        raise ValueError("E4 requires exactly one tenant-a workload")
    c = matches[0]
    hc = c["HostConfig"]
    if mutation == "privileged":
        hc["Privileged"] = True
    elif mutation == "capabilities":
        hc["CapDrop"] = []
    elif mutation == "seccomp":
        hc["SecurityOpt"] = [o for o in hc.get("SecurityOpt", []) if not o.startswith("seccomp")]
        hc["SecurityOpt"].append("seccomp=unconfined")
    elif mutation == "root":
        c["Config"]["User"] = "0"
    elif mutation == "host-pid":
        hc["PidMode"] = "host"
    elif mutation == "unlimited-cpu":
        hc["NanoCpus"] = hc["CpuQuota"] = 0
    elif mutation == "writable-root":
        hc["ReadonlyRootfs"] = False
    elif mutation in ("host-bind", "engine-socket"):
        path = "/etc" if mutation == "host-bind" else "/var/run/docker.sock"
        c.setdefault("Mounts", []).append({"Type": "bind", "Source": path, "Destination": "/e4", "RW": True})
    elif mutation == "unplaced-cpu":
        hc["CpusetCpus"] = ""
    else:
        raise ValueError(f"Unknown E4 mutation: {mutation}")


def target_status(results, check_id: str) -> str:
    rows = [t.status for r in results if r.check_id == check_id for t in r.targets if t.ref == "tenant-a"]
    return rows[0] if len(rows) == 1 else "missing-or-ambiguous"


def fault_study(snap: Snapshot, policy: Policy) -> dict:
    baseline = run_checks(snap, policy, [])
    rows = []
    for fid, theme, check_id, mutation in FAULTS:
        altered = snap.model_copy(deep=True)
        mutate(altered, mutation)
        outcome = target_status(run_checks(altered, policy, []), check_id)
        before = target_status(baseline, check_id)
        rows.append({"id": fid, "theme": theme, "mutation": mutation, "check": check_id,
                     "baseline": before, "mutated": outcome, "detected": before == "pass" and outcome == "fail"})
    return {"kind": "snapshot-configuration-fault-injection", "target": "tenant-a", "cases": rows,
            "detected": sum(r["detected"] for r in rows), "total": len(rows),
            "passed": len(rows) == 10 and all(r["detected"] for r in rows),
            "claim": "Checker sensitivity to these ten configuration faults; no live exploit or CVE validation."}


def assess(report: AuditReport, checks: list[str]) -> dict:
    rows = []
    for cid in checks:
        matches = [r for r in report.results if r.check_id == cid]
        r = matches[0] if len(matches) == 1 else None
        verified = bool(r and r.status == "pass" and not r.waived and r.targets
                        and all(t.status == "pass" for t in r.targets))
        rows.append({"check": cid, "status": r.status if r else "missing-or-ambiguous",
                     "waived": bool(r and r.waived), "verified": verified,
                     "nonPassingTargets": [{"ref": t.ref, "status": t.status, "reason": t.message}
                                           for t in r.targets if t.status != "pass"] if r else []})
    return {"configurationVerified": bool(rows) and all(r["verified"] for r in rows), "evidence": rows}


def generate(repo: Path, snapshot: Path | None = None) -> dict:
    snapshot = snapshot or repo / "auditor/tests/fixtures/snapshots/hardened-desktop.json"
    paths = {"snapshot": snapshot, "policy": repo / "testbed/policy.yaml",
             "crosswalkCode": Path(__file__), "launcher": repo / "testbed/images/common/integrity.py",
             "integrityExperiment": repo / "scripts/integrity_study.py",
             "hardenedCompose": repo / "testbed/compose.hardened.yaml",
             **{p: repo / f"results/published/audit-{p}.json" for p in ("insecure", "hardened")}}
    reports = {p: AuditReport.model_validate_json(paths[p].read_bytes()) for p in ("insecure", "hardened")}
    integrity = runpy.run_path(str(repo / "scripts/integrity_study.py"))["study"](repo.resolve())
    return {"version": 1, "generatedAt": datetime.now(UTC).isoformat(),
            "sources": {"qos2024": QOS_DOI, "security2025": ACM_DOI},
            "inputs": {key: {"path": str(path.resolve().relative_to(repo.resolve())).replace("\\", "/"),
                               "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                       for key, path in paths.items()},
            "measurementBasis": "E1-E3: historical published live runs; E4: current saved-snapshot experiment.",
            "themes": [{**theme, "profiles": {p: assess(report, theme["checks"]) for p, report in reports.items()}}
                       for theme in THEMES],
            "e4": fault_study(Snapshot.model_validate_json(snapshot.read_bytes()), load_policy(paths["policy"])),
            "e5": integrity,
            "notImplemented": ["2024 autoencoder and recurrent-neural-network classifiers",
                               "2024 four-host Kubernetes/Spark replication", "Full 47-exploit ACM taxonomy validation",
                               "Symlink defense testing (M4), hardware attestation, eBPF defenses",
                               "Post-start continuous binary attestation"],
            "contribution": "Selected survey defenses linked to checks, startup integrity enforcement, "
                            "independent fault challenges, and separate reliability evidence."}


def write_study(repo: Path, out: Path, snapshot: Path | None = None) -> int:
    report = generate(repo, snapshot)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"E4 configuration faults detected: {report['e4']['detected']}/{report['e4']['total']}; report: {out}")
    print(f"E5 startup integrity challenges passed: {sum(r['passed'] for r in report['e5']['cases'])}/5")
    return 0 if report["e4"]["passed"] and report["e5"]["passed"] else 1
