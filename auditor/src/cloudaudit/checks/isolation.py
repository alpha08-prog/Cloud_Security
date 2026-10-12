"""Isolation (Fig 11 axis): privileges, namespaces and dedicated resources (R2)."""

from __future__ import annotations

from ..host import expand_cpus
from ..policy import Policy
from ..snapshot import Snapshot, service, tenant
from . import WORKLOADS, check, containers, excepted, same_tenant_ref, target


def _caps(values: list[str] | None) -> set[str]:
    return {v.upper().removeprefix("CAP_") for v in values or []}


@check("ISO-01")
def not_privileged(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, WORKLOADS):
        privileged = bool(c["HostConfig"].get("Privileged"))
        out.append(target(c, "fail" if privileged else "pass",
                          "runs privileged" if privileged else "not privileged", {"privileged": privileged}))
    return out


@check("ISO-02")
def capabilities(snap: Snapshot, policy: Policy):
    allow = _caps(policy.capability_allowlist)
    out = []
    for c in containers(snap, policy, WORKLOADS):
        hc = c["HostConfig"]
        dropped, added = _caps(hc.get("CapDrop")), _caps(hc.get("CapAdd"))
        extra = sorted(added - allow)
        if hc.get("Privileged"):
            status, msg = "fail", "privileged: holds every capability"
        elif "ALL" not in dropped:
            status, msg = "fail", "default capability set kept (cap_drop ALL missing)"
        elif extra:
            status, msg = "fail", f"adds capabilities outside the allowlist: {', '.join(extra)}"
        else:
            status, msg = "pass", "all capabilities dropped" + (f"; adds {', '.join(sorted(added))}" if added else "")
        out.append(target(c, status, msg, {"capDrop": sorted(dropped), "capAdd": sorted(added)}))
    return out


@check("ISO-03")
def seccomp_and_nnp(snap: Snapshot, policy: Policy):
    daemon_seccomp = any("seccomp" in o for o in snap.info.get("SecurityOptions") or [])
    out = []
    for c in containers(snap, policy, WORKLOADS):
        opts = [o.replace("=", ":") for o in c["HostConfig"].get("SecurityOpt") or []]
        unconfined = any(o.startswith("seccomp:unconfined") for o in opts) or c["HostConfig"].get("Privileged")
        nnp = any(o in ("no-new-privileges", "no-new-privileges:true") for o in opts)
        problems = []
        if not daemon_seccomp:
            problems.append("engine has seccomp disabled")
        if unconfined:
            problems.append("seccomp unconfined")
        if not nnp:
            problems.append("no-new-privileges not set")
        out.append(target(c, "fail" if problems else "pass", "; ".join(problems) or "seccomp on, no-new-privileges",
                          {"securityOpt": opts, "engineSeccomp": daemon_seccomp}))
    return out


def _is_root(user: str) -> bool:
    name = (user or "").split(":", 1)[0]
    return name in ("", "0", "root")


@check("ISO-04")
def non_root(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, WORKLOADS):
        if t := excepted(c, policy, "ISO-04"):
            out.append(t)
            continue
        user = c["Config"].get("User") or ""
        source = "container"
        if not user:
            user = ((snap.images.get(c.get("Image", "")) or {}).get("Config") or {}).get("User", "")
            source = "image"
        root = _is_root(user)
        out.append(target(c, "fail" if root else "pass", f"runs as {'root' if root else user} ({source} setting)",
                          {"user": user or "root", "source": source}))
    return out


@check("ISO-05")
def private_pid_uts(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, WORKLOADS):
        hc = c["HostConfig"]
        problems = []
        for key, label in (("PidMode", "PID"), ("UTSMode", "UTS")):
            mode = hc.get(key) or ""
            if mode == "host":
                problems.append(f"shares the host {label} namespace")
            elif mode.startswith("container:") and not same_tenant_ref(snap, c, mode):
                problems.append(f"joins another tenant's {label} namespace")
        out.append(target(c, "fail" if problems else "pass", "; ".join(problems) or "private PID and UTS namespaces",
                          {"pidMode": hc.get("PidMode") or "private", "utsMode": hc.get("UTSMode") or "private"}))
    return out


@check("ISO-06")
def resource_limits(snap: Snapshot, policy: Policy):
    swap_supported = not any("swap" in str(w).lower() for w in snap.info.get("Warnings") or [])
    out = []
    for c in containers(snap, policy):
        hc = c["HostConfig"]
        cpu = (hc.get("NanoCpus") or 0) > 0 or (hc.get("CpuQuota") or 0) > 0
        mem = (hc.get("Memory") or 0) > 0
        swap_capped = (hc.get("MemorySwap") or 0) == (hc.get("Memory") or 0) and mem
        pids = (hc.get("PidsLimit") or 0) > 0
        missing = [name for name, ok in (("cpu", cpu), ("memory", mem), ("pids", pids)) if not ok]
        if mem and swap_supported and not swap_capped:
            missing.append("swap (memswap_limit != mem_limit)")
        out.append(target(c, "fail" if missing else "pass",
                          f"no limit on {', '.join(missing)}" if missing else "cpu, memory, swap and pids limited",
                          {"cpus": (hc.get("NanoCpus") or 0) / 1e9, "memoryBytes": hc.get("Memory") or 0,
                           "memorySwapBytes": hc.get("MemorySwap") or 0, "pidsLimit": hc.get("PidsLimit") or 0}))
    return out


@check("ISO-07")
def dedicated_cpusets(snap: Snapshot, policy: Policy):
    tenants = containers(snap, policy)
    sets = {service(c): set(expand_cpus(c["HostConfig"].get("CpusetCpus") or "")) for c in tenants}
    out = []
    for c in tenants:
        mine = sets[service(c)]
        if not mine:
            out.append(target(c, "fail", "no cpuset: may run on any CPU, including other tenants'", {"cpuset": ""}))
            continue
        clashes = sorted({service(o) for o in tenants if tenant(o) != tenant(c) and sets[service(o)] & mine})
        out.append(target(c, "fail" if clashes else "pass",
                          f"cpuset overlaps {', '.join(clashes)}" if clashes else "dedicated cpuset",
                          {"cpuset": c["HostConfig"].get("CpusetCpus"), "overlapsWith": clashes}))
    return out
