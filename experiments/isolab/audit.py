"""`lab.py audit`, `lab.py gate` and `lab.py snapshot`."""

from __future__ import annotations

import json
from pathlib import Path

from . import auditor, compose, util

NEGATIVE_CONTROL = ("ISO-01", "HV-01", "XVM-01", "ID-01")  # must fail in the insecure profile


def run_dir(profile: str, out: Path | None = None) -> Path:
    return (out or util.RUNS / util.detect_platform()) / profile


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(util.REPO))
    except ValueError:
        return str(path)


def require_running(profile: str) -> None:
    running = compose.current_profile()
    if running != profile:
        raise util.CommandError(f"the {profile} profile is not running (running: {running}); "
                                f"run `lab.py up {profile}` first")


def audit(profile: str, out: Path | None = None) -> dict:
    require_running(profile)
    auditor.wait_ready()
    report = auditor.get_json("/report?fresh=1", timeout=120)
    sarif = auditor.get_json("/report.sarif")
    d = run_dir(profile, out)
    util.write_json(d / "audit.json", report)
    util.write_json(d / "audit.sarif", sarif)
    print(auditor.get("/report.txt").decode())
    util.ok(f"saved {_rel(d)}/audit.json and audit.sarif")
    return report


def gate(profile: str, out: Path | None = None) -> bool:
    """Hardened: the policy gate must pass, and the E2/E3 gates if those ran.
    Insecure: a negative control - known-bad settings must be caught on every axis."""
    d = run_dir(profile, out)
    report = util.read_json(d / "audit.json")
    ok = True
    if profile == "hardened":
        g = report["gate"]
        if g["passed"]:
            util.ok(f"policy gate passed (waived: {', '.join(g['waived']) or 'none'})")
        else:
            util.fail(f"policy gate failed: blocking {', '.join(g['blocking']) or '-'}; "
                      f"expired waivers {', '.join(g['expiredWaivers']) or '-'}")
            ok = False
        if (d / "e2.json").exists():
            s = next(x for x in util.read_json(d / "e2.json")["summary"] if x["profile"] == profile)
            passed = s["openPaths"] == 0 and s["controlsPassed"] == s["controls"]
            (util.ok if passed else util.fail)(
                f"E2: {s['openPaths']} open paths, controls {s['controlsPassed']}/{s['controls']}")
            ok &= passed
        if (d / "e3.json").exists():
            s = next(x for x in util.read_json(d / "e3.json")["summary"] if x["profile"] == profile)
            passed = s["detected"] == s["expected"] and s["falsePositives"] == 0
            (util.ok if passed else util.fail)(
                f"E3: detected {s['detected']}/{s['expected']}, false positives {s['falsePositives']}")
            ok &= passed
    else:
        status = {r["checkId"]: r["status"] for r in report["results"]}
        missed = [c for c in NEGATIVE_CONTROL if status.get(c) != "fail"]
        if missed:
            util.fail(f"negative control: the auditor did not catch {', '.join(missed)} in the insecure profile")
            ok = False
        else:
            util.ok(f"negative control: insecure profile correctly fails {', '.join(NEGATIVE_CONTROL)}")
        axis_of = {c["id"]: c["axis"] for c in report["catalogue"]}
        by_axis: dict[str, list[str]] = {}
        for r in report["results"]:
            by_axis.setdefault(axis_of[r["checkId"]], []).append(r["status"])
        clean = [a for a, statuses in by_axis.items() if "fail" not in statuses]
        if clean:
            util.fail(f"negative control: no failing check on axis {', '.join(clean)}")
            ok = False
        else:
            util.ok("negative control: every Figure 11 axis has at least one failing check")
    return ok


def snapshot(profile: str) -> Path:
    doc = auditor.get_json("/snapshot")
    kind = "desktop" if "desktop" in util.detect_platform() else "ubuntu"
    path = util.REPO / "auditor" / "tests" / "fixtures" / "snapshots" / f"{profile}-{kind}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8", newline="\n")
    util.ok(f"saved {_rel(path)}")
    return path
