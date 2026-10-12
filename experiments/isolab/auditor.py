"""Client for the auditor's HTTP API (published on 127.0.0.1 by the testbed)."""

from __future__ import annotations

import json
import os
import time
import urllib.request

from . import util

BASE = f"http://127.0.0.1:{os.environ.get('AUDITOR_PORT', '8088')}"


def get(path: str, timeout: float = 60) -> bytes:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
        return r.read()


def get_json(path: str, timeout: float = 60):
    return json.loads(get(path, timeout))


def post(path: str, timeout: float = 60):
    req = urllib.request.Request(f"{BASE}{path}", data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def wait_ready(timeout: float = 120) -> None:
    def ready():
        try:
            return get_json("/healthz", 5).get("watcherHeartbeatAgeSeconds") is not None
        except OSError:
            return False
    util.wait_until(ready, timeout, 1.0, "auditor to be ready")


def detections(since_ns: int = 0) -> list[dict]:
    return get_json(f"/detections?since={since_ns}")


def server_now_ns() -> int:
    """The auditor's clock (inside the VM). Detection times are on this clock, not the host's."""
    return int(get_json("/healthz", 5)["serverTimeNs"])


def now_ns() -> int:
    return time.time_ns()
