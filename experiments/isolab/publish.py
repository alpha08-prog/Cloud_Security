"""`lab.py publish`: merge both profiles' runs into results/published/ and evaluate
the pre-registered hypotheses (docs/experiments.md). The web app imports these
files at build time; their shape is schemas/*.schema.json (validated here, in the
auditor's dev container, and again by the web app's contract tests).
"""

from __future__ import annotations

import shutil
import statistics
from pathlib import Path

from . import devtools, e2, e3, util

SCHEMA_VERSION = "1.0.0"


def _load(run_root: Path, profile: str, name: str) -> dict | None:
    path = run_root / profile / name
    return util.read_json(path) if path.exists() else None


def _verdict(ok: bool | None) -> str:
    return "inconclusive" if ok is None else ("supported" if ok else "not-supported")


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 3) if values else None


def e1_doc(runs: dict[str, dict], e3s: dict[str, dict]) -> dict:
    base = runs.get("hardened") or runs.get("insecure")
    slo = base["config"]["sloP99Ms"]
    all_runs = [r for p in ("insecure", "hardened") if p in runs for r in runs[p]["runs"]]
    summary = []
    for profile in ("insecure", "hardened"):
        rs = [r for r in all_runs if r["profile"] == profile]
        if not rs:
            continue
        valid = [r for r in rs if r["valid"]]
        b = _median([r["latencyMs"]["p99"] for r in valid if r["arm"] == "baseline"])
        n = _median([r["latencyMs"]["p99"] for r in valid if r["arm"] == "noisy"])
        summary.append({"profile": profile, "baselineP99Ms": b, "noisyP99Ms": n,
                        "interferenceFactor": round(n / b, 3) if b and n else None,
                        "sloMetUnderNoise": (n <= slo) if n is not None else None,
                        "validRuns": len(valid), "totalRuns": len(rs)})
    s = {x["profile"]: x for x in summary}
    if_i = (s.get("insecure") or {}).get("interferenceFactor")
    if_h = (s.get("hardened") or {}).get("interferenceFactor")
    det = {p: runs[p].get("noisyNeighbourDetections") for p in runs}
    t7 = {p: next((r for r in e3s[p]["results"] if r["triggerId"] == "T7"), None) for p in e3s}
    # H4 is tested by E3's T7 trigger, which waits up to 90 s for DET-08. E1's noisy windows
    # only add evidence when they outlast DET-08's 30 s sustain requirement by a margin; then
    # the hardened profile must also have stayed silent during E1.
    h4_parts = []
    if t7.get("insecure") and t7.get("hardened"):
        h4_parts.append(t7["insecure"]["detected"] and not t7["hardened"]["detected"])
    if base["config"]["measureSeconds"] >= 60 and "hardened" in det:
        h4_parts.append(det["hardened"] == 0)
    hypotheses = [
        {"id": "H1", "statement": "Insecure: interference factor (p99 noisy / p99 baseline) >= 2",
         "verdict": _verdict(None if if_i is None else if_i >= 2),
         "detail": f"IF = {if_i}" if if_i is not None else "no valid insecure runs"},
        {"id": "H2", "statement": f"Hardened: interference factor <= 1.25 and p99 under noise <= {slo:g} ms",
         "verdict": _verdict(None if if_h is None else (if_h <= 1.25 and bool(s['hardened']['sloMetUnderNoise']))),
         "detail": f"IF = {if_h}, p99 under noise = {s.get('hardened', {}).get('noisyP99Ms')} ms"
         if if_h is not None else "no valid hardened runs"},
        {"id": "H3", "statement": "Optional SMT-shared arm: higher server time than hardened",
         "verdict": "inconclusive", "detail": "optional arm not run (Hyper-V vCPU mapping makes it indicative only)"},
        {"id": "H4", "statement": "DET-08 fires under noise in insecure and stays silent in hardened",
         "verdict": _verdict(all(h4_parts) if h4_parts else None),
         "detail": f"E1 DET-08 detections: {det}; E3 T7 detected: "
                   f"{ {p: (v or {}).get('detected') for p, v in t7.items()} }"},
    ]
    return {"schemaVersion": SCHEMA_VERSION, "kind": "e1", "generatedAt": util.utc_now(),
            "variant": base["variant"], "environment": base["environment"], "hypotheses": hypotheses,
            "config": base["config"], "runs": all_runs, "summary": summary}


def e2_doc(runs: dict[str, dict]) -> dict:
    base = runs.get("hardened") or runs.get("insecure")
    results = [r for p in ("insecure", "hardened") if p in runs for r in runs[p]["results"]]
    summary = [s for p in ("insecure", "hardened") if p in runs for s in runs[p]["summary"]]
    s = {x["profile"]: x for x in summary}
    i, h = s.get("insecure"), s.get("hardened")
    hypotheses = [
        {"id": "H5", "statement": "Insecure: at least 10 of 12 isolation paths are open",
         "verdict": _verdict(None if i is None else i["openPaths"] >= 10),
         "detail": f"{i['openPaths']}/{i['probes']} open" if i else "insecure not run"},
        {"id": "H6", "statement": "Hardened: 0 of 12 paths open, with every positive control passing",
         "verdict": _verdict(None if h is None else h["openPaths"] == 0 and h["controlsPassed"] == h["controls"]),
         "detail": f"{h['openPaths']}/{h['probes']} open, controls {h['controlsPassed']}/{h['controls']}"
         if h else "hardened not run"},
    ]
    return {"schemaVersion": SCHEMA_VERSION, "kind": "e2", "generatedAt": util.utc_now(), "variant": base["variant"],
            "environment": base["environment"], "hypotheses": hypotheses, "probes": e2.probe_catalogue(),
            "results": results, "summary": summary}


def e3_doc(runs: dict[str, dict]) -> dict:
    base = runs.get("hardened") or runs.get("insecure")
    results = [r for p in ("insecure", "hardened") if p in runs for r in runs[p]["results"]]
    fps = [f for p in ("insecure", "hardened") if p in runs for f in runs[p]["falsePositives"]]
    summary = [s for p in ("insecure", "hardened") if p in runs for s in runs[p]["summary"]]
    ok = [s["detected"] == s["expected"] and s["falsePositives"] == 0 and s["attributionAccuracy"] == 1
          for s in summary]
    detail = "; ".join(f"{s['profile']}: {s['detected']}/{s['expected']} detected, {s['falsePositives']} false "
                       f"positives, median {s['medianLatencyMs']} ms, attribution {s['attributionAccuracy']}"
                       for s in summary)
    hypotheses = [{"id": "H7", "statement": "100% detection within SLO, correct attribution, 0 false positives",
                   "verdict": _verdict(all(ok) if ok else None), "detail": detail or "not run"}]
    return {"schemaVersion": SCHEMA_VERSION, "kind": "e3", "generatedAt": util.utc_now(), "variant": base["variant"],
            "environment": base["environment"], "hypotheses": hypotheses,
            "quietWindowSeconds": base["quietWindowSeconds"], "triggers": e3.catalogue(), "results": results,
            "falsePositives": fps, "summary": summary}


def publish(run_root: Path | None = None, dest: Path | None = None) -> Path:
    run_root = run_root or util.RUNS / util.detect_platform()
    dest = dest or util.PUBLISHED
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for profile in ("insecure", "hardened"):
        for name, target in (("audit.json", f"audit-{profile}.json"), ("audit.sarif", f"audit-{profile}.sarif")):
            src = run_root / profile / name
            if src.exists():
                shutil.copyfile(src, dest / target)
                written.append(target)
    runs = {n: {p: d for p in ("insecure", "hardened") if (d := _load(run_root, p, f"{n}.json"))}
            for n in ("e1", "e2", "e3")}
    if runs["e3"]:
        util.write_json(dest / "e3.json", e3_doc(runs["e3"]))
        written.append("e3.json")
    if runs["e2"]:
        util.write_json(dest / "e2.json", e2_doc(runs["e2"]))
        written.append("e2.json")
    if runs["e1"]:
        util.write_json(dest / "e1.json", e1_doc(runs["e1"], runs["e3"]))
        written.append("e1.json")
    util.write_json(dest / "manifest.json", {"generatedAt": util.utc_now(), "platform": run_root.name,
                                             "gitSha": util.git_sha(), "files": sorted(written)})
    rc = devtools.validate(dest)
    if rc != 0:
        raise util.CommandError("published results do not match schemas/*.schema.json")
    for name in ("e1.json", "e2.json", "e3.json"):
        if (dest / name).exists():
            for h in util.read_json(dest / name)["hypotheses"]:
                mark = {"supported": util.ok, "not-supported": util.fail}.get(h["verdict"], util.warn)
                mark(f"{h['id']} {h['verdict']}: {h['statement']} ({h['detail']})")
    shown = dest.relative_to(util.REPO) if dest.is_relative_to(util.REPO) else dest
    util.ok(f"published {len(written)} files to {shown}")
    return dest
