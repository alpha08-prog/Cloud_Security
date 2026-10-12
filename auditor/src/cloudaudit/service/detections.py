"""In-memory detection store (DET-01 ... DET-09)."""

from __future__ import annotations

import itertools
import threading
import time
from collections import Counter, deque

from ..models import Detection

RULES = {
    "DET-01": ("Interactive exec into a tenant workload", "medium", ["R4"]),
    "DET-02": ("Privileged workload started", "critical", ["R2", "R4"]),
    "DET-03": ("Engine socket mounted into a workload", "critical", ["R4"]),
    "DET-04": ("Workload joined a host namespace", "high", ["R4"]),
    "DET-05": ("Unattributed workload started", "medium", ["R1"]),
    "DET-06": ("Workload attached to another tenant's network", "high", ["R4"]),
    "DET-07": ("Canary (decoy metadata service) contacted", "high", ["R4", "R1"]),
    "DET-08": ("Noisy neighbour: one tenant starving another of CPU", "medium", ["R3"]),
    "DET-09": ("Workload killed by its memory limit (OOM)", "low", ["R3"]),
}


class DetectionStore:
    def __init__(self, maxlen: int = 2000) -> None:
        self._lock = threading.Lock()
        self._items: deque[Detection] = deque(maxlen=maxlen)
        self._ids = itertools.count(1)
        self.counts: Counter[tuple[str, str, str]] = Counter()

    def raise_(self, rule: str, *, tenant: str | None, workload_id: str | None, service: str | None,
               event_time_ns: int, message: str, evidence: dict | None = None) -> Detection:
        title, severity, reqs = RULES[rule]
        now = time.time_ns()
        d = Detection(id=f"{rule}-{next(self._ids):05d}", rule=rule, title=title, severity=severity,
                      requirements=reqs, tenant=tenant, workload_id=workload_id, service=service,
                      event_time_ns=event_time_ns, detected_at_ns=now,
                      latency_ms=round(max(0, now - event_time_ns) / 1e6, 1), message=message,
                      evidence=evidence or {})
        with self._lock:
            self._items.append(d)
            self.counts[(rule, tenant or "unattributed", severity)] += 1
        print(f"detection {d.id} tenant={tenant} latency={d.latency_ms}ms: {message}", flush=True)
        return d

    def since(self, since_ns: int = 0) -> list[Detection]:
        with self._lock:
            return [d for d in self._items if d.detected_at_ns >= since_ns]
