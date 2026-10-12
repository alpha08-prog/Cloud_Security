"""E2 - segmentation and escape-surface matrix: which isolation boundaries are open?

Every probe is read-only or a TCP/HTTP connect with a 2 s timeout, run from inside
a tenant with `docker exec` (testbed/images/common/probe.py). Three positive
controls prove that "blocked" is not just "the network is broken".
Protocol: docs/experiments.md (E2).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import audit, compose, e1, load, util

BOTH_ALLOWED = {"insecure": "allowed", "hardened": "allowed"}
OPEN_THEN_BLOCKED = {"insecure": "allowed", "hardened": "blocked"}

# id, description, source, destination, control, axis, expected
PROBES = [
    ("C1", "Load generator reaches tenant-a's health endpoint", "loadgen", "tenant-a:8080", True,
     "cross-vm-attacks", BOTH_ALLOWED),
    ("C2", "Prometheus reaches the auditor on the provider network", "prometheus", "auditor:8088", True,
     "cross-vm-attacks", BOTH_ALLOWED),
    ("C3", "tenant-c reaches a listener on its own loopback", "tenant-c", "127.0.0.1", True,
     "isolation", BOTH_ALLOWED),
    ("P1", "tenant-c reaches tenant-a by DNS name", "tenant-c", "tenant-a:8080", False,
     "cross-vm-attacks", OPEN_THEN_BLOCKED),
    ("P2", "tenant-c reaches tenant-a by IP address", "tenant-c", "tenant-a IP:8080", False,
     "cross-vm-attacks", OPEN_THEN_BLOCKED),
    ("P3", "tenant-c reaches tenant-a through its published host port", "tenant-c", "host gateway:18080", False,
     "cross-vm-attacks", {"insecure": "platform-dependent", "hardened": "blocked"}),
    ("P4", "tenant-c reaches the decoy metadata service", "tenant-c", "metadata:8080", False,
     "cross-vm-attacks", OPEN_THEN_BLOCKED),
    ("P5", "tenant-c reaches provider telemetry (Prometheus API)", "tenant-c", "prometheus:9090", False,
     "data-leakage", OPEN_THEN_BLOCKED),
    ("P6", "tenant-c opens a connection to the internet", "tenant-c", "1.1.1.1:443", False,
     "data-leakage", OPEN_THEN_BLOCKED),
    ("P7", "tenant-c can see tenant-a's processes", "tenant-c", "/proc", False,
     "isolation", OPEN_THEN_BLOCKED),
    ("P8", "tenant-c can talk to the container engine API", "tenant-c", "/var/run/docker.sock", False,
     "hypervisor-vulnerabilities", OPEN_THEN_BLOCKED),
    ("P9", "tenant-c can read host system files", "tenant-c", "/host-etc", False,
     "data-leakage", OPEN_THEN_BLOCKED),
    ("P10", "tenant-c can read tenant-a's (non-secret) marker file", "tenant-c", "/data/tenant-a/marker.txt", False,
     "data-leakage", OPEN_THEN_BLOCKED),
    ("P11", "tenant-c holds Linux capabilities", "tenant-c", "CapEff", False,
     "isolation", OPEN_THEN_BLOCKED),
    ("P12", "tenant-b reaches tenant-a", "tenant-b", "tenant-a:8080", False,
     "cross-vm-attacks", OPEN_THEN_BLOCKED),
]


def probe_catalogue() -> list[dict]:
    return [{"id": i, "description": d, "source": s, "destination": t, "control": c, "axis": a, "expected": e}
            for i, d, s, t, c, a, e in PROBES]


def _exec_probe(service: str, *args: str) -> dict:
    name = compose.container_name(service)
    out = util.docker("exec", name, "python", "/opt/probes/probe.py", *args, timeout=120)
    return json.loads(out)


def _tenant_a_ip() -> str | None:
    doc = compose.inspect("tenant-a") or {}
    for net in (doc.get("NetworkSettings") or {}).get("Networks", {}).values():
        if net.get("IPAddress"):
            return net["IPAddress"]
    return None


def run(profile: str, variant: str = "full", out: Path | None = None) -> dict:
    audit.require_running(profile)
    outcomes: dict[str, tuple[str, str]] = {}

    # C1: a throwaway client on tenant-a's network, as the load generator would be.
    proc = util.run(["docker", "run", "--rm", "--network", load.victim_network(profile),
                     *util.operator_labels("e2-control"),
                     "--entrypoint", "python", "isolab/payments-api:local", "/opt/probes/probe.py",
                     "http-get", "tenant-a", "8080", "/healthz"], check=False, timeout=120)
    c1 = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {"outcome": "error",
                                                                               "detail": proc.stderr[-200:]}
    outcomes["C1"] = (c1["outcome"], c1["detail"])

    # C2: inside the provider plane.
    proc = util.run(["docker", "exec", compose.container_name("prometheus"), "wget", "-q", "-O", "/dev/null",
                     "-T", "2", "http://auditor:8088/healthz"], check=False, timeout=60)
    outcomes["C2"] = ("allowed", "HTTP 200 from auditor:8088") if proc.returncode == 0 else \
        ("blocked", (proc.stderr or proc.stdout).strip()[:200])

    ip = _tenant_a_ip() or ""
    for p in _exec_probe("tenant-c", "suite", "--role", "c", "--tenant-a-ip", ip)["probes"]:
        outcomes[p["id"]] = (p["outcome"], p["detail"])
    for p in _exec_probe("tenant-b", "suite", "--role", "b")["probes"]:
        outcomes[p["id"]] = (p["outcome"], p["detail"])

    results = []
    for probe in probe_catalogue():
        outcome, detail = outcomes.get(probe["id"], ("error", "not run"))
        expected = probe["expected"][profile]
        results.append({"profile": profile, "probeId": probe["id"], "outcome": outcome, "detail": detail,
                        "asExpected": expected == "platform-dependent" or outcome == expected})
        mark = util.ok if results[-1]["asExpected"] else util.fail
        mark(f"{probe['id']:4} {outcome:8} {probe['description']}  ({detail})")
    doc = {"profile": profile, "variant": variant, "results": results, "environment": e1.environment()}
    util.write_json(audit.run_dir(profile, out) / "e2.json", {**doc, **summary_for(profile, results)})
    return doc


def summary_for(profile: str, results: list[dict]) -> dict:
    controls = {p[0] for p in PROBES if p[4]}
    rs = [r for r in results if r["profile"] == profile]
    s = {
        "profile": profile,
        "openPaths": sum(r["outcome"] == "allowed" for r in rs if r["probeId"] not in controls),
        "probes": sum(r["probeId"] not in controls for r in rs),
        "controlsPassed": sum(r["outcome"] == "allowed" for r in rs if r["probeId"] in controls),
        "controls": sum(r["probeId"] in controls for r in rs),
    }
    util.info(f"E2 {profile}: {s['openPaths']}/{s['probes']} paths open, "
              f"controls {s['controlsPassed']}/{s['controls']}")
    return {"summary": [s]}
