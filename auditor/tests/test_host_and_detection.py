"""Host fact parsing (fake sysfs), engine-event detections and the noisy-neighbour rule."""

from __future__ import annotations

import time
from collections import deque

from cloudaudit import host
from cloudaudit.service.detections import DetectionStore
from cloudaudit.service.events import EventWatcher
from cloudaudit.service.stats import Sample, StatsPoller, Workload
from cloudaudit.snapshot import docker_time_ns


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_host_facts_from_a_fake_sysfs(tmp_path):
    cpu = tmp_path / "sys/devices/system/cpu"
    for i in range(4):
        write(cpu / f"cpu{i}/topology/thread_siblings_list", "0-1" if i < 2 else "2-3")
    write(cpu / "smt/control", "on")
    write(cpu / "smt/active", "1")
    write(cpu / "vulnerabilities/meltdown", "Not affected")
    write(cpu / "vulnerabilities/spec_rstack_overflow", "Vulnerable: Safe RET, no microcode")
    write(tmp_path / "sys/kernel/mm/ksm/run", "0")
    write(tmp_path / "proc/sys/kernel/kptr_restrict", "1")
    facts = host.collect(str(tmp_path), str(tmp_path / "nocgroup"))
    assert facts.cores == [[0, 1], [2, 3]]
    assert facts.smt_active is True and facts.ksm_run == 0
    assert facts.vulnerabilities["spec_rstack_overflow"].startswith("Vulnerable")
    assert facts.sysctls["kernel.kptr_restrict"] == 1 and facts.sysctls["kernel.dmesg_restrict"] is None


def test_docker_timestamps_keep_nanoseconds():
    assert docker_time_ns("2026-10-12T15:35:15.460886701Z") == 1791819315460886701
    assert docker_time_ns("2026-10-12T15:35:15Z") == 1791819315000000000


class FakeAPI:
    def __init__(self, containers, networks=None):
        self._c, self._n = containers, networks or {}

    def inspect_container(self, cid):
        return self._c[cid]

    def inspect_network(self, name):
        return self._n[name]


class FakeClient:
    def __init__(self, containers, networks=None):
        self.api = FakeAPI(containers, networks)


def container(labels=None, privileged=False, mounts=None, pid="", healthcheck=None):
    return {"Name": "/x", "Config": {"Labels": labels or {}, "Image": "alpine",
                                     "Healthcheck": {"Test": healthcheck} if healthcheck else None},
            "HostConfig": {"Privileged": privileged, "PidMode": pid}, "Mounts": mounts or []}


TENANT_B = {"io.isolab.plane": "tenant", "io.isolab.tenant": "b", "io.isolab.workload-id": "trig",
            "com.docker.compose.service": "trigger"}


def watcher(containers, networks=None):
    store = DetectionStore()
    return EventWatcher(FakeClient(containers, networks), store, lambda: None, lambda: None), store


def event(action, cid="c1", attrs=None, etype="container"):
    return {"Type": etype, "Action": action, "Actor": {"ID": cid, "Attributes": attrs or {}},
            "timeNano": time.time_ns()}


def test_privileged_socket_and_host_pid_are_detected():
    w, store = watcher({"c1": container(TENANT_B, privileged=True, pid="host",
                                        mounts=[{"Source": "/var/run/docker.sock"}])})
    w.handle(event("create", attrs=TENANT_B))
    rules = sorted(d.rule for d in store.since())
    assert rules == ["DET-02", "DET-03", "DET-04"]
    assert all(d.tenant == "b" for d in store.since())


def test_unlabelled_workload_is_unattributed():
    w, store = watcher({"c1": container({})})
    w.handle(event("create"))
    [d] = store.since()
    assert d.rule == "DET-05" and d.tenant is None


def test_healthcheck_execs_are_not_people():
    hc = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz')"]
    w, store = watcher({"c1": container(TENANT_B, healthcheck=hc)})
    w.handle(event("exec_create: " + " ".join(hc[1:]), attrs=TENANT_B))
    assert store.since() == []
    w.handle(event("exec_create: sh", attrs=TENANT_B))
    assert [d.rule for d in store.since()] == ["DET-01"]


def test_cross_tenant_network_attach():
    nets = {"isolab_net-a": {"Labels": {"io.isolab.tenant": "a"}},
            "isolab_net-b": {"Labels": {"io.isolab.tenant": "b"}}}
    w, store = watcher({"c1": container(TENANT_B)}, nets)
    w.handle(event("connect", attrs={"container": "c1", "name": "isolab_net-b"}, etype="network"))
    assert store.since() == []  # own network
    w.handle(event("connect", attrs={"container": "c1", "name": "isolab_net-a"}, etype="network"))
    [d] = store.since()
    assert d.rule == "DET-06" and d.evidence["networkOwner"] == "a"


def _workload(tenant, service, usage_cores, pressure=0.0, cpus=(), n=10, step=5.0):
    w = Workload(service=service, tenant=tenant, plane="tenant", workload_id=service, container_id=service,
                 started_ns=time.time_ns(), cgroup=None, cpus=frozenset(cpus), history=deque(maxlen=64))
    t0 = time.time() - n * step
    for i in range(n + 1):
        w.history.append(Sample(t=t0 + i * step, usage_us=int(usage_cores * 1e6 * i * step),
                                psi_cpu_us=int(pressure * 1e6 * i * step)))
    return w


def _poller(monkeypatch, workloads, host_cpus=12):
    store = DetectionStore()
    poller = StatsPoller(client=None, detections=store)
    poller.host_cpus = frozenset(range(host_cpus))
    monkeypatch.setattr(poller, "snapshot", lambda: workloads)
    return poller, store


def test_noisy_neighbour_on_shared_cpus_fires_after_30s(monkeypatch):
    victim = _workload("a", "tenant-a", 0.2, pressure=0.012)       # no cpusets: everything shared
    noisy = _workload("b", "tenant-b-job", 11.2)
    poller, store = _poller(monkeypatch, [victim, noisy])
    poller.detect_noisy_neighbour()                                 # condition starts ...
    assert store.since() == [] and poller.noisy["b"] is True
    poller._onset["b"] -= 31                                        # ... and has held for 31 s
    poller.detect_noisy_neighbour()
    [d] = store.since()
    assert d.rule == "DET-08" and d.tenant == "b" and d.evidence["victims"] == ["a"]
    assert d.evidence["fairShareCores"] == 6.0                      # 12 CPUs / 2 active tenants


def test_dedicated_cpusets_cannot_be_noisy(monkeypatch):
    victim = _workload("a", "tenant-a", 0.2, cpus={4, 5})
    busy = _workload("b", "tenant-b-job", 7.0, cpus={6, 7, 8, 9, 10, 11, 0})   # big, but no overlap with a
    poller, store = _poller(monkeypatch, [victim, busy])
    poller._onset["b"] = time.time() - 60
    poller.detect_noisy_neighbour()
    assert store.since() == [] and poller.noisy["b"] is False


def test_no_victim_means_no_noisy_neighbour(monkeypatch):
    busy = _workload("b", "tenant-b-job", 11.0)
    idle = _workload("a", "tenant-a", 0.001)                        # not active: nobody to disturb
    poller, store = _poller(monkeypatch, [busy, idle])
    poller._onset["b"] = time.time() - 60
    poller.detect_noisy_neighbour()
    assert store.since() == []


def test_within_fair_share_is_not_noisy(monkeypatch):
    a = _workload("a", "tenant-a", 0.3)
    b = _workload("b", "tenant-b", 3.0)                             # fair share 6 on 12 CPUs
    poller, store = _poller(monkeypatch, [a, b])
    poller.detect_noisy_neighbour()
    assert poller.noisy["b"] is False
