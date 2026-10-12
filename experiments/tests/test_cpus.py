"""The CPU placement planner: tenants on separate physical cores whenever possible."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from isolab.cpus import plan  # noqa: E402


def smt(cores: int) -> list[list[int]]:
    return [[2 * i, 2 * i + 1] for i in range(cores)]


def physical(placement, cpus):
    return {i for i, core in enumerate(placement.cores) for c in cpus if c in core}


def test_six_cores_give_every_role_its_own_physical_cores():
    p = plan(smt(6))
    roles = [p.provider, p.loadgen, p.tenant["a"], p.tenant["b"], p.tenant["c"]]
    owned = [physical(p, r) for r in roles]
    for i, a in enumerate(owned):
        for b in owned[i + 1:]:
            assert not a & b
    assert p.env()["CPUSET_TENANT_B"] == "6,7,8,9"
    assert p.quota["b"] == 3.0  # one thread short of its cpuset so the quota is what caps the noisy job
    assert p.env()["STRESS_WORKERS"] == "12"
    assert p.notes == []


def test_two_core_ci_runner_shares_a_core_and_says_so():
    p = plan(smt(2))
    assert physical(p, p.tenant["a"]) == physical(p, p.tenant["b"])  # siblings of one core
    assert set(p.tenant["a"]).isdisjoint(p.tenant["b"])              # but never the same thread
    assert any("SMT siblings" in n for n in p.notes)


def test_tenant_cpusets_never_overlap_between_tenants():
    for n in range(2, 9):
        p = plan(smt(n))
        a, b, c = (set(p.tenant[k]) for k in "abc")
        assert a.isdisjoint(b)
        assert a.isdisjoint(c) and b.isdisjoint(c) or n < 3
