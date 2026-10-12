"""tenant-a: a small CPU-sensitive HTTP service, the victim in experiment E1.

GET /healthz  -> 200 "ok"
GET /work     -> runs a fixed CPU loop (WORK_ITERATIONS rounds of SHA-256) and
                 reports the compute time in a Server-Timing header, so the load
                 generator can separate queueing delay from compute slowdown.

On start it writes a non-secret marker file to its data volume. Experiment E2
checks whether another tenant can read it (a shared-storage leak), so the file
says plainly that it is only a marker.
"""

from __future__ import annotations

import hashlib
import os
import signal
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WORK_ITERATIONS = int(os.environ.get("WORK_ITERATIONS", "6000"))
DATA_DIR = os.environ.get("DATA_DIR", "/data")
BLOCK = b"isolab" * 32


def do_work() -> float:
    start = time.perf_counter()
    digest = BLOCK
    for _ in range(WORK_ITERATIONS):
        digest = hashlib.sha256(digest + BLOCK).digest()
    return (time.perf_counter() - start) * 1000


class Handler(BaseHTTPRequestHandler):
    server_version = "payments-api/1.0"

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        if self.path == "/healthz":
            self._reply(200, b"ok\n", "text/plain")
        elif self.path.startswith("/work"):
            ms = do_work()
            self._reply(200, b'{"ok":true}\n', "application/json", {"Server-Timing": f"work;dur={ms:.3f}"})
        else:
            self._reply(404, b"not found\n", "text/plain")

    def _reply(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # keep the hot path quiet
        pass


def write_marker() -> None:
    path = os.path.join(DATA_DIR, "tenant-a")
    try:
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "marker.txt"), "w") as f:
            f.write("IsoLab marker file for tenant-a. Not a secret; used to test storage isolation.\n")
    except OSError as exc:
        print(f"marker not written: {exc}", file=sys.stderr)


def main() -> None:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    write_marker()
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.daemon_threads = True
    print(f"payments-api listening on :8080 (WORK_ITERATIONS={WORK_ITERATIONS})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
