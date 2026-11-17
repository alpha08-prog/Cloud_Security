"""Retain a compact, hashed summary of a fresh hardened E2/E3/audit smoke run."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
from isolab.e2 import isolation_passed  # noqa: E402
from isolab.e3 import detection_passed  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    args = parser.parse_args()
    paths = {name: args.runs.resolve() / "hardened" / f"{name}.json" for name in ("audit", "e2", "e3")}
    data = {name: json.loads(path.read_bytes()) for name, path in paths.items()}
    report = {
        "generatedAt": datetime.now(UTC).isoformat(), "kind": "fresh-hardened-smoke-summary",
        "variant": data["e3"]["variant"], "quietWindowSeconds": data["e3"]["quietWindowSeconds"],
        "e2Passed": isolation_passed("hardened", data["e2"]["results"]),
        "e3Passed": detection_passed("hardened", data["e3"]["results"], data["e3"]["falsePositives"]),
        "auditGate": data["audit"]["gate"],
        "e2Results": data["e2"]["results"], "e3Results": data["e3"]["results"],
        "falsePositives": data["e3"]["falsePositives"],
        "inputs": {name: {"path": path.relative_to(ROOT).as_posix(),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                   for name, path in paths.items()},
        "limit": "Shortened hardened checks; no fresh E1 benchmark or insecure comparison in this smoke run.",
    }
    out = ROOT / "results/research/revision-smoke.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"E2={report['e2Passed']}, E3={report['e3Passed']}, audit={report['auditGate']['passed']}: {out}")
    return 0 if report["e2Passed"] and report["e3Passed"] and report["auditGate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
