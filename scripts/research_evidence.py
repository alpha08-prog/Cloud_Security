"""Recompute manuscript statistics from committed measurements without Docker.

Run with the auditor dependencies installed and auditor/src plus experiments on PYTHONPATH.
This never changes results/published or exposes the blind literature sample.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

from isolab import e2, e3  # noqa: E402


def read(name):
    return json.loads((ROOT / "results/published" / name).read_text(encoding="utf-8"))


def wilson(k, n):
    z = 1.959963984540054
    denominator = 1 + z * z / n
    centre = (k / n + z * z / (2 * n)) / denominator
    half = z * math.sqrt(k / n * (1 - k / n) / n + z * z / (4 * n * n)) / denominator
    return [round(centre - half, 4), round(centre + half, 4)]


def main():
    latency, paths, detections = [read(f"{name}.json") for name in ("e1", "e2", "e3")]
    output = {"basis": "Reanalysis of committed 2026-10-12 measurements; not a fresh live run",
              "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((ROOT / "results/published").iterdir()) if p.is_file()},
              "profiles": {}}
    for profile in ("insecure", "hardened"):
        audit = read(f"audit-{profile}.json")
        catalogue = {c["id"]: c for c in audit["catalogue"]}
        weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        credits = {"pass": 1, "warn": .5, "fail": 0, "error": 0}
        earned = possible = 0
        for result in audit["results"]:
            if result["status"] == "skip":
                continue
            weight = weights[catalogue[result["checkId"]]["severity"]]
            possible += weight
            earned += weight * (0 if result["waived"] else credits[result["status"]])
        assert round(earned / possible, 4) == audit["scores"]["overall"]["score"]
        runs = [r for r in latency["runs"] if r["profile"] == profile]
        medians = {arm: statistics.median(r["latencyMs"]["p99"] for r in runs if r["arm"] == arm)
                   for arm in ("baseline", "noisy")}
        for run in runs:
            assert run["valid"] and run["droppedIterations"] == 0 and run["failedRate"] <= .01
            if run["arm"] == "noisy":
                assert run["noisyCoresUsed"] >= 1  # observed full run exceeds both protocol floors
        saved = next(s for s in latency["summary"] if s["profile"] == profile)
        assert round(medians["baseline"], 3) == saved["baselineP99Ms"]
        assert round(medians["noisy"], 3) == saved["noisyP99Ms"]
        assert e3.detection_passed(profile, detections["results"], detections["falsePositives"])
        summary = e3.summary_for(profile, detections["results"], detections["falsePositives"])
        assert summary == next(s for s in detections["summary"] if s["profile"] == profile)
        output["profiles"][profile] = {
            "coverage": earned / possible, "earned": earned, "possible": possible,
            "checkStatuses": dict(Counter(r["status"] for r in audit["results"])),
            "p99MediansMs": medians,
            "p99RangesMs": {arm: [min(r["latencyMs"]["p99"] for r in runs if r["arm"] == arm),
                                   max(r["latencyMs"]["p99"] for r in runs if r["arm"] == arm)]
                            for arm in ("baseline", "noisy")},
            "ifFromUnroundedMedians": medians["noisy"] / medians["baseline"],
            "totalMeasuredIterations": sum(r["iterations"] for r in runs),
            "detectionWilson95": wilson(summary["detected"], summary["expected"]),
            "e3": summary,
        }
    assert e2.isolation_passed("hardened", paths["results"])
    insecure, hardened = (output["profiles"][p] for p in ("insecure", "hardened"))
    output["noisyP99ReductionPct"] = 100 * (1 - hardened["p99MediansMs"]["noisy"] /
                                            insecure["p99MediansMs"]["noisy"])
    output["zeroEventPoissonUpper95PerMinute"] = -math.log(.05) / (detections["quietWindowSeconds"] / 60)
    output["intervalCaveat"] = "Wilson intervals assume independent Bernoulli trials; triggers differ by design."
    dest = ROOT / "docs/research/evidence.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
