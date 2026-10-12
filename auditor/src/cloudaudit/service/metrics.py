"""Prometheus exporter: per-tenant usage and pressure (R3), audit results, detections."""

from __future__ import annotations

import time

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from .. import __version__
from ..catalogue import BY_ID


class Collector:
    def __init__(self, get_auditor) -> None:
        self.get = get_auditor

    def describe(self):
        return []

    def collect(self):
        a = self.get()
        if a is None:
            return
        yield from self._workloads(a)
        yield from self._audit(a)
        yield from self._detections(a)
        yield from self._self(a)

    def _workloads(self, a):
        keys = ["service", "tenant", "plane", "workload_id"]
        cpu = CounterMetricFamily("cloudaudit_tenant_cpu_seconds", "CPU time used", labels=keys)
        thr = CounterMetricFamily("cloudaudit_tenant_cpu_throttled_seconds", "Time throttled by the CPU quota",
                                  labels=keys)
        mem = GaugeMetricFamily("cloudaudit_tenant_memory_bytes", "Memory in use", labels=keys)
        meml = GaugeMetricFamily("cloudaudit_tenant_memory_limit_bytes", "Memory limit (absent if none)", labels=keys)
        pids = GaugeMetricFamily("cloudaudit_tenant_pids", "Processes/threads", labels=keys)
        pidl = GaugeMetricFamily("cloudaudit_tenant_pids_limit", "PID limit (absent if none)", labels=keys)
        rx = CounterMetricFamily("cloudaudit_tenant_network_receive_bytes", "Bytes received", labels=keys)
        tx = CounterMetricFamily("cloudaudit_tenant_network_transmit_bytes", "Bytes sent", labels=keys)
        psi = CounterMetricFamily("cloudaudit_tenant_pressure_waiting_seconds",
                                  "PSI 'some': time at least one task waited for the resource",
                                  labels=[*keys, "resource"])
        for w in a.poller.snapshot():
            if not w.history:
                continue
            s = w.history[-1]
            lv = [w.service, w.tenant or "", w.plane, w.workload_id or ""]
            cpu.add_metric(lv, s.usage_us / 1e6)
            thr.add_metric(lv, s.throttled_us / 1e6)
            mem.add_metric(lv, s.mem_bytes)
            if s.mem_limit:
                meml.add_metric(lv, s.mem_limit)
            pids.add_metric(lv, s.pids)
            if s.pids_limit:
                pidl.add_metric(lv, s.pids_limit)
            if s.rx_bytes is not None:
                rx.add_metric(lv, s.rx_bytes)
                tx.add_metric(lv, s.tx_bytes or 0)
            for res, value in (("cpu", s.psi_cpu_us), ("memory", s.psi_mem_us), ("io", s.psi_io_us)):
                if value is not None:
                    psi.add_metric([*lv, res], value / 1e6)
        host = GaugeMetricFamily("cloudaudit_host_pressure_some_avg10", "Host-wide PSI some avg10 (%)",
                                 labels=["resource"])
        for res, value in a.poller.host_psi.items():
            host.add_metric([res], value)
        noisy = GaugeMetricFamily("cloudaudit_noisy_neighbour_active",
                                  "1 while a tenant exceeds its fair share of CPUs shared with active tenants (DET-08)",
                                  labels=["tenant"])
        for tenant, active in a.poller.noisy.items():
            noisy.add_metric([tenant], 1 if active else 0)
        cpus = GaugeMetricFamily("cloudaudit_host_logical_cpus", "Logical CPUs on the container host")
        cpus.add_metric([], len(a.poller.host_cpus))
        yield from (cpu, thr, mem, meml, pids, pidl, rx, tx, psi, host, noisy, cpus)

    def _audit(self, a):
        r = a.report
        if r is None:
            return
        status = GaugeMetricFamily("cloudaudit_check_status", "1 for the check's current status",
                                   labels=["check_id", "axis", "severity", "status", "waived"])
        passed = GaugeMetricFamily("cloudaudit_check_passed", "1 if the check passed",
                                   labels=["check_id", "axis", "severity"])
        for res in r.results:
            spec = BY_ID[res.check_id]
            status.add_metric([res.check_id, spec.axis, spec.severity, res.status, str(res.waived).lower()], 1)
            passed.add_metric([res.check_id, spec.axis, spec.severity], 1 if res.status == "pass" else 0)
        axis = GaugeMetricFamily("cloudaudit_axis_coverage_ratio", "Severity-weighted coverage per Fig 11 axis",
                                 labels=["axis"])
        for s in r.scores.by_axis:
            if s.score is not None:
                axis.add_metric([s.key], s.score)
        req = GaugeMetricFamily("cloudaudit_requirement_coverage_ratio", "Coverage per requirement R1-R4",
                                labels=["requirement"])
        for s in r.scores.by_requirement:
            if s.score is not None:
                req.add_metric([s.key], s.score)
        gate = GaugeMetricFamily("cloudaudit_gate_passed", "1 if the policy gate passes")
        gate.add_metric([], 1 if r.gate.passed else 0)
        last = GaugeMetricFamily("cloudaudit_last_scan_timestamp_seconds", "Time of the last audit scan")
        last.add_metric([], a.last_scan)
        yield from (status, passed, axis, req, gate, last)

    def _detections(self, a):
        fam = CounterMetricFamily("cloudaudit_detections", "Detections raised", labels=["rule", "tenant", "severity"])
        for (rule, tenant, severity), n in a.detections.counts.items():
            fam.add_metric([rule, tenant, severity], n)
        yield fam

    def _self(self, a):
        age = a.watcher.heartbeat_age()
        up = GaugeMetricFamily("cloudaudit_events_watcher_up", "1 if the engine-event watcher is live")
        up.add_metric([], 1 if age is not None and age < 30 else 0)
        info = GaugeMetricFamily("cloudaudit_info", "Auditor build and testbed profile",
                                 labels=["version", "profile", "platform"])
        platform = a.report.environment.platform if a.report else ""
        info.add_metric([__version__, a.profile, platform], 1)
        now = GaugeMetricFamily("cloudaudit_exporter_time_seconds", "Exporter clock")
        now.add_metric([], time.time())
        yield from (up, info, now)
