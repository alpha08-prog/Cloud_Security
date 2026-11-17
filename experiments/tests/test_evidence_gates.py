"""Scientific validity gates must reject missing, erroneous and misattributed evidence."""

import copy
import json
from pathlib import Path

import pytest

from isolab import audit, e2, e3, publish

ROOT = Path(__file__).resolve().parents[2]


def published(name):
    return json.loads((ROOT / "results" / "published" / f"{name}.json").read_text(encoding="utf-8"))


def test_committed_experiments_pass_strict_evidence_gates():
    segmentation, detection = published("e2"), published("e3")
    assert e2.isolation_passed("hardened", segmentation["results"])
    for profile in ("insecure", "hardened"):
        assert e3.detection_passed(profile, detection["results"], detection["falsePositives"])


@pytest.mark.parametrize("damage", ["error", "missing", "duplicate", "open", "control"])
def test_isolation_rejects_invalid_evidence(damage):
    doc = published("e2")
    rows = [r for r in doc["results"] if r["profile"] == "hardened"]
    probe = next(r for r in rows if r["probeId"] == "P1")
    if damage == "missing":
        rows.remove(probe)
    elif damage == "duplicate":
        rows.append(copy.deepcopy(probe))
    elif damage == "control":
        rows[0]["outcome"] = "blocked"
    else:
        probe["outcome"] = "error" if damage == "error" else "allowed"
    assert not e2.isolation_passed("hardened", rows)
    run = {**doc, "results": rows}
    assert publish.e2_doc({"hardened": run})["hypotheses"][1]["verdict"] == "not-supported"


@pytest.mark.parametrize("damage", ["attribution", "late", "missing", "duplicate", "silence", "false-positive"])
def test_detection_rejects_invalid_evidence(damage):
    doc = published("e3")
    rows = [r for r in doc["results"] if r["profile"] == "hardened"]
    if damage == "attribution":
        rows[0]["attributionCorrect"] = False
    elif damage == "late":
        rows[0]["withinSlo"] = False
    elif damage == "missing":
        rows.pop()
    elif damage == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif damage == "silence":
        next(r for r in rows if r["triggerId"] == "T7")["detected"] = True
    else:
        doc["falsePositives"].append({"profile": "hardened"})
    assert not e3.detection_passed("hardened", rows, doc["falsePositives"])
    assert publish.e3_doc({"hardened": {**doc, "results": rows}})["hypotheses"][0]["verdict"] == "not-supported"


def test_live_gate_rejects_wrong_attribution_even_with_good_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "run_dir", lambda *args: tmp_path)
    (tmp_path / "audit.json").write_text(json.dumps(published("audit-hardened")), encoding="utf-8")
    doc = published("e3")
    next(r for r in doc["results"] if r["profile"] == "hardened")["attributionCorrect"] = False
    (tmp_path / "e3.json").write_text(json.dumps(doc), encoding="utf-8")
    assert not audit.gate("hardened")
