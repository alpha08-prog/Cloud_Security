"""Cross-VM (cross-tenant) attacks (Fig 11 axis): every path one tenant could use to
reach another - shared networks, the host's network, published ports, shared
physical cores, merged memory pages - plus the live tripwires that watch for attempts."""

from __future__ import annotations

from collections import defaultdict

from ..host import expand_cpus
from ..models import Target
from ..policy import Policy
from ..snapshot import Snapshot, service, short_network, tenant
from . import TENANT, WORKLOADS, check, containers, host_target, same_tenant_ref, target


def _networks_of(c: dict) -> list[str]:
    return list((c.get("NetworkSettings") or {}).get("Networks") or {})


@check("XVM-01")
def no_shared_tenant_network(snap: Snapshot, policy: Policy):
    members: dict[str, set[str]] = defaultdict(set)
    for c in containers(snap, policy, TENANT):
        for net in _networks_of(c):
            members[net].add(tenant(c) or f"unlabelled:{service(c)}")
    out: list[Target] = []
    for net, tenants in sorted(members.items()):
        shared = len(tenants) > 1
        out.append(Target(kind="network", ref=short_network(net), status="fail" if shared else "pass",
                          message=f"tenants {', '.join(sorted(tenants))} share this network" if shared
                          else f"single tenant ({next(iter(tenants))})",
                          evidence={"tenants": sorted(tenants)}))
    return out


@check("XVM-02")
def internal_tenant_networks(snap: Snapshot, policy: Policy):
    by_name = {n["Name"]: n for n in snap.networks}
    used: dict[str, set[str]] = defaultdict(set)
    for c in containers(snap, policy, TENANT):
        for net in _networks_of(c):
            used[net].add(service(c))
    out: list[Target] = []
    for net, services in sorted(used.items()):
        doc = by_name.get(net, {})
        if net == "bridge":
            status, msg = "fail", "tenant attached to the engine's default bridge"
        elif doc.get("Internal"):
            status, msg = "pass", "internal network (no egress)"
        else:
            status, msg = "fail", "routable network: tenants can reach the outside and the host"
        out.append(Target(kind="network", ref=short_network(net), status=status, message=msg,
                          evidence={"internal": bool(doc.get("Internal")), "attached": sorted(services)}))
    return out


@check("XVM-03")
def no_host_network(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, WORKLOADS):
        mode = c["HostConfig"].get("NetworkMode") or ""
        if mode == "host":
            status, msg = "fail", "uses the host network stack"
        elif mode.startswith("container:") and not same_tenant_ref(snap, c, mode):
            status, msg = "fail", "joins another tenant's network namespace"
        else:
            status, msg = "pass", f"own network namespace ({mode or 'default'})"
        out.append(target(c, status, msg, {"networkMode": mode}))
    return out


@check("XVM-04")
def no_published_ports(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, TENANT):
        bindings = c["HostConfig"].get("PortBindings") or {}
        published = [f"{(b or {}).get('HostIp') or '0.0.0.0'}:{(b or {}).get('HostPort')}->{port}"
                     for port, binds in bindings.items() for b in (binds or [])]
        lan = any(p.startswith(("0.0.0.0", "::", ":")) for p in published)
        if published:
            msg = f"publishes {', '.join(published)}" + (" (reachable from the LAN)" if lan else "")
        else:
            msg = "publishes no host ports"
        out.append(target(c, "fail" if published else "pass", msg, {"published": published}))
    return out


@check("XVM-05")
def smt_aware_placement(snap: Snapshot, policy: Policy):
    cores = snap.host.cores
    if snap.host.smt_active is False or not cores or all(len(core) == 1 for core in cores):
        return [host_target("pass", "SMT inactive: no hardware threads shared between tenants",
                            {"smtActive": snap.host.smt_active})]
    all_cpus = {cpu for core in cores for cpu in core}
    core_of = {cpu: i for i, core in enumerate(cores) for cpu in core}
    by_tenant: dict[str, set[int]] = defaultdict(set)
    for c in containers(snap, policy, TENANT):
        cpus = set(expand_cpus(c["HostConfig"].get("CpusetCpus") or "")) or all_cpus
        by_tenant[tenant(c) or f"unlabelled:{service(c)}"] |= {core_of[x] for x in cpus if x in core_of}
    shared = defaultdict(list)
    for t, tcores in by_tenant.items():
        for core in tcores:
            shared[core].append(t)
    clashes = {core: sorted(ts) for core, ts in shared.items() if len(ts) > 1}
    evidence = {"smtActive": snap.host.smt_active, "physicalCores": len(cores),
                "sharedCores": [f"core {k}: {', '.join(v)}" for k, v in sorted(clashes.items())]}
    if clashes:
        return [host_target("fail", f"{len(clashes)} physical core(s) run more than one tenant", evidence)]
    return [host_target("pass", "every physical core serves at most one tenant", evidence)]


@check("XVM-06")
def ksm_off(snap: Snapshot, policy: Policy):
    run = snap.host.ksm_run
    if run is None:
        return [host_target("pass", "kernel same-page merging not available", {"ksmRun": None})]
    return [host_target("fail" if run == 1 else "pass",
                        "KSM is merging identical pages across workloads" if run == 1 else f"KSM off (run={run})",
                        {"ksmRun": run})]


@check("XVM-07")
def tripwires_armed(snap: Snapshot, policy: Policy):
    s = snap.self_state
    stale = policy.observation.heartbeat_stale_seconds
    out = []
    age = s.watcher_heartbeat_age_s
    out.append(Target(kind="auditor", ref="engine-event-watcher",
                      status="pass" if age is not None and age <= stale else "fail",
                      message=f"heartbeat {age:.0f}s ago" if age is not None else "not running",
                      evidence={"heartbeatAgeSeconds": age}))
    out.append(Target(kind="auditor", ref="canary",
                      status="pass" if s.canary_healthy else "fail",
                      message="canary running and healthy" if s.canary_healthy else "canary missing or unhealthy",
                      evidence={"healthy": s.canary_healthy}))
    out.append(Target(kind="auditor", ref="alert-rules",
                      status="pass" if s.rules_loaded else "fail",
                      message="Prometheus alert rules loaded" if s.rules_loaded else "alert rules not loaded",
                      evidence={"loaded": s.rules_loaded}))
    return out

