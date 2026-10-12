from __future__ import annotations

from datetime import date

from conftest import TODAY

from cloudaudit.engine import build_report, gate, run_checks
from cloudaudit.models import CheckResult, CheckSpec, Frameworks, Waiver
from cloudaudit.scoring import score


def spec(id: str, axis: str, severity: str) -> CheckSpec:
    return CheckSpec(id=id, title=id, description="", axis=axis, requirements=["R2"], severity=severity,
                     scope="host", taxonomy=[], remediation="",
                     frameworks=Frameworks(csa_top_threats=[], csa_domains=[], enisa=[], nist=[]))


def result(id: str, status: str, waived: bool = False) -> CheckResult:
    return CheckResult(check_id=id, status=status, waived=waived, message="", targets=[])


def test_worked_example_from_the_viva_notes():
    # HV-01 critical pass (4) + HV-02 medium pass (2) + HV-03 high warn (1.5) + HV-04 medium waived (0)
    # + HV-06 medium pass (2), HV-05 skipped: 9.5 / 13
    hv = "hypervisor-vulnerabilities"
    cat = [spec("HV-01", hv, "critical"), spec("HV-02", hv, "medium"), spec("HV-03", hv, "high"),
           spec("HV-04", hv, "medium"), spec("HV-05", hv, "medium"), spec("HV-06", hv, "medium")]
    res = [result("HV-01", "pass"), result("HV-02", "pass"), result("HV-03", "warn"),
           result("HV-04", "fail", waived=True), result("HV-05", "skip"), result("HV-06", "pass")]
    s = next(x for x in score(cat, res).by_axis if x.key == hv)
    assert (s.earned, s.possible, s.evaluated, s.skipped, s.total) == (9.5, 13, 5, 1, 6)
    assert s.score == round(9.5 / 13, 4)


def test_axis_with_nothing_evaluated_has_null_score():
    s = score([spec("HV-05", "hypervisor-vulnerabilities", "medium")], [result("HV-05", "skip")])
    assert next(x for x in s.by_axis if x.key == "hypervisor-vulnerabilities").score is None


def test_unweighted_score_counts_checks_equally():
    cat = [spec("ISO-01", "isolation", "critical"), spec("ISO-02", "isolation", "low")]
    s = score(cat, [result("ISO-01", "pass"), result("ISO-02", "fail")])
    assert next(x for x in s.unweighted_by_axis if x.key == "isolation").score == 0.5
    assert next(x for x in s.by_axis if x.key == "isolation").score == 0.8


def test_expired_waiver_blocks_the_gate(hardened, policy):
    stale = [Waiver(check_id="HV-03", platform="*", reason="old", expires=date(2026, 1, 1), approved_by="x"),
             Waiver(check_id="HV-04", platform="*", reason="old", expires=date(2026, 1, 1), approved_by="x")]
    results = run_checks(hardened, policy, stale, TODAY)
    g = gate(results, policy, TODAY)
    assert not g.passed
    assert set(g.expired_waivers) == {"HV-03", "HV-04"}
    assert "HV-03" in g.blocking  # high severity, no longer waived


def test_waiver_only_applies_on_its_platform(hardened, policy):
    other = [Waiver(check_id="HV-03", platform="github-ubuntu", reason="x", expires=date(2099, 1, 1), approved_by="x")]
    r = next(r for r in run_checks(hardened, policy, other, TODAY) if r.check_id == "HV-03")
    assert not r.waived


def test_waived_checks_earn_no_credit(hardened, policy, waivers):
    report = build_report(hardened, policy, waivers, TODAY)
    hv = next(s for s in report.scores.by_axis if s.key == "hypervisor-vulnerabilities")
    assert hv.score < 1.0
    assert report.gate.waived == ["HV-03", "HV-04"]
