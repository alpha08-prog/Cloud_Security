"""Every check against real snapshots of both profiles (recorded on Docker Desktop)."""

from __future__ import annotations

import pytest
from conftest import TODAY

from cloudaudit.catalogue import CATALOGUE
from cloudaudit.checks import REGISTRY
from cloudaudit.engine import build_report, run_checks

INSECURE_EXPECTED = {
    "ISO-01": "fail", "ISO-02": "fail", "ISO-03": "fail", "ISO-04": "fail", "ISO-05": "fail", "ISO-06": "fail",
    "ISO-07": "fail",
    "HV-01": "fail", "HV-02": "pass", "HV-03": "fail", "HV-04": "fail", "HV-05": "skip",
    "DL-01": "fail", "DL-02": "fail", "DL-03": "fail", "DL-04": "fail", "DL-05": "fail",
    "XVM-01": "fail", "XVM-02": "fail", "XVM-03": "pass", "XVM-04": "fail", "XVM-05": "fail", "XVM-06": "pass",
    "XVM-07": "pass",
    "ID-01": "fail", "ID-02": "fail", "ID-03": "fail", "ID-04": "fail", "ID-05": "pass",
}


def test_every_catalogue_entry_has_an_implementation():
    assert set(REGISTRY) == {c.id for c in CATALOGUE}
    assert len(CATALOGUE) == 30


@pytest.mark.parametrize("check_id,expected", sorted(INSECURE_EXPECTED.items()))
def test_insecure_profile(insecure, policy, waivers, check_id, expected):
    results = {r.check_id: r for r in run_checks(insecure, policy, waivers, TODAY)}
    assert results[check_id].status == expected, results[check_id].message


def test_hardened_profile_passes_except_documented_host_limits(hardened, policy, waivers):
    results = {r.check_id: r for r in run_checks(hardened, policy, waivers, TODAY)}
    not_passing = {k: (r.status, r.waived) for k, r in results.items() if r.status != "pass"}
    # HV-03/HV-04: provider-layer limits of Docker Desktop, waived; HV-05: no AppArmor in the VM.
    assert not_passing == {"HV-03": ("fail", True), "HV-04": ("fail", True), "HV-05": ("skip", False)}


def test_hardened_gate_passes_and_insecure_gate_fails(insecure, hardened, policy, waivers):
    assert build_report(hardened, policy, waivers, TODAY).gate.passed
    bad = build_report(insecure, policy, waivers, TODAY).gate
    assert not bad.passed
    assert {"ISO-01", "HV-01", "XVM-01", "ID-01"} <= set(bad.blocking)


def test_insecure_fails_on_every_axis(insecure, policy, waivers):
    results = {r.check_id: r.status for r in run_checks(insecure, policy, waivers, TODAY)}
    for axis in {c.axis for c in CATALOGUE}:
        assert any(results[c.id] == "fail" for c in CATALOGUE if c.axis == axis), axis


def test_provider_exceptions_are_reported_as_skips_not_passes(hardened, policy, waivers):
    results = {r.check_id: r for r in run_checks(hardened, policy, waivers, TODAY)}
    proxy = next(t for t in results["HV-01"].targets if t.ref == "socket-proxy")
    assert proxy.status == "skip" and proxy.evidence.get("exception") is True


def test_secret_values_never_reach_the_report(insecure, policy, waivers):
    report = build_report(insecure, policy, waivers, TODAY).model_dump_json()
    assert "not-a-real-secret" not in report
    dl05 = next(r for r in build_report(insecure, policy, waivers, TODAY).results if r.check_id == "DL-05")
    assert dl05.targets[-1].evidence["variables"] == ["LEGACY_DB_PASSWORD"] or any(
        t.evidence.get("variables") == ["LEGACY_DB_PASSWORD"] for t in dl05.targets)


def test_targets_reference_services_not_container_ids(insecure, policy, waivers):
    report = build_report(insecure, policy, waivers, TODAY)
    ids = {c["Id"][:12] for c in insecure.containers}
    for r in report.results:
        for t in r.targets:
            assert t.ref[:12] not in ids


def test_a_broken_check_reports_error_instead_of_vanishing(hardened, policy, waivers, monkeypatch):
    def boom(snap, pol):
        raise RuntimeError("synthetic")

    monkeypatch.setitem(REGISTRY, "ISO-01", boom)
    result = next(r for r in run_checks(hardened, policy, waivers, TODAY) if r.check_id == "ISO-01")
    assert result.status == "error" and "synthetic" in result.message
