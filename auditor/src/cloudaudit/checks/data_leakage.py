"""Data leakage (Fig 11 axis): storage, IPC and secrets crossing tenant boundaries."""

from __future__ import annotations

import posixpath
import re
from collections import defaultdict

from ..models import Target
from ..policy import Policy
from ..snapshot import Snapshot, service, tenant
from . import TENANT, WORKLOADS, check, containers, same_tenant_ref, target


def _sensitive(source: str, sensitive: list[str]) -> bool:
    src = posixpath.normpath(source or "/")
    for p in sensitive:
        p = posixpath.normpath(p)
        # the path itself, anything under it, or a parent of it (mounting / exposes /etc too)
        if src == p or src.startswith(p + "/") or p.startswith(src.rstrip("/") + "/") or src == "/":
            return True
    return False


@check("DL-01")
def host_mounts(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, TENANT):
        binds = [m for m in c.get("Mounts") or [] if m.get("Type") == "bind"]
        if not binds:
            out.append(target(c, "pass", "no host bind mounts", {"binds": []}))
            continue
        bad = [m["Source"] for m in binds if _sensitive(m.get("Source", ""), policy.sensitive_paths)]
        writable = [m["Source"] for m in binds if m.get("RW")]
        if bad or writable:
            parts = []
            if bad:
                parts.append(f"sensitive host paths: {', '.join(bad)}")
            if writable:
                parts.append(f"writable host paths: {', '.join(writable)}")
            status, msg = "fail", "; ".join(parts)
        else:
            status, msg = "warn", "read-only host bind mounts (prefer volumes)"
        out.append(target(c, status, msg, {"binds": [m.get("Source", "") for m in binds]}))
    return out


@check("DL-02")
def no_shared_storage(snap: Snapshot, policy: Policy):
    users: dict[str, set[str]] = defaultdict(set)
    kinds: dict[str, str] = {}
    for c in containers(snap, policy, TENANT):
        owner = tenant(c) or f"unlabelled:{service(c)}"
        for m in c.get("Mounts") or []:
            if m.get("Type") == "volume":
                key = m.get("Name", "")
                kinds[key] = "volume"
            elif m.get("Type") == "bind":
                key = m.get("Source", "")
                kinds[key] = "bind"
            else:
                continue
            users[key].add(owner)
    out: list[Target] = []
    for key, owners in sorted(users.items()):
        ref = key.removeprefix("isolab_") if kinds[key] == "volume" else key
        shared = len(owners) > 1
        out.append(Target(kind="volume", ref=ref, status="fail" if shared else "pass",
                          message=f"shared by tenants {', '.join(sorted(owners))}" if shared
                          else f"used by one tenant ({next(iter(owners))})",
                          evidence={"type": kinds[key], "tenants": sorted(owners)}))
    return out


@check("DL-03")
def no_shared_ipc(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, TENANT):
        mode = c["HostConfig"].get("IpcMode") or "private"
        if mode == "host":
            status, msg = "fail", "shares the host IPC namespace"
        elif mode.startswith("container:"):
            ok = same_tenant_ref(snap, c, mode)
            status, msg = ("pass", "shares IPC within its own tenant") if ok else ("fail", "joins another tenant's IPC")
        elif mode == "shareable":
            status, msg = "warn", "IPC namespace is shareable"
        else:
            status, msg = "pass", f"{mode} IPC namespace"
        out.append(target(c, status, msg, {"ipcMode": mode}))
    return out


@check("DL-04")
def read_only_rootfs(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, WORKLOADS):
        ro = bool(c["HostConfig"].get("ReadonlyRootfs"))
        message = "read-only root filesystem" if ro else "writable root filesystem"
        out.append(target(c, "pass" if ro else "fail", message, {"readOnlyRootfs": ro}))
    return out


@check("DL-05")
def no_secret_env(snap: Snapshot, policy: Policy):
    pattern = re.compile(policy.secret_env_pattern, re.IGNORECASE)
    out = []
    for c in containers(snap, policy, TENANT):
        names = [e.split("=", 1)[0] for e in c["Config"].get("Env") or []]
        hits = sorted(n for n in names if pattern.search(n))
        out.append(target(c, "fail" if hits else "pass",
                          f"secret-like variables: {', '.join(hits)}" if hits else "no secret-like variable names",
                          {"variables": hits}))  # names only, never values
    return out
