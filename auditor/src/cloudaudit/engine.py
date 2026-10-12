"""Run the catalogue against a snapshot and build the report."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from pathlib import Path

from . import __version__
from .catalogue import CATALOGUE
from .checks import REGISTRY
from .models import AuditReport, CheckResult, Environment, Gate, Location, Target, Tool
from .policy import Policy, find_waiver, is_expired
from .scoring import score
from .snapshot import Snapshot

ORDER = {"fail": 4, "error": 3, "warn": 2, "pass": 1, "skip": 0}
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def worst(targets: list[Target]) -> str:
    statuses = [t.status for t in targets]
    if not statuses or all(s == "skip" for s in statuses):
        return "skip"
    return max((s for s in statuses if s != "skip"), key=ORDER.__getitem__)


def summarise(status: str, targets: list[Target]) -> str:
    if status == "skip":
        return targets[0].message if targets else "not applicable"
    bad = [t for t in targets if t.status == status]
    if status == "pass":
        return f"{len([t for t in targets if t.status == 'pass'])} of {len(targets)} passed"
    names = ", ".join(t.ref for t in bad[:4]) + (f" +{len(bad) - 4} more" if len(bad) > 4 else "")
    return f"{status} on {names}: {bad[0].message}"


def run_checks(snap: Snapshot, policy: Policy, waivers: list, today: date | None = None) -> list[CheckResult]:
    results = []
    for spec in CATALOGUE:
        fn = REGISTRY[spec.id]
        try:
            targets = fn(snap, policy)
        except Exception as exc:  # a broken check must show up, not vanish
            targets = [Target(kind="auditor", ref=spec.id, status="error", message=f"{type(exc).__name__}: {exc}")]
        status = worst(targets)
        result = CheckResult(check_id=spec.id, status=status, message=summarise(status, targets), targets=targets)
        if status in ("fail", "warn", "error"):
            failing = [t.ref for t in targets if t.status in ("fail", "warn", "error")]
            w = find_waiver(waivers, spec.id, snap.platform, failing)
            if w:
                result.waiver = w
                result.waived = not is_expired(w, today)
        results.append(result)
    return results


def gate(results: list[CheckResult], policy: Policy, today: date | None = None) -> Gate:
    threshold = SEVERITY_RANK[policy.gate.fail_on]
    specs = {c.id: c for c in CATALOGUE}
    blocking, waived, expired = [], [], []
    for r in results:
        if r.waiver and is_expired(r.waiver, today):
            expired.append(r.check_id)
        if r.status not in ("fail", "error"):
            continue
        if r.waived:
            waived.append(r.check_id)
        elif SEVERITY_RANK[specs[r.check_id].severity] >= threshold:
            blocking.append(r.check_id)
    return Gate(fail_on=policy.gate.fail_on, passed=not blocking and not expired, blocking=blocking,
                waived=waived, expired_waivers=expired)


def environment(snap: Snapshot) -> Environment:
    info = snap.info
    return Environment(
        platform=snap.platform if snap.platform in ("docker-desktop-wsl2", "docker-desktop", "github-ubuntu",
                                                    "linux", "fixture") else "linux",
        docker_server_version=str(snap.version.get("Version") or info.get("ServerVersion") or ""),
        api_version=str(snap.version.get("ApiVersion") or ""),
        operating_system=str(info.get("OperatingSystem") or ""),
        kernel_version=str(info.get("KernelVersion") or ""),
        cgroup_version=str(info.get("CgroupVersion") or ""),
        cgroup_driver=str(info.get("CgroupDriver") or ""),
        logical_cpus=int(info.get("NCPU") or 0),
        physical_cores=len(snap.host.cores),
        smt_control=snap.host.smt_control,
        smt_active=snap.host.smt_active,
        security_options=list(info.get("SecurityOptions") or []),
        ci=snap.ci,
    )


def locate(results: list[CheckResult], testbed_dir: str | None, profile: str) -> None:
    """Attach compose-file line numbers to targets, for SARIF and the web app."""
    if not testbed_dir:
        return
    files = [f"compose.{profile}.yaml", "compose.yaml"]
    index: dict[str, Location] = {}
    for name in reversed(files):  # overlay wins
        path = Path(testbed_dir) / name
        if not path.exists():
            continue
        section = None
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line and not line.startswith((" ", "#")):
                section = line.split(":", 1)[0]
            elif section in ("services", "networks", "volumes") and line.startswith("  ") and \
                    not line.startswith("   ") and line.strip().endswith(":"):
                index[f"{section}/{line.strip()[:-1]}"] = Location(file=f"testbed/{name}", line=n)
    policy_loc = Location(file="testbed/policy.yaml", line=1)
    for r in results:
        for t in r.targets:
            key = {"container": "services", "network": "networks", "volume": "volumes"}.get(t.kind)
            t.location = index.get(f"{key}/{t.ref}") if key else policy_loc
            if t.location is None:
                t.location = policy_loc


def build_report(snap: Snapshot, policy: Policy, waivers: list, today: date | None = None) -> AuditReport:
    results = run_checks(snap, policy, waivers, today)
    locate(results, os.environ.get("TESTBED_DIR"), snap.profile)
    return AuditReport(
        generated_at=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        profile=snap.profile if snap.profile in ("insecure", "hardened") else "fixture",
        tool=Tool(version=__version__, git_sha=os.environ.get("GIT_SHA") or None),
        environment=environment(snap),
        policy_sha256=policy.sha256,
        catalogue=CATALOGUE,
        results=results,
        scores=score(CATALOGUE, results),
        gate=gate(results, policy, today),
    )
