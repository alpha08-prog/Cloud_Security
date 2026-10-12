"""Hypervisor vulnerabilities (Fig 11 axis). In a container cloud the 'hypervisor' is
the engine plus the shared kernel; these checks look at both (R2, R3)."""

from __future__ import annotations

import re

from ..policy import Policy
from ..snapshot import Snapshot
from . import TENANT, WORKLOADS, check, containers, excepted, host_target, target


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text)[:3])


@check("HV-01")
def engine_api_not_exposed(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, WORKLOADS):
        if t := excepted(c, policy, "HV-01"):
            out.append(t)
            continue
        sockets = [m.get("Source") or m.get("Destination") for m in c.get("Mounts") or []
                   if any(s in (m.get("Source") or "") or s in (m.get("Destination") or "")
                          for s in policy.engine_sockets)]
        docker_host = [e.split("=", 1)[0] for e in c["Config"].get("Env") or [] if e.startswith("DOCKER_HOST=")]
        exposed = sockets or docker_host
        out.append(target(c, "fail" if exposed else "pass",
                          f"engine socket mounted: {', '.join(sockets or docker_host)}" if exposed
                          else "no engine socket", {"sockets": sockets}))
    return out


@check("HV-02")
def patch_baseline(snap: Snapshot, policy: Policy):
    server = snap.version.get("Version") or snap.info.get("ServerVersion") or ""
    kernel = snap.info.get("KernelVersion") or ""
    problems = []
    if _version(server) < _version(policy.min_versions.docker_server):
        problems.append(f"engine {server} < {policy.min_versions.docker_server}")
    if _version(kernel) < _version(policy.min_versions.kernel):
        problems.append(f"kernel {kernel} < {policy.min_versions.kernel}")
    return [host_target("fail" if problems else "pass", "; ".join(problems) or "engine and kernel at baseline",
                        {"engine": server, "kernel": kernel, "minEngine": policy.min_versions.docker_server,
                         "minKernel": policy.min_versions.kernel})]


@check("HV-03")
def cpu_mitigations(snap: Snapshot, policy: Policy):
    vulns = snap.host.vulnerabilities
    if not vulns:
        return [host_target("skip", "kernel exposes no CPU vulnerability status")]
    vulnerable = {k: v for k, v in vulns.items() if v.lower().startswith("vulnerable")}
    unknown = {k: v for k, v in vulns.items() if v.lower().startswith("unknown")}
    if vulnerable:
        status, msg = "fail", "vulnerable: " + ", ".join(f"{k} ({v})" for k, v in vulnerable.items())
    elif unknown:
        status, msg = "warn", "mitigation state unknown: " + ", ".join(unknown)
    else:
        status, msg = "pass", f"all {len(vulns)} known CPU flaws mitigated or not applicable"
    return [host_target(status, msg, {"vulnerable": sorted(vulnerable), "unknown": sorted(unknown),
                                      "checked": len(vulns)})]


@check("HV-04")
def user_namespaces(snap: Snapshot, policy: Policy):
    opts = " ".join(snap.info.get("SecurityOptions") or [])
    on = "name=userns" in opts or "name=rootless" in opts
    return [host_target("pass" if on else "fail",
                        "user namespaces remap container root" if on else "container root is host root (no userns)",
                        {"securityOptions": snap.info.get("SecurityOptions") or []})]


@check("HV-05")
def mandatory_access_control(snap: Snapshot, policy: Policy):
    opts = " ".join(snap.info.get("SecurityOptions") or [])
    has_apparmor, has_selinux = "apparmor" in opts, "selinux" in opts
    out = []
    for c in containers(snap, policy, TENANT):
        if not (has_apparmor or has_selinux):
            out.append(target(c, "skip", "host has no AppArmor or SELinux"))
            continue
        profile = c.get("AppArmorProfile") or ""
        label = c.get("ProcessLabel") or ""
        confined = (has_apparmor and profile not in ("", "unconfined")) or (has_selinux and bool(label))
        out.append(target(c, "pass" if confined else "fail",
                          f"confined by {profile or label}" if confined else "no MAC profile (unconfined)",
                          {"appArmorProfile": profile or None, "selinuxLabel": label or None}))
    return out


@check("HV-06")
def kernel_hardening(snap: Snapshot, policy: Policy):
    weak = {}
    for name, minimum in policy.sysctls.items():
        value = snap.host.sysctls.get(name)
        if value is None or value < minimum:
            weak[name] = value
    evidence = {k: snap.host.sysctls.get(k) for k in policy.sysctls}
    if weak:
        return [host_target("fail", "below policy: " + ", ".join(f"{k}={v}" for k, v in weak.items()), evidence)]
    return [host_target("pass", "kernel hardening settings meet policy", evidence)]
