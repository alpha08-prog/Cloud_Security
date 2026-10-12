"""Read-only facts about the container host: the shared kernel and CPU.

All paths are resolved under an injectable root so tests can point at a fake
sysfs/procfs tree. Inside the auditor container `/sys` and `/proc/sys` already
show the host kernel's global settings; per-container cgroups come from the
read-only mount at CGROUP_ROOT.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

SYSCTLS = (
    "kernel.unprivileged_bpf_disabled",
    "kernel.kptr_restrict",
    "kernel.dmesg_restrict",
    "kernel.perf_event_paranoid",
)


class HostFacts(BaseModel):
    smt_control: str | None = None
    smt_active: bool | None = None
    cores: list[list[int]] = Field(default_factory=list, description="physical cores as SMT sibling groups")
    vulnerabilities: dict[str, str] = Field(default_factory=dict)
    ksm_run: int | None = None
    sysctls: dict[str, int | None] = Field(default_factory=dict)
    psi_host: bool = False
    cgroup_mount: bool = False


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def expand_cpus(spec: str) -> list[int]:
    cpus: list[int] = []
    for part in (spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            cpus.extend(range(int(lo), int(hi) + 1))
        else:
            cpus.append(int(part))
    return cpus


def collect(root: str = "/", cgroup_root: str = "/host/cgroup") -> HostFacts:
    r = Path(root)
    cpu = r / "sys/devices/system/cpu"
    facts = HostFacts()
    facts.smt_control = _read(cpu / "smt/control")
    active = _read(cpu / "smt/active")
    facts.smt_active = None if active is None else active == "1"

    groups: dict[tuple[int, ...], None] = {}
    for c in sorted(cpu.glob("cpu[0-9]*"), key=lambda p: int(p.name[3:])):
        siblings = _read(c / "topology/thread_siblings_list")
        groups[tuple(expand_cpus(siblings) if siblings else [int(c.name[3:])])] = None
    facts.cores = [list(g) for g in sorted(groups, key=lambda g: g[0])]

    for f in sorted((cpu / "vulnerabilities").glob("*")):
        value = _read(f)
        if value is not None:
            facts.vulnerabilities[f.name] = value

    ksm = _read(r / "sys/kernel/mm/ksm/run")
    facts.ksm_run = int(ksm) if ksm and ksm.isdigit() else None

    for name in SYSCTLS:
        value = _read(r / "proc/sys" / name.replace(".", "/"))
        facts.sysctls[name] = int(value) if value is not None and value.lstrip("-").isdigit() else None

    facts.psi_host = _read(r / "proc/pressure/cpu") is not None
    facts.cgroup_mount = (Path(cgroup_root) / "cgroup.controllers").exists()
    return facts
