"""Shared helpers for the IsoLab orchestrator. Standard library only.

Everything shells out to the `docker` CLI with argument lists (never a shell
string), which keeps Windows/Git Bash path mangling out of the picture and makes
the same code work on the laptop and in CI.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTBED = REPO / "testbed"
RESULTS = REPO / "results"
RUNS = RESULTS / "runs"
PUBLISHED = RESULTS / "published"
PROJECT = "isolab"
PROFILES = ("insecure", "hardened")

# Small helper image for host reads (topology, sysctls) and benign triggers.
ALPINE = "alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc"

# Labels used everywhere (see CLAUDE.md conventions).
L_PLANE = "io.isolab.plane"
L_TENANT = "io.isolab.tenant"
L_OWNER = "io.isolab.owner"
L_WORKLOAD = "io.isolab.workload-id"


def operator_labels(name: str) -> list[str]:
    """Identity for the orchestrator's own short-lived helper containers (R1 applies to us too)."""
    return ["--label", f"{L_PLANE}=operator", "--label", f"{L_WORKLOAD}=operator-{name}"]

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def info(msg: str) -> None:
    print(_c("36", "»"), msg, flush=True)


def ok(msg: str) -> None:
    print(_c("32", "✔"), msg, flush=True)


def warn(msg: str) -> None:
    print(_c("33", "!"), msg, flush=True)


def fail(msg: str) -> None:
    print(_c("31", "✘"), msg, flush=True)


class CommandError(RuntimeError):
    pass


def run(cmd: list[str], *, check: bool = True, capture: bool = True, env: dict | None = None,
        timeout: float | None = None, input: str | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    proc = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=full_env,
        timeout=timeout,
        input=input,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip() if capture else ""
        raise CommandError(f"{' '.join(cmd[:6])}… exited {proc.returncode}\n{detail}")
    return proc


def docker(*args: str, check: bool = True, timeout: float | None = None) -> str:
    return run(["docker", *args], check=check, timeout=timeout).stdout


def docker_json(*args: str) -> object:
    return json.loads(docker(*args))


def docker_info() -> dict:
    return docker_json("info", "--format", "{{json .}}")


def detect_platform(info_doc: dict | None = None) -> str:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-ubuntu"
    info_doc = info_doc or docker_info()
    if "Docker Desktop" in str(info_doc.get("OperatingSystem", "")):
        return "docker-desktop-wsl2" if "WSL2" in str(info_doc.get("KernelVersion", "")) else "docker-desktop"
    return "linux"


def git_sha() -> str:
    try:
        return run(["git", "-C", str(REPO), "rev-parse", "--short=12", "HEAD"]).stdout.strip()
    except (CommandError, FileNotFoundError):
        return "dev"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_docker_time(value: str) -> float:
    """Docker's RFC 3339 timestamps with nanoseconds -> epoch seconds (float)."""
    value = value.strip().replace("Z", "+00:00")
    if "." in value:
        head, rest = value.split(".", 1)
        frac, tz = rest, ""
        for sep in ("+", "-"):
            if sep in rest:
                frac, tz = rest.split(sep, 1)
                tz = sep + tz
                break
        value = f"{head}.{frac[:6]}{tz}"
    return datetime.fromisoformat(value).timestamp()


def write_json(path: Path, doc: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def wait_until(predicate, timeout: float, interval: float = 1.0, what: str = "condition"):
    deadline = time.monotonic() + timeout
    while True:
        result = predicate()
        if result:
            return result
        if time.monotonic() > deadline:
            raise TimeoutError(f"timed out after {timeout:.0f}s waiting for {what}")
        time.sleep(interval)


def host_os() -> str:
    return f"{platform.system()} {platform.release()}"
