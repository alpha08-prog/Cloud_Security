"""Bring the testbed up and down, show its status, and check the host first (doctor)."""

from __future__ import annotations

import re
import socket

from . import compose, cpus, util

PORTS = {"Grafana": 3000, "Prometheus": 9090, "Auditor API": 8088, "tenant-a (insecure only)": 18080}
TEXT_DIRS = ("testbed", "monitor", "auditor", "experiments", "scripts")
TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".js", ".sh", ".toml", ".lock", ".env", ""}

# Provider-side host hardening applied by `up hardened`. Kernel-wide settings in
# the container host (the Docker Desktop VM or the CI runner); they reset when
# Docker Desktop restarts. HV-06 audits them.
HOST_SYSCTLS = {"kernel.kptr_restrict": 1, "kernel.dmesg_restrict": 1}


def doctor() -> bool:
    good = True

    def check(passed: bool, message: str, hint: str = "", soft: bool = False) -> None:
        nonlocal good
        if passed:
            util.ok(message)
        elif soft:
            util.warn(f"{message}{f' - {hint}' if hint else ''}")
        else:
            util.fail(f"{message}{f' - {hint}' if hint else ''}")
            good = False

    try:
        info = util.docker_info()
    except (util.CommandError, FileNotFoundError) as exc:
        util.fail(f"Docker engine not reachable: {exc}")
        util.info("Start Docker Desktop (or the docker service) and re-run.")
        return False
    if info.get("ServerErrors"):
        check(False, f"Docker engine reports errors: {info['ServerErrors']}")
        return False
    check(True, f"Docker engine {info.get('ServerVersion')} on {info.get('OperatingSystem')} "
                f"(kernel {info.get('KernelVersion')})")
    platform = util.detect_platform(info)
    check(True, f"platform: {platform}")

    version = util.docker("compose", "version", "--short", check=False).strip().lstrip("v")
    nums = [int(x) for x in re.findall(r"\d+", version)[:2]] or [0, 0]
    check(tuple(nums) >= (2, 24), f"Docker Compose {version}", "need 2.24 or newer")
    check(str(info.get("CgroupVersion")) == "2", f"cgroup v{info.get('CgroupVersion')} "
          f"({info.get('CgroupDriver')} driver)", "IsoLab needs cgroup v2 for per-tenant pressure (PSI)")
    ncpu = int(info.get("NCPU", 0))
    check(ncpu >= 4, f"{ncpu} logical CPUs, {info.get('MemTotal', 0) / 2**30:.1f} GiB memory",
          "need at least 4 CPUs")
    sec = " ".join(info.get("SecurityOptions") or [])
    check("seccomp" in sec, f"engine security options: {sec or 'none'}", "seccomp should be enabled")

    running = util.docker("ps", "--format", "{{.Names}}\t{{.Label \"com.docker.compose.project\"}}",
                          check=False).splitlines()
    stray = [line.split("\t")[0] for line in running if line and not line.endswith(f"\t{util.PROJECT}")]
    check(not stray, "no unrelated containers running",
          f"stop {', '.join(stray)} or the identification check ID-02 will (correctly) flag them", soft=True)

    if not any(line.endswith(f"\t{util.PROJECT}") for line in running):
        for name, port in PORTS.items():
            check(_port_free(port), f"port {port} free ({name})", "set *_PORT env vars or free the port",
                  soft=port == 18080)

    cr_files = _files_with_cr()
    check(not cr_files, "no CRLF line endings in testbed/monitor/auditor/experiments files",
          f"convert to LF: {', '.join(cr_files[:5])}")

    try:
        placement = cpus.plan(cpus.read_topology())
        env = placement.env()
        check(True, f"CPU plan: provider={env['CPUSET_PROVIDER']} loadgen={env['CPUSET_LOADGEN']} "
                    f"a={env['CPUSET_TENANT_A']} b={env['CPUSET_TENANT_B']} c={env['CPUSET_TENANT_C']} "
                    f"({env['PLACEMENT_NOTES']})")
    except util.CommandError as exc:
        check(False, f"could not read CPU topology: {exc}")
    return good


def _port_free(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) != 0


def _files_with_cr() -> list[str]:
    bad = []
    for d in TEXT_DIRS:
        root = util.REPO / d
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if any(part in {"node_modules", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "secrets"}
                   for part in path.parts):
                continue
            try:
                if b"\r\n" in path.read_bytes():
                    bad.append(str(path.relative_to(util.REPO)))
            except OSError:
                pass
    return bad


def harden_host() -> None:
    script = "; ".join(f"sysctl -w {k}={v}" for k, v in HOST_SYSCTLS.items())
    current = util.docker("run", "--rm", "--label", f"{util.L_PLANE}=operator", util.ALPINE, "sh", "-c",
                          "; ".join(f"sysctl -n {k}" for k in HOST_SYSCTLS)).split()
    if all(int(v) >= want for v, want in zip(current, HOST_SYSCTLS.values(), strict=False)):
        util.ok("host kernel hardening already in place")
        return
    util.info("applying provider host hardening: " + ", ".join(f"{k}={v}" for k, v in HOST_SYSCTLS.items()))
    util.docker("run", "--rm", "--privileged", "--label", f"{util.L_PLANE}=operator", util.ALPINE, "sh", "-c", script)


def up(profile: str, *, build: bool = True) -> None:
    running = compose.current_profile()
    if running and running != profile:
        util.info(f"{running} profile is running; taking it down first")
        down()
    cpus.ensure()
    compose.ensure_secrets()
    if profile == "hardened":
        harden_host()
    if build:
        util.info("building images")
        compose.compose(profile, "build", "--quiet", capture=True, timeout=1200)
    util.info(f"starting the {profile} profile")
    compose.compose(profile, "up", "-d", "--wait", "--wait-timeout", "180", "--remove-orphans", capture=True,
                    timeout=600)
    status()


def down() -> None:
    profile = compose.current_profile()
    if profile:
        compose.compose(profile, "--profile", "noisy", "down", "--volumes", "--remove-orphans", "--timeout", "5",
                        timeout=300)
    else:
        util.run(["docker", "compose", "--project-name", util.PROJECT, "down", "--volumes", "--remove-orphans",
                  "--timeout", "5"], check=False, timeout=300)
    leftovers = util.docker("ps", "-aq", "--filter", f"label=com.docker.compose.project={util.PROJECT}",
                            check=False).split()
    if leftovers:
        util.docker("rm", "-f", *leftovers, check=False)
    util.ok("testbed is down")


def status() -> list[dict]:
    ids = util.docker("ps", "-q", "--filter", f"label=com.docker.compose.project={util.PROJECT}",
                      check=False).split()
    if not ids:
        util.warn("testbed is not running")
        return []
    rows = []
    for c in util.docker_json("inspect", *ids):
        labels = c["Config"]["Labels"] or {}
        hc = c["HostConfig"]
        rows.append({
            "service": labels.get("com.docker.compose.service", c["Name"].lstrip("/")),
            "plane": labels.get(util.L_PLANE, "-"),
            "tenant": labels.get(util.L_TENANT, "-"),
            "state": (c["State"].get("Health") or {}).get("Status") or c["State"]["Status"],
            "cpuset": hc.get("CpusetCpus") or "any",
            "cpus": f"{hc['NanoCpus'] / 1e9:g}" if hc.get("NanoCpus") else "-",
            "mem": f"{hc['Memory'] // 2**20}m" if hc.get("Memory") else "-",
            "user": c["Config"].get("User") or "root",
            "networks": ",".join(n.removeprefix(f"{util.PROJECT}_")
                                 for n in (c["NetworkSettings"]["Networks"] or {})),
        })
    rows.sort(key=lambda r: (r["plane"] != "provider", r["service"]))
    _table(rows)
    profile = compose.current_profile()
    if profile:
        util.info(f"profile: {profile}  |  Grafana http://127.0.0.1:3000  |  Prometheus http://127.0.0.1:9090  "
                  f"|  Auditor http://127.0.0.1:8088/report")
    return rows


def _table(rows: list[dict]) -> None:
    cols = list(rows[0])
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print("  ".join(c.upper().ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r[c]).ljust(widths[c]) for c in cols))
