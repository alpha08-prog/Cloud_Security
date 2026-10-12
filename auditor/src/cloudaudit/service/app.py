"""The auditor service: one process that audits, observes and detects.

    GET  /healthz                 liveness
    GET  /report[?fresh=1]        latest audit report (JSON); fresh=1 re-scans first
    GET  /report.sarif            the same report as SARIF 2.1.0
    GET  /report.txt              the same report as a console summary
    GET  /snapshot                sanitized snapshot (env values redacted) - test fixtures
    GET  /detections?since=NS     detections raised since an epoch-nanosecond time
    POST /scan                    re-scan now
    POST /hooks/canary            canary hit (bearer token from a Compose secret)
    GET  /metrics                 Prometheus exporter

It only ever talks to the engine through the read-only socket proxy.
"""

from __future__ import annotations

import hmac
import os
import threading
import time
import urllib.request

import docker
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_client.core import REGISTRY

from .. import snapshot as snap_mod
from ..engine import build_report
from ..models import AuditReport
from ..policy import Policy, load_policy, load_waivers
from ..report import to_console, to_sarif
from ..snapshot import L_SERVICE, L_TENANT, L_WORKLOAD, ObservedTenant, SelfState
from .detections import DetectionStore
from .events import EventWatcher
from .metrics import Collector
from .stats import StatsPoller

TESTBED = os.environ.get("TESTBED_DIR", "/workspace/testbed")
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
SCAN_INTERVAL_S = 60.0
DEBOUNCE_S = 3.0


class Auditor:
    def __init__(self) -> None:
        self.client = docker.DockerClient(base_url=os.environ.get("DOCKER_HOST", "tcp://socket-proxy:2375"),
                                          timeout=15)
        self.profile = os.environ.get("ISOLAB_PROFILE", "hardened")
        self.detections = DetectionStore()
        self.policy: Policy | None = None
        self.report: AuditReport | None = None
        self.report_lock = threading.Lock()
        self.scan_lock = threading.Lock()
        self.last_scan = 0.0
        self.rules_loaded: bool | None = None
        self._wake = threading.Event()
        self._load_policy()
        interval = self.policy.observation.stats_interval_seconds if self.policy else 5.0
        self.poller = StatsPoller(self.client, self.detections, interval=interval)
        self.watcher = EventWatcher(self.client, self.detections, lambda: self.policy, self.request_scan)

    def _load_policy(self) -> None:
        self.policy = load_policy(f"{TESTBED}/policy.yaml")

    def start(self) -> None:
        self.poller.start()
        self.watcher.start()
        threading.Thread(target=self._scan_loop, name="scanner", daemon=True).start()

    # ------------------------------------------------------------------ scanning
    def request_scan(self) -> None:
        self._wake.set()

    def _scan_loop(self) -> None:
        time.sleep(DEBOUNCE_S * 2)  # let the poller take a first sample
        while True:
            try:
                self.scan()
            except Exception as exc:
                print(f"scan failed: {type(exc).__name__}: {exc}", flush=True)
            woke = self._wake.wait(SCAN_INTERVAL_S)
            if woke:
                time.sleep(DEBOUNCE_S)
                self._wake.clear()

    def self_state(self) -> SelfState:
        return SelfState(
            watcher_heartbeat_age_s=self.watcher.heartbeat_age(),
            rules_loaded=self.rules_loaded,
            observed={k: ObservedTenant(**v) for k, v in self.poller.observed().items()},
        )

    def _check_rules(self) -> None:
        try:
            with urllib.request.urlopen(f"{PROMETHEUS_URL}/api/v1/rules", timeout=3) as r:
                import json  # noqa: PLC0415

                groups = json.load(r).get("data", {}).get("groups", [])
                self.rules_loaded = any(g.get("rules") for g in groups)
        except OSError:
            self.rules_loaded = False

    def scan(self) -> AuditReport:
        with self.scan_lock:
            self._load_policy()
            self._check_rules()
            snap = snap_mod.take(self.client, profile=self.profile, self_state=self.self_state(),
                                 cgroup_root=os.environ.get("CGROUP_ROOT", "/host/cgroup"))
            canary = [c for c in snap.containers if snap_mod.service(c) == "canary"]
            snap.self_state.canary_healthy = bool(canary) and \
                ((canary[0]["State"].get("Health") or {}).get("Status") == "healthy")
            self._last_snapshot = snap
            report = build_report(snap, self.policy, load_waivers(f"{TESTBED}/waivers.yaml"))
            with self.report_lock:
                self.report = report
                self.last_scan = time.time()
            return report

    # ------------------------------------------------------------------ canary
    def canary_hit(self, body: dict) -> dict:
        src = body.get("srcIp", "")
        hit_ns = int(body.get("hitTimeNs") or time.time_ns())
        attrs: dict = {"name": None}
        for c in self.client.api.containers(filters={"status": "running"}):
            for net in ((c.get("NetworkSettings") or {}).get("Networks") or {}).values():
                if net.get("IPAddress") == src:
                    labels = c.get("Labels") or {}
                    attrs = {**labels, "name": (c.get("Names") or ["?"])[0].lstrip("/")}
        service = attrs.get(L_SERVICE) or attrs.get("name") or f"unknown ({src})"
        d = self.detections.raise_(
            "DET-07", tenant=attrs.get(L_TENANT), workload_id=attrs.get(L_WORKLOAD), service=service,
            event_time_ns=hit_ns, message=f"{service} contacted the decoy metadata service ({body.get('method')} "
                                          f"{body.get('path')})",
            evidence={"path": str(body.get("path"))[:200], "attributed": attrs.get(L_TENANT) is not None})
        return d.dump()


auditor: Auditor | None = None
app = FastAPI(title="cloudaudit", version="1.0.0", docs_url=None, redoc_url=None)


def _token() -> str:
    try:
        with open(os.environ.get("CANARY_TOKEN_FILE", "/run/secrets/canary_token")) as f:
            return f.read().strip()
    except OSError:
        return ""


@app.get("/healthz")
def healthz():
    return {"ok": True, "watcherHeartbeatAgeSeconds": auditor.watcher.heartbeat_age() if auditor else None}


@app.get("/report")
def report(fresh: bool = False):
    if fresh or auditor.report is None:
        auditor.scan()
    return JSONResponse(auditor.report.dump())


@app.get("/report.sarif")
def report_sarif(fresh: bool = False):
    if fresh or auditor.report is None:
        auditor.scan()
    return JSONResponse(to_sarif(auditor.report))


@app.get("/report.txt", response_class=PlainTextResponse)
def report_text(fresh: bool = False):
    if fresh or auditor.report is None:
        auditor.scan()
    return to_console(auditor.report)


@app.get("/snapshot")
def snapshot():
    auditor.scan()
    return JSONResponse(auditor._last_snapshot.sanitized().model_dump(mode="json"))


@app.post("/scan")
def scan():
    r = auditor.scan()
    return {"gatePassed": r.gate.passed, "generatedAt": r.generated_at}


@app.get("/detections")
def detections(since: int = 0):
    return [d.dump() for d in auditor.detections.since(since)]


@app.post("/hooks/canary")
async def canary(request: Request):
    header = request.headers.get("authorization", "")
    token = _token()
    if not token or not hmac.compare_digest(header, f"Bearer {token}"):
        raise HTTPException(status_code=401, detail="bad token")
    return auditor.canary_hit(await request.json())


@app.get("/metrics")
def metrics():
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/", response_class=PlainTextResponse)
def index():
    return __doc__


def run(port: int = 8088) -> None:
    global auditor
    import uvicorn  # noqa: PLC0415

    auditor = Auditor()
    REGISTRY.register(Collector(lambda: auditor))
    auditor.start()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning", access_log=False)
