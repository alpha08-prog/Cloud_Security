"""Report renderers: SARIF 2.1.0 for code scanning, and a console summary."""

from __future__ import annotations

from .catalogue import BY_ID, CATALOGUE
from .models import AuditReport

SECURITY_SEVERITY = {"critical": "9.5", "high": "7.5", "medium": "5.0", "low": "2.0"}
LEVEL = {"fail": "error", "error": "error", "warn": "warning"}
REPO_URL = "https://github.com/alpha08-prog/Cloud_Security"


def to_sarif(report: AuditReport) -> dict:
    rules = []
    for c in CATALOGUE:
        rules.append({
            "id": c.id,
            "name": c.title.replace(" ", ""),
            "shortDescription": {"text": c.title},
            "fullDescription": {"text": c.description},
            "help": {
                "text": f"{c.description}\n\nRemediation: {c.remediation}",
                "markdown": f"{c.description}\n\n**Remediation:** {c.remediation}\n\n"
                            f"Paper taxonomy: {', '.join(f'`{t}`' for t in c.taxonomy)}",
            },
            "defaultConfiguration": {"level": "error" if c.severity in ("critical", "high") else "warning"},
            "properties": {
                "security-severity": SECURITY_SEVERITY[c.severity],
                "tags": ["security", f"axis:{c.axis}", *[f"requirement:{r}" for r in c.requirements]],
                "precision": "high",
            },
        })
    results = []
    for r in report.results:
        spec = BY_ID[r.check_id]
        for t in r.targets:
            if t.status not in LEVEL:
                continue
            loc = t.location
            entry = {
                "ruleId": r.check_id,
                "level": LEVEL[t.status],
                "message": {"text": f"[{report.profile}] {t.ref}: {t.message}"},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": loc.file if loc else "testbed/policy.yaml",
                                             "uriBaseId": "%SRCROOT%"},
                        "region": {"startLine": loc.line if loc else 1},
                    },
                    "logicalLocations": [{"name": t.ref, "kind": t.kind}],
                }],
                "partialFingerprints": {"isolabTarget/v1": f"{report.profile}:{r.check_id}:{t.kind}:{t.ref}"},
                "properties": {"axis": spec.axis, "tenant": t.tenant, "severity": spec.severity},
            }
            if r.waived and r.waiver:
                entry["suppressions"] = [{"kind": "external", "status": "accepted",
                                          "justification": f"{r.waiver.reason.strip()} (expires "
                                                           f"{r.waiver.expires}, approved by {r.waiver.approved_by})"}]
            results.append(entry)
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "cloudaudit", "version": report.tool.version, "informationUri": REPO_URL,
                                "rules": rules}},
            "automationDetails": {"id": f"isolab/{report.profile}/"},
            "results": results,
            "properties": {"profile": report.profile, "platform": report.environment.platform,
                           "gatePassed": report.gate.passed},
        }],
    }


def to_console(report: AuditReport) -> str:
    icon = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "error": "ERR ", "skip": "SKIP"}
    lines = [f"cloudaudit {report.tool.version} - profile {report.profile} on {report.environment.platform}", ""]
    by_axis: dict[str, list] = {}
    for r in report.results:
        by_axis.setdefault(BY_ID[r.check_id].axis, []).append(r)
    scores = {s.key: s for s in report.scores.by_axis}
    for axis, results in by_axis.items():
        s = scores[axis]
        pct = "n/a" if s.score is None else f"{s.score * 100:.0f}%"
        lines.append(f"{axis}  coverage {pct}  ({s.evaluated} evaluated, {s.skipped} skipped)")
        for r in results:
            spec = BY_ID[r.check_id]
            flag = " (waived)" if r.waived else ""
            lines.append(f"  {icon[r.status]} {r.check_id:7} {spec.severity:8} {spec.title}{flag}")
            if r.status not in ("pass", "skip"):
                lines.append(f"       {r.message}")
        lines.append("")
    o = report.scores.overall
    lines.append(f"overall coverage {o.score * 100:.0f}%" if o.score is not None else "overall coverage n/a")
    g = report.gate
    lines.append(f"gate (fail on >= {g.fail_on}): {'PASSED' if g.passed else 'FAILED'}"
                 + (f"  blocking: {', '.join(g.blocking)}" if g.blocking else "")
                 + (f"  waived: {', '.join(g.waived)}" if g.waived else "")
                 + (f"  expired waivers: {', '.join(g.expired_waivers)}" if g.expired_waivers else ""))
    return "\n".join(lines)
