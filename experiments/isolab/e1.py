"""E1 - noisy neighbour: does one tenant's CPU burn break another tenant's latency SLO?

Protocol and pre-registered hypotheses: docs/experiments.md (E1). One call runs
every arm for ONE profile (the testbed can only run one profile at a time) and
writes results/runs/<platform>/<profile>/e1.json; `lab.py publish` merges both
profiles and evaluates the hypotheses.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from . import audit, auditor, compose, cpus, load, util

VARIANTS = {
    #           rate, warmup, measure, reps, cooldown
    "full": dict(rate=50, warmup=15, measure=90, reps=3, cooldown=30),
    "ci": dict(rate=20, warmup=5, measure=30, reps=1, cooldown=5),
}
SLO_P99_MS = 25.0
JOB = "tenant-b-job"


def min_noisy_cores(profile: str) -> float:
    """The noise counts as real if tenant-b used at least 1 core, or 80% of its CPU quota
    when the hardened profile caps it lower than that (small CI runners)."""
    if profile == "hardened":
        return min(1.0, 0.8 * float(cpus.ensure().get("CPUS_TENANT_B", "1")))
    return 1.0


def start_noise(profile: str, seconds: int) -> None:
    compose.compose(profile, "--profile", "noisy", "up", "-d", "--no-deps", "--force-recreate", JOB,
                    extra_env={"STRESS_TIMEOUT": str(seconds)}, timeout=120)


def stop_noise(profile: str) -> None:
    compose.compose(profile, "--profile", "noisy", "rm", "--stop", "--force", JOB, check=False, timeout=120)


def _percentiles(values: dict | None) -> dict | None:
    if not values:
        return None
    return {"avg": values["avg"], "min": values["min"], "med": values["med"], "p90": values["p(90)"],
            "p95": values["p(95)"], "p99": values["p(99)"], "max": values["max"]}


def one_run(profile: str, arm: str, rep: int, cfg: dict) -> dict:
    window = cfg["warmup"] + cfg["measure"]
    started = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    if arm == "noisy":
        start_noise(profile, window + 20)
        time.sleep(3)  # let stress-ng spin up before the warm-up starts
    util.info(f"E1 {profile} {arm} rep {rep}: {cfg['rate']} req/s, {cfg['warmup']}s warm-up + "
              f"{cfg['measure']}s measured")
    try:
        k6 = load.run_k6(profile, cfg["rate"], cfg["warmup"], cfg["measure"])
        # Queries cover the measurement window that just ended (Prometheus' own clock).
        span = f"{cfg['measure']}s"
        time.sleep(6)  # one more scrape so the window's last samples are in
        noisy_cores = load.prom_scalar(
            f'sum(rate(cloudaudit_tenant_cpu_seconds_total{{plane="tenant",tenant="b"}}[{span}]))')
        pressure = load.prom_scalar(
            f'rate(cloudaudit_tenant_pressure_waiting_seconds_total{{service="tenant-a",resource="cpu"}}[{span}])')
        throttled = load.prom_by(
            f'sum by (tenant) (increase(cloudaudit_tenant_cpu_throttled_seconds_total{{plane="tenant"}}[{span}]))',
            "tenant")
    finally:
        if arm == "noisy":
            stop_noise(profile)
    reasons = []
    if k6["droppedIterations"]:
        reasons.append(f"{k6['droppedIterations']} dropped iterations")
    if k6["failedRate"] > 0.01:
        reasons.append(f"{k6['failedRate']:.1%} failed requests")
    if arm == "noisy" and (noisy_cores or 0) < min_noisy_cores(profile):
        reasons.append(f"noise did not happen (tenant-b used {noisy_cores or 0:.2f} cores)")
    run = {
        "profile": profile, "arm": arm, "repetition": rep, "startedAt": started,
        "latencyMs": _percentiles(k6["latencyMs"]),
        "serverWorkMs": _percentiles(k6.get("serverWorkMs")),
        "failedRate": k6["failedRate"], "droppedIterations": int(k6["droppedIterations"]),
        "iterations": int(k6["iterations"]),
        "noisyCoresUsed": round(noisy_cores, 3) if noisy_cores is not None else None,
        "victimCpuPressurePct": round(pressure * 100, 2) if pressure is not None else None,
        "throttledSeconds": {k or "?": round(v, 3) for k, v in throttled.items()},
        "valid": not reasons, "invalidReason": "; ".join(reasons) or None,
    }
    p = run["latencyMs"]
    util.ok(f"   p50 {p['med']:.1f} ms  p99 {p['p99']:.1f} ms  tenant-b {run['noisyCoresUsed']} cores  "
            f"victim CPU pressure {run['victimCpuPressurePct']}%" + ("" if run["valid"] else
                                                                       f"  INVALID: {run['invalidReason']}"))
    return run


def run(profile: str, variant: str = "full", out: Path | None = None) -> dict:
    audit.require_running(profile)
    cfg = VARIANTS[variant]
    load.build()
    auditor.wait_ready()
    stop_noise(profile)
    since = auditor.server_now_ns()
    runs = []
    for rep in range(1, cfg["reps"] + 1):
        # Interleave arm order across repetitions so drift (thermals, background load) hits both arms.
        arms = ["baseline", "noisy"] if rep % 2 else ["noisy", "baseline"]
        for arm in arms:
            runs.append(one_run(profile, arm, rep, cfg))
            time.sleep(cfg["cooldown"])
    dets = [d for d in auditor.detections(since) if d["rule"] == "DET-08"]
    env = cpus.ensure()
    doc = {
        "profile": profile, "variant": variant,
        "config": {"ratePerSecond": cfg["rate"], "warmupSeconds": cfg["warmup"], "measureSeconds": cfg["measure"],
                   "repetitions": cfg["reps"], "stressWorkers": int(env["STRESS_WORKERS"]),
                   "workIterations": work_iterations(), "sloP99Ms": SLO_P99_MS},
        "runs": runs,
        "noisyNeighbourDetections": len(dets),
        "environment": environment(),
    }
    util.write_json(audit.run_dir(profile, out) / "e1.json", doc)
    return doc


def work_iterations() -> int:
    env = (compose.inspect("tenant-a") or {}).get("Config", {}).get("Env") or []
    return int(next((e.split("=", 1)[1] for e in env if e.startswith("WORK_ITERATIONS=")), "0"))


def environment() -> dict:
    info = util.docker_info()
    env = cpus.ensure()
    return {
        "platform": util.detect_platform(info),
        "dockerServerVersion": str(info.get("ServerVersion")),
        "kernelVersion": str(info.get("KernelVersion")),
        "logicalCpus": int(info.get("NCPU", 0)),
        "physicalCores": int(env.get("PHYSICAL_CORES", 0)),
        "gitSha": util.git_sha(),
        "placement": {k: env[k] for k in ("CPUSET_PROVIDER", "CPUSET_LOADGEN", "CPUSET_TENANT_A", "CPUSET_TENANT_B",
                                          "CPUSET_TENANT_C", "PLACEMENT_NOTES")},
    }
