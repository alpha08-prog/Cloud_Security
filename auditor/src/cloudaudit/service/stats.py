"""R3 - constant observation of shared resources.

Every few seconds, read each workload's cgroup v2 counters straight from the
host's cgroup tree (mounted read-only): CPU time, CPU throttling, memory, PIDs
and pressure stall information (PSI). PSI says how long a workload's runnable
tasks waited for a resource - the honest measure of a noisy neighbour, which raw
CPU% is not. Network bytes come from the engine's stats API.

The noisy-neighbour detector (DET-08) runs on these samples. A noisy neighbour
is a tenant that, for 30 s, uses more than its fair share of CPUs it SHARES with
other active tenants (fair share = host CPUs / active tenants). Tenants confined
to dedicated cores share nothing, so they cannot be noisy at the CPU level.

Why not trigger on the victim's own pressure? Measured on the testbed (E1 smoke
runs, see docs/experiments.md changelog), a lightly loaded victim's PSI stays
around 1% with or without a noisy neighbour, while its p99 latency triples: the
victim signal is too weak to threshold. The aggressor signal is unambiguous, and
the victim's pressure is still reported as evidence.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

from ..host import expand_cpus
from ..snapshot import docker_time_ns, plane, service, tenant, workload_id
from .detections import DetectionStore

# DET-08 parameters (see docs/experiments.md, H4).
MIN_AGGRESSOR_CORES = 1.5      # never flag a tenant using fewer cores than this ...
ACTIVE_CORES = 0.02            # ... a tenant using more than this counts as active (a potential victim) ...
RATE_WINDOW_S = 10.0           # ... usage measured over 10 s ...
SUSTAIN_S = 30.0               # ... condition held for 30 s in a row.


@dataclass
class Sample:
    t: float
    usage_us: int = 0
    throttled_us: int = 0
    psi_cpu_us: int | None = None
    psi_mem_us: int | None = None
    psi_io_us: int | None = None
    mem_bytes: int = 0
    mem_limit: int | None = None
    pids: int = 0
    pids_limit: int | None = None
    rx_bytes: int | None = None
    tx_bytes: int | None = None


@dataclass
class Workload:
    service: str
    tenant: str | None
    plane: str
    workload_id: str | None
    container_id: str
    started_ns: int
    cgroup: Path | None
    cpus: frozenset[int] = frozenset()
    history: deque = field(default_factory=lambda: deque(maxlen=64))


def _read_kv(path: Path) -> dict[str, int]:
    out = {}
    try:
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].lstrip("-").isdigit():
                out[parts[0]] = int(parts[1])
    except OSError:
        pass
    return out


def _read_psi_some_total(path: Path) -> int | None:
    try:
        for line in path.read_text().splitlines():
            if line.startswith("some "):
                for item in line.split()[1:]:
                    if item.startswith("total="):
                        return int(item[6:])
    except OSError:
        return None
    return None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def _read_int(path: Path) -> int | None:
    try:
        text = path.read_text().strip()
    except OSError:
        return None
    return None if text == "max" else int(text) if text.lstrip("-").isdigit() else None


def find_cgroup(root: Path, container_id: str) -> Path | None:
    for candidate in (root / "docker" / container_id, root / "system.slice" / f"docker-{container_id}.scope"):
        if (candidate / "cpu.stat").exists():
            return candidate
    for pattern in (f"*/{container_id}", f"*/*{container_id}*", f"*/*/*{container_id}*"):
        for match in root.glob(pattern):
            if (match / "cpu.stat").exists():
                return match
    return None


class StatsPoller(threading.Thread):
    def __init__(self, client, detections: DetectionStore, interval: float = 5.0,
                 cgroup_root: str | None = None) -> None:
        super().__init__(name="stats-poller", daemon=True)
        self.client = client
        self.detections = detections
        self.interval = interval
        self.root = Path(cgroup_root or os.environ.get("CGROUP_ROOT", "/host/cgroup"))
        self.workloads: dict[str, Workload] = {}
        self.lock = threading.Lock()
        self.host_psi: dict[str, float] = {}
        self.host_cpus = frozenset(expand_cpus(_read_text(self.root / "cpuset.cpus.effective") or "") or
                                   range(os.cpu_count() or 1))
        self._onset: dict[str, float] = {}
        self._fired: set[str] = set()
        self.noisy: dict[str, bool] = {}
        self._cycle = 0
        self.last_error: str | None = None

    # ------------------------------------------------------------------ sampling
    def run(self) -> None:
        while True:
            started = time.monotonic()
            try:
                self.poll()
                self.detect_noisy_neighbour()
                self.last_error = None
            except Exception as exc:  # keep observing whatever happens
                self.last_error = f"{type(exc).__name__}: {exc}"
                print(f"stats poller error: {self.last_error}", flush=True)
            time.sleep(max(0.5, self.interval - (time.monotonic() - started)))

    def poll(self) -> None:
        self._cycle += 1
        running = self.client.api.containers(filters={"status": "running"})
        seen = set()
        for c in running:
            cid = c["Id"]
            seen.add(cid)
            w = self.workloads.get(cid)
            if w is None:
                doc = self.client.api.inspect_container(cid)
                if plane(doc) == "operator":
                    continue
                w = Workload(service=service(doc), tenant=tenant(doc), plane=plane(doc),
                             workload_id=workload_id(doc), container_id=cid,
                             started_ns=docker_time_ns(doc["State"].get("StartedAt", "")),
                             cgroup=find_cgroup(self.root, cid))
                with self.lock:
                    self.workloads[cid] = w
            if w.cgroup is None:
                w.cgroup = find_cgroup(self.root, cid)
            if w.cgroup is not None and not w.cpus:
                w.cpus = frozenset(expand_cpus(_read_text(w.cgroup / "cpuset.cpus.effective") or "")) or self.host_cpus
            s = Sample(t=time.time())
            if w.cgroup is not None:
                cpu = _read_kv(w.cgroup / "cpu.stat")
                s.usage_us = cpu.get("usage_usec", 0)
                s.throttled_us = cpu.get("throttled_usec", 0)
                s.psi_cpu_us = _read_psi_some_total(w.cgroup / "cpu.pressure")
                s.psi_mem_us = _read_psi_some_total(w.cgroup / "memory.pressure")
                s.psi_io_us = _read_psi_some_total(w.cgroup / "io.pressure")
                s.mem_bytes = _read_int(w.cgroup / "memory.current") or 0
                s.mem_limit = _read_int(w.cgroup / "memory.max")
                s.pids = _read_int(w.cgroup / "pids.current") or 0
                s.pids_limit = _read_int(w.cgroup / "pids.max")
            if self._cycle % 3 == 1 or not w.history:  # network bytes: cheaper cadence
                try:
                    st = self.client.api.stats(cid, stream=False, one_shot=True)
                    nets = st.get("networks") or {}
                    s.rx_bytes = sum(n.get("rx_bytes", 0) for n in nets.values())
                    s.tx_bytes = sum(n.get("tx_bytes", 0) for n in nets.values())
                except Exception:
                    pass
            elif w.history:
                s.rx_bytes, s.tx_bytes = w.history[-1].rx_bytes, w.history[-1].tx_bytes
            w.history.append(s)
        with self.lock:
            for cid in list(self.workloads):
                if cid not in seen:
                    del self.workloads[cid]
        for res in ("cpu", "memory", "io"):
            try:
                line = Path(f"/proc/pressure/{res}").read_text().splitlines()[0]
                self.host_psi[res] = float(line.split()[1].split("=")[1])
            except (OSError, IndexError, ValueError):
                pass

    # ------------------------------------------------------------------ rates
    @staticmethod
    def rate(history: deque, attr: str, window: float) -> float | None:
        if len(history) < 2:
            return None
        newest = history[-1]
        oldest = next((s for s in history if newest.t - s.t <= window + 0.5), history[0])
        a, b = getattr(oldest, attr), getattr(newest, attr)
        dt = newest.t - oldest.t
        if a is None or b is None or dt <= 0:
            return None
        return (b - a) / (dt * 1e6)  # microseconds per second -> fraction (or cores)

    def snapshot(self) -> list[Workload]:
        with self.lock:
            return list(self.workloads.values())

    # ------------------------------------------------------------------ DET-08
    def detect_noisy_neighbour(self) -> None:
        tenants = [w for w in self.snapshot() if w.plane == "tenant"]
        cores: dict[str, float] = defaultdict(float)
        cpus: dict[str, set[int]] = defaultdict(set)
        members: dict[str, list[Workload]] = defaultdict(list)
        for w in tenants:
            key = w.tenant or f"unlabelled:{w.service}"
            cores[key] += self.rate(w.history, "usage_us", RATE_WINDOW_S) or 0.0
            cpus[key] |= set(w.cpus or self.host_cpus)
            members[key].append(w)
        active = [k for k, c in cores.items() if c > ACTIVE_CORES]
        fair_share = len(self.host_cpus) / max(1, len(active))
        now = time.time()
        for key in cores:
            victims = [v for v in active if v != key and cpus[v] & cpus[key]]
            condition = bool(victims) and cores[key] > max(MIN_AGGRESSOR_CORES, fair_share)
            self.noisy[key] = condition
            if not condition:
                self._onset.pop(key, None)
                self._fired.discard(key)
                continue
            self._onset.setdefault(key, now)
            if now - self._onset[key] < SUSTAIN_S or key in self._fired:
                continue
            self._fired.add(key)
            hot = max(members[key], key=lambda w: self.rate(w.history, "usage_us", RATE_WINDOW_S) or 0.0)
            pressure = []  # victims' CPU pressure, as evidence (see module docstring)
            for v in victims:
                for w in members[v]:
                    p = self.rate(w.history, "psi_cpu_us", RATE_WINDOW_S)
                    if p is not None:
                        pressure.append(f"{w.service} {p * 100:.2f}%")
            self.detections.raise_(
                "DET-08", tenant=hot.tenant, workload_id=hot.workload_id, service=hot.service,
                event_time_ns=hot.started_ns,
                message=f"tenant {key} uses {cores[key]:.1f} cores (fair share {fair_share:.1f}) on CPUs it shares "
                        f"with tenant(s) {', '.join(sorted(victims))}",
                evidence={"aggressorCores": round(cores[key], 2), "fairShareCores": round(fair_share, 2),
                          "victims": sorted(victims), "victimCpuPressurePct": pressure,
                          "sharedCpus": len(set().union(*(cpus[v] for v in victims)) & cpus[key]),
                          "sustainedSeconds": round(now - self._onset[key], 1)})

    def observed(self) -> dict[str, dict]:
        now = time.time()
        out = {}
        for w in self.snapshot():
            if not w.history:
                continue
            last = w.history[-1]
            out[w.service] = {"last_sample_age_s": now - last.t, "psi": last.psi_cpu_us is not None}
        return out
