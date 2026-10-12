"""The report contract: committed schemas are current, reports and SARIF validate."""

from __future__ import annotations

import json

import jsonschema
from conftest import SCHEMAS, TODAY, read_json

from cloudaudit.catalogue import CATALOGUE, to_markdown
from cloudaudit.cli import write_schemas
from cloudaudit.engine import build_report
from cloudaudit.models import AXES
from cloudaudit.report import to_sarif


def test_committed_schemas_match_the_models(tmp_path):
    write_schemas(tmp_path)
    for generated in sorted(tmp_path.glob("*.json")):
        committed = SCHEMAS / generated.name
        assert committed.exists(), f"run `cloudaudit schema --out schemas` ({generated.name} missing)"
        assert read_json(committed) == read_json(generated), f"{generated.name} is stale: regenerate it"


def test_reports_validate_against_the_schema(insecure, hardened, policy, waivers):
    schema = read_json(SCHEMAS / "audit-report.schema.json")
    for snap in (insecure, hardened):
        jsonschema.validate(build_report(snap, policy, waivers, TODAY).dump(), schema)


def test_sarif_is_valid_sarif_2_1_0(insecure, policy, waivers):
    sarif = to_sarif(build_report(insecure, policy, waivers, TODAY))
    jsonschema.validate(json.loads(json.dumps(sarif)), read_json(SCHEMAS / "vendor" / "sarif-2.1.0.json"))
    assert sarif["runs"][0]["results"], "the insecure profile must produce findings"


def test_sarif_findings_point_at_compose_lines(insecure, policy, waivers, monkeypatch):
    monkeypatch.setenv("TESTBED_DIR", str(SCHEMAS.parent / "testbed"))
    sarif = to_sarif(build_report(insecure, policy, waivers, TODAY))
    privileged = next(r for r in sarif["runs"][0]["results"] if r["ruleId"] == "ISO-01")
    loc = privileged["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == "testbed/compose.insecure.yaml"
    lines = (SCHEMAS.parent / "testbed" / "compose.insecure.yaml").read_text().splitlines()
    assert lines[loc["region"]["startLine"] - 1].strip() == "tenant-c:"


def test_waived_findings_are_suppressed_in_sarif(hardened, policy, waivers):
    sarif = to_sarif(build_report(hardened, policy, waivers, TODAY))
    results = sarif["runs"][0]["results"]
    assert results and all("suppressions" in r for r in results)  # hardened: only the waived host issues


def test_catalogue_covers_every_axis_and_requirement():
    for axis in AXES:
        assert sum(c.axis == axis for c in CATALOGUE) >= 3, axis
    for req in ("R1", "R2", "R3", "R4"):
        assert any(req in c.requirements for c in CATALOGUE), req


def test_checks_doc_is_current():
    doc = (SCHEMAS.parent / "docs" / "checks.md").read_text(encoding="utf-8")
    assert doc.strip() == to_markdown().strip(), "regenerate docs/checks.md (cloudaudit catalogue --format md)"
