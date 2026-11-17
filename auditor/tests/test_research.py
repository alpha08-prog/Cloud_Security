from __future__ import annotations

import json
from pathlib import Path

import pytest

from cloudaudit.catalogue import CATALOGUE
from cloudaudit.models import AuditReport
from cloudaudit.research import FAULTS, THEMES, assess, fault_study, generate, mutate

ROOT = Path(__file__).resolve().parents[2]


def test_e4_detects_independent_faults_without_changing_input(hardened, policy):
    original = hardened.model_dump_json()
    report = fault_study(hardened, policy)
    assert report["passed"]
    assert report["detected"] == report["total"] == 10
    assert all(r["baseline"] == "pass" and r["mutated"] == "fail" for r in report["cases"])
    assert original == hardened.model_dump_json()


def test_preexisting_fault_does_not_count_as_new_detection(hardened, policy):
    broken = hardened.model_copy(deep=True)
    mutate(broken, "privileged")
    report = fault_study(broken, policy)
    assert not report["passed"]
    assert not report["cases"][0]["detected"]


def test_missing_target_and_unknown_mutation_rejected(hardened):
    with pytest.raises(ValueError, match="Unknown"):
        mutate(hardened.model_copy(deep=True), "invalid")
    empty = hardened.model_copy(deep=True)
    empty.containers = []
    with pytest.raises(ValueError, match="exactly one"):
        mutate(empty, "root")


@pytest.mark.parametrize("status,waived", [("fail", True), ("skip", False), ("error", False), ("pass", True)])
def test_mapping_never_counts_unverified_evidence(status, waived):
    report = AuditReport.model_validate_json((ROOT / "results/published/audit-hardened.json").read_bytes())
    row = next(r for r in report.results if r.check_id == "ISO-01")
    row.status, row.waived = status, waived
    assert not assess(report, ["ISO-01"])["configurationVerified"]


def test_missing_and_duplicate_checks_fail_closed():
    report = AuditReport.model_validate_json((ROOT / "results/published/audit-hardened.json").read_bytes())
    row = next(r for r in report.results if r.check_id == "ISO-01")
    report.results.append(row.model_copy(deep=True))
    assert not assess(report, ["ISO-01"])["configurationVerified"]
    assert not assess(report, ["NONEXISTENT"])["configurationVerified"]
    assert not assess(report, [])["configurationVerified"]


def test_research_references_and_inputs():
    known = {c.id for c in CATALOGUE}
    assert all(set(t["checks"]) <= known for t in THEMES)
    assert len({r[0] for r in FAULTS}) == len(FAULTS)
    result = generate(ROOT)
    assert result["e4"]["passed"]
    assert result["e5"]["passed"]
    assert sum(row["executed"] for row in result["e5"]["cases"]) == 1
    for item in result["inputs"].values():
        assert len(item["sha256"]) == 64
        assert (ROOT / item["path"]).is_file()
    assert len(json.dumps(result)) > 100
