"""Check registry and helpers shared by the check modules.

A check is a pure function `(Snapshot, Policy) -> list[Target]`: one target per
workload/network/volume/host fact it looked at, each with its own status and
evidence. The engine (cloudaudit.engine) rolls targets up into a CheckResult.
"""

from __future__ import annotations

from collections.abc import Callable

from ..models import Target
from ..policy import Policy
from ..snapshot import Snapshot, plane, service, tenant, workload_id

CheckFn = Callable[[Snapshot, Policy], list[Target]]
REGISTRY: dict[str, CheckFn] = {}

TENANT = ("tenant",)
WORKLOADS = ("tenant", "provider")


def check(check_id: str) -> Callable[[CheckFn], CheckFn]:
    def register(fn: CheckFn) -> CheckFn:
        if check_id in REGISTRY:
            raise ValueError(f"{check_id} registered twice")
        REGISTRY[check_id] = fn
        return fn
    return register


def containers(snap: Snapshot, policy: Policy, planes: tuple[str, ...] = TENANT) -> list[dict]:
    """Running containers in the given planes. Operator-plane helpers and ignored services are excluded."""
    return [c for c in snap.containers
            if plane(c) in planes and service(c) not in policy.ignore_services]


def target(c: dict, status: str, message: str, evidence: dict | None = None) -> Target:
    return Target(kind="container", ref=service(c), tenant=tenant(c), workload_id=workload_id(c),
                  status=status, message=message, evidence=evidence or {})


def excepted(c: dict, policy: Policy, check_id: str) -> Target | None:
    exc = policy.exception_for(service(c), check_id)
    if exc:
        return target(c, "skip", f"documented provider exception: {exc.reason.strip()}", {"exception": True})
    return None


def host_target(status: str, message: str, evidence: dict | None = None, ref: str = "host") -> Target:
    return Target(kind="host", ref=ref, status=status, message=message, evidence=evidence or {})


def same_tenant_ref(snap: Snapshot, c: dict, mode: str) -> bool:
    """For `container:<id|name>` namespace modes: is the other container in the same tenant?"""
    other = mode.split(":", 1)[1]
    for o in snap.containers:
        if o.get("Id", "").startswith(other) or o.get("Name", "").lstrip("/") == other:
            return tenant(o) is not None and tenant(o) == tenant(c)
    return False


# Import the check modules so their @check decorators register.
from . import cross_tenant, data_leakage, hypervisor, identification, isolation  # noqa: E402,F401
