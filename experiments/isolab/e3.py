"""E3 - detection validation: does the platform notice isolation-breaking actions,
quickly, attributed to the right tenant, without false alarms?

A quiet window comes first (normal load, no triggers: every detection in it is a
false positive). Then benign triggers - harmless commands with the *shape* of an
isolation-breaking action, the idea behind Falco's event-generator. Latencies are
measured on the VM's clock (engine event time -> detection time).
Protocol: docs/experiments.md (E3).
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

from . import audit, auditor, compose, e1, load, util

QUIET = {"full": 120, "ci": 30}
BOTH = {"insecure": "detect", "hardened": "detect"}

# id, description, rule, expect, expected tenant per profile, SLO (ms), requirements
TRIGGERS = [
    ("T1", "`docker exec` into tenant-a", "DET-01", BOTH, {"insecure": "a", "hardened": "a"}, 5000, ["R4"]),
    ("T2", "Short-lived privileged container (tenant b)", "DET-02", BOTH, {"insecure": "b", "hardened": "b"}, 5000,
     ["R2", "R4"]),
    ("T3", "Short-lived container with the engine socket mounted (tenant c)", "DET-03", BOTH,
     {"insecure": "c", "hardened": "c"}, 5000, ["R4"]),
    ("T4", "Container with no identity labels", "DET-05", BOTH, {"insecure": None, "hardened": None}, 5000, ["R1"]),
    ("T5", "tenant-c attached to a network owned by tenant a", "DET-06", BOTH, {"insecure": None, "hardened": "c"},
     5000, ["R4"]),
    ("T6", "tenant-c contacts the decoy metadata service", "DET-07", BOTH, {"insecure": None, "hardened": "c"}, 5000,
     ["R4", "R1"]),
    ("T7", "Noisy job in tenant b while tenant-a serves traffic", "DET-08",
     {"insecure": "detect", "hardened": "silent"}, {"insecure": "b", "hardened": None}, 90000, ["R3"]),
    ("T8", "Short-lived container joining the host PID namespace (tenant c)", "DET-04", BOTH,
     {"insecure": "c", "hardened": "c"}, 5000, ["R4"]),
]


def catalogue() -> list[dict]:
    return [{"id": i, "description": d, "expectedRule": r, "expect": e, "expectedTenant": t, "sloMs": slo,
             "requirements": req} for i, d, r, e, t, slo, req in TRIGGERS]


def _labels(tenant: str, wid: str) -> list[str]:
    return ["--label", f"{util.L_PLANE}=tenant", "--label", f"{util.L_TENANT}={tenant}",
            "--label", f"{util.L_WORKLOAD}={wid}"]


def _alpine(*args: str) -> None:
    util.run(["docker", "run", "--rm", "--network", "none", *args], timeout=60)


def _fire(trigger: str, profile: str) -> None:
    c = compose.container_name("tenant-c")
    if trigger == "T1":
        util.docker("exec", compose.container_name("tenant-a"), "true")
    elif trigger == "T2":
        _alpine("--privileged", *_labels("b", "e3-t2"), util.ALPINE, "sleep", "3")
    elif trigger == "T3":
        _alpine("-v", "/var/run/docker.sock:/var/run/docker.sock:ro", *_labels("c", "e3-t3"), util.ALPINE, "sleep", "3")
    elif trigger == "T4":
        _alpine(util.ALPINE, "sleep", "3")
    elif trigger == "T5":
        net = f"{util.PROJECT}_e3-net-a"
        util.docker("network", "create", "--internal", "--label", f"{util.L_PLANE}=tenant",
                    "--label", f"{util.L_TENANT}=a", net)
        try:
            util.docker("network", "connect", net, c)
            time.sleep(1)
            util.docker("network", "disconnect", net, c)
        finally:
            util.docker("network", "rm", net, check=False)
    elif trigger == "T6":
        provider = compose.network_name("provider-net")
        attached = provider in util.docker("inspect", "-f", "{{json .NetworkSettings.Networks}}", c)
        if not attached:
            util.docker("network", "connect", provider, c)
        try:
            util.docker("exec", c, "python", "-c",
                        "import urllib.request\n"
                        "try: urllib.request.urlopen('http://metadata:8080/latest/meta-data/', timeout=3)\n"
                        "except Exception: pass")
        finally:
            if not attached:
                util.docker("network", "disconnect", provider, c, check=False)
    elif trigger == "T8":
        _alpine("--pid", "host", *_labels("c", "e3-t8"), util.ALPINE, "sleep", "3")


def _wait_for(rule: str, since: int, timeout_s: float) -> dict | None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        hits = [d for d in auditor.detections(since) if d["rule"] == rule]
        if hits:
            return hits[0]
        time.sleep(0.5)
    return None


def run(profile: str, variant: str = "full", out: Path | None = None) -> dict:
    audit.require_running(profile)
    load.build()
    auditor.wait_ready()
    e1.stop_noise(profile)
    time.sleep(5)  # let the startup events of the testbed settle

    # Quiet window under normal load: every detection here is a false positive.
    quiet = QUIET[variant]
    util.info(f"E3 {profile}: quiet window {quiet}s under 20 req/s")
    t_quiet = auditor.server_now_ns()
    bg = load.start_k6(profile, 20, quiet)
    bg.wait()
    false_positives = [{"profile": profile, "rule": d["rule"], "tenant": d["tenant"], "message": d["message"]}
                       for d in auditor.detections(t_quiet)]
    for fp in false_positives:
        util.fail(f"false positive in quiet window: {fp['rule']} {fp['message']}")

    results = []
    for t in catalogue():
        expect = t["expect"][profile]
        since = auditor.server_now_ns()
        bg = None
        if t["id"] == "T7":
            bg = load.start_k6(profile, 20, 110)
            time.sleep(5)
            e1.start_noise(profile, 100)
        else:
            _fire(t["id"], profile)
        wait_s = t["sloMs"] / 1000 + (5 if t["id"] == "T7" else 3)
        hit = _wait_for(t["expectedRule"], since, wait_s)
        if t["id"] == "T7":
            e1.stop_noise(profile)
            if bg:
                bg.terminate()
                util.docker("rm", "-f", "isolab-loadgen-bg", check=False)
        detected = hit is not None
        if expect == "silent":
            if detected:
                false_positives.append({"profile": profile, "rule": hit["rule"], "tenant": hit["tenant"],
                                        "message": hit["message"]})
            outcome = {"profile": profile, "triggerId": t["id"], "expected": expect, "detected": detected,
                       "rule": hit["rule"] if hit else None, "tenant": hit["tenant"] if hit else None,
                       "latencyMs": None, "withinSlo": not detected, "attributionCorrect": None,
                       "asExpected": not detected}
        else:
            latency = hit["latencyMs"] if hit else None
            attributed = hit is not None and hit["tenant"] == t["expectedTenant"][profile]
            outcome = {"profile": profile, "triggerId": t["id"], "expected": expect, "detected": detected,
                       "rule": hit["rule"] if hit else None, "tenant": hit["tenant"] if hit else None,
                       "latencyMs": latency, "withinSlo": detected and latency <= t["sloMs"],
                       "attributionCorrect": attributed if hit else False,
                       "asExpected": detected and latency <= t["sloMs"] and attributed}
        results.append(outcome)
        mark = util.ok if outcome["asExpected"] else util.fail
        what = "silent as expected" if expect == "silent" and not detected else (
            f"{outcome['rule']} in {outcome['latencyMs']} ms, tenant {outcome['tenant']}" if detected else "MISSED")
        mark(f"{t['id']} {t['description']}: {what}")
        time.sleep(2)

    doc = {"profile": profile, "variant": variant, "quietWindowSeconds": quiet, "results": results,
           "falsePositives": false_positives, "environment": e1.environment()}
    doc["summary"] = [summary_for(profile, results, false_positives)]
    util.write_json(audit.run_dir(profile, out) / "e3.json", doc)
    s = doc["summary"][0]
    util.info(f"E3 {profile}: detected {s['detected']}/{s['expected']}, false positives {s['falsePositives']}, "
              f"median latency {s['medianLatencyMs']} ms")
    return doc


def summary_for(profile: str, results: list[dict], false_positives: list[dict]) -> dict:
    rs = [r for r in results if r["profile"] == profile and r["expected"] == "detect"]
    latencies = [r["latencyMs"] for r in rs if r["latencyMs"] is not None]
    attributed = [r["attributionCorrect"] for r in rs if r["detected"]]
    detected = sum(r["detected"] and r["withinSlo"] for r in rs)
    return {
        "profile": profile,
        "detectionRate": round(detected / len(rs), 4) if rs else 0.0,
        "detected": detected,
        "expected": len(rs),
        "falsePositives": sum(fp["profile"] == profile for fp in false_positives),
        "medianLatencyMs": round(statistics.median(latencies), 1) if latencies else None,
        "maxLatencyMs": round(max(latencies), 1) if latencies else None,
        "attributionAccuracy": round(sum(attributed) / len(attributed), 4) if attributed else None,
    }


DEMOS = {"exec": "T1", "privileged": "T2", "socket": "T3", "unlabelled": "T4", "drift": "T5", "canary": "T6",
         "noisy": "T7", "hostpid": "T8"}


def demo(name: str) -> int:
    """One trigger, live, for a demo: fire it and print the detection the auditor raises."""
    profile = compose.current_profile()
    if not profile:
        raise util.CommandError("the testbed is not running")
    t = next(x for x in catalogue() if x["id"] == DEMOS[name])
    util.info(f"{profile}: {t['description']} (expect {t['expectedRule']}: {t['expect'][profile]})")
    since = auditor.server_now_ns()
    if t["id"] == "T7":
        load.build()
        bg = load.start_k6(profile, 20, 110)
        time.sleep(5)
        e1.start_noise(profile, 100)
        util.info("noisy job running; watch Grafana (http://127.0.0.1:3000) - DET-08 needs 30 s of sustained "
                  "unfair use")
    else:
        _fire(t["id"], profile)
    hit = _wait_for(t["expectedRule"], since, t["sloMs"] / 1000 + 5)
    if t["id"] == "T7":
        e1.stop_noise(profile)
        bg.terminate()
        util.docker("rm", "-f", "isolab-loadgen-bg", check=False)
    for d in auditor.detections(since):
        util.ok(f"{d['rule']} {d['severity']} tenant={d['tenant']} service={d['service']} "
                f"latency={d['latencyMs']} ms: {d['message']}")
    if hit is None:
        (util.ok if t["expect"][profile] == "silent" else util.fail)(
            f"no {t['expectedRule']} raised" + (" - as expected for this profile" if t["expect"][profile] == "silent"
                                                 else ""))
    return 0
