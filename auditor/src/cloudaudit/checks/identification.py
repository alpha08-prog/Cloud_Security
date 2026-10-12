"""VM identification (Fig 11 axis, requirement R1): knowing exactly what runs, for
whom, where it came from, and that it is being watched."""

from __future__ import annotations

from collections import Counter

from ..models import Target
from ..policy import Policy
from ..snapshot import L_PLANE, L_TENANT, Snapshot, labels, plane, service, short_network, tenant, workload_id
from . import TENANT, WORKLOADS, check, containers, target


@check("ID-01")
def identity_labels(snap: Snapshot, policy: Policy):
    counts = Counter(workload_id(c) for c in snap.containers if workload_id(c))
    out = []
    for c in containers(snap, policy, WORKLOADS):
        required = policy.required_labels.get(plane(c), [])
        missing = [k for k in required if not labels(c).get(k)]
        wid = workload_id(c)
        problems = []
        if missing:
            problems.append(f"missing {', '.join(missing)}")
        if wid and counts[wid] > 1:
            problems.append(f"workload id {wid} is not unique")
        out.append(target(c, "fail" if problems else "pass", "; ".join(problems) or f"identified as {wid}",
                          {"plane": labels(c).get(L_PLANE), "missing": missing}))
    return out


@check("ID-02")
def no_unattributed(snap: Snapshot, policy: Policy):
    out = []
    for c in snap.containers:
        if service(c) in policy.ignore_services:
            continue
        attributed = bool(labels(c).get(L_PLANE)) and bool(workload_id(c))
        if not attributed:
            out.append(target(c, "fail", "running without an identity (no plane/workload-id labels)",
                              {"image": c["Config"].get("Image")}))
    if not out:
        out.append(Target(kind="fleet", ref="host", status="pass",
                          message=f"all {len(snap.containers)} running containers are attributed",
                          evidence={"running": len(snap.containers)}))
    return out


@check("ID-03")
def identity_matches_placement(snap: Snapshot, policy: Policy):
    nets = {n["Name"]: n for n in snap.networks}
    vols = {v["Name"]: v for v in snap.volumes}
    out = []
    for c in containers(snap, policy, TENANT):
        mine = tenant(c)
        if not mine:
            out.append(target(c, "skip", "no tenant label (see ID-01)"))
            continue
        wrong = []
        for net in (c.get("NetworkSettings") or {}).get("Networks") or {}:
            owner = ((nets.get(net) or {}).get("Labels") or {}).get(L_TENANT)
            if owner != mine:
                wrong.append(f"network {short_network(net)} ({'tenant ' + owner if owner else 'not tenant ' + mine})")
        for m in c.get("Mounts") or []:
            if m.get("Type") != "volume":
                continue
            owner = ((vols.get(m.get("Name", "")) or {}).get("Labels") or {}).get(L_TENANT)
            if owner != mine:
                wrong.append(f"volume {short_network(m.get('Name', ''))} "
                             f"({'tenant ' + owner if owner else 'not tenant ' + mine})")
        out.append(target(c, "fail" if wrong else "pass",
                          "attached to " + "; ".join(wrong) if wrong else f"only tenant {mine}'s networks and volumes",
                          {"mismatches": wrong}))
    return out


@check("ID-04")
def image_provenance(snap: Snapshot, policy: Policy):
    out = []
    for c in containers(snap, policy, WORKLOADS):
        ref = c["Config"].get("Image") or ""
        img_labels = ((snap.images.get(c.get("Image", "")) or {}).get("Config") or {}).get("Labels") or {}
        base = img_labels.get("org.opencontainers.image.base.name", "")
        revision = img_labels.get("org.opencontainers.image.revision", "")
        if "@sha256:" in ref:
            status, msg = "pass", "image pinned by digest"
        elif "@sha256:" in base and revision:
            status, msg = "pass", f"built from a pinned base at revision {revision}"
        else:
            missing = []
            if "@sha256:" not in base:
                missing.append("base image not pinned by digest" if base else "no base image label")
            if not revision:
                missing.append("no source revision label")
            status, msg = "fail", "; ".join(missing)
        out.append(target(c, status, msg, {"image": ref, "base": base or None, "revision": revision or None}))
    return out


@check("ID-05")
def continuously_observed(snap: Snapshot, policy: Policy):
    stale = policy.observation.stale_after_seconds
    observed = snap.self_state.observed
    out = []
    for c in containers(snap, policy, TENANT):
        o = observed.get(service(c))
        if o is None or o.last_sample_age_s is None:
            out.append(target(c, "fail", "no usage samples"))
        elif o.last_sample_age_s > stale:
            out.append(target(c, "fail", f"last sample {o.last_sample_age_s:.0f}s ago",
                              {"lastSampleAgeSeconds": round(o.last_sample_age_s, 1)}))
        elif not o.psi:
            out.append(target(c, "warn", "usage sampled, but pressure (PSI) unavailable",
                              {"lastSampleAgeSeconds": round(o.last_sample_age_s, 1), "psi": False}))
        else:
            out.append(target(c, "pass", "usage and pressure sampled",
                              {"lastSampleAgeSeconds": round(o.last_sample_age_s, 1), "psi": True}))
    return out
