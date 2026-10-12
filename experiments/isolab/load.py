"""The k6 load generator (operator plane), and the Prometheus queries E1 needs."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
import urllib.request

from . import compose, cpus, util

IMAGE = "isolab/loadgen:local"
PROMETHEUS = f"http://127.0.0.1:{os.environ.get('PROMETHEUS_PORT', '9090')}"


def build() -> None:
    util.run(["docker", "build", "--quiet", "-t", IMAGE, "--build-arg", f"GIT_SHA={util.git_sha()}",
              "-f", str(util.TESTBED / "images" / "loadgen" / "Dockerfile"), str(util.TESTBED / "images")],
             timeout=600)


def victim_network(profile: str) -> str:
    """The network the load generator joins to reach tenant-a, as a client would."""
    return compose.network_name("net-a" if profile == "hardened" else "ops-net")


def k6_cmd(profile: str, rate: int, warmup: int, duration: int, name: str) -> list[str]:
    env = cpus.ensure()
    return [
        "docker", "run", "--rm", "--name", name,
        "--network", victim_network(profile),
        # Fairness control: the measuring instrument gets its own physical core and the
        # maximum CPU weight in every arm, so it is never the thing being starved.
        "--cpuset-cpus", env["CPUSET_LOADGEN"], "--cpu-shares", "262144",
        "--label", f"{util.L_PLANE}=operator", "--label", f"{util.L_WORKLOAD}=operator-loadgen",
        IMAGE, "run", "--quiet", "--no-color",
        "-e", "TARGET=http://tenant-a:8080/work", "-e", f"RATE={rate}",
        "-e", f"WARMUP={warmup}s", "-e", f"DURATION={duration}s",
        "/scripts/payments.js",
    ]


def run_k6(profile: str, rate: int, warmup: int, duration: int, name: str = "isolab-loadgen") -> dict:
    proc = util.run(k6_cmd(profile, rate, warmup, duration, name), timeout=warmup + duration + 120)
    line = next((ln for ln in reversed(proc.stdout.splitlines()) if ln.startswith("{")), None)
    if line is None:
        raise util.CommandError(f"k6 produced no summary:\n{proc.stdout[-500:]}\n{proc.stderr[-500:]}")
    return json.loads(line)


def start_k6(profile: str, rate: int, duration: int, name: str = "isolab-loadgen-bg") -> subprocess.Popen:
    return subprocess.Popen(k6_cmd(profile, rate, 1, duration, name), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def prom_query(expr: str) -> list[dict]:
    url = f"{PROMETHEUS}/api/v1/query?{urllib.parse.urlencode({'query': expr})}"
    with urllib.request.urlopen(url, timeout=10) as r:
        doc = json.load(r)
    return doc.get("data", {}).get("result", [])


def prom_scalar(expr: str) -> float | None:
    result = prom_query(expr)
    return float(result[0]["value"][1]) if result else None


def prom_by(expr: str, label: str) -> dict[str, float]:
    return {r["metric"].get(label, ""): float(r["value"][1]) for r in prom_query(expr)}
