"""A decoy that no workload has any reason to contact (detection DET-07).

It sits on the provider network under the DNS alias `metadata`, imitating a cloud
instance-metadata endpoint. Every request gets a 404; any request that does not
come from loopback (the healthcheck) is reported to the auditor as a canary hit,
with the source IP so the auditor can attribute it to a tenant.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOOK_URL = os.environ.get("AUDITOR_HOOK_URL", "http://auditor:8088/hooks/canary")
TOKEN_FILE = os.environ.get("CANARY_TOKEN_FILE", "/run/secrets/canary_token")


def token() -> str:
    try:
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    except OSError:
        return ""


def report(src_ip: str, path: str, method: str, hit_ns: int) -> None:
    body = json.dumps({"srcIp": src_ip, "path": path, "method": method, "hitTimeNs": hit_ns}).encode()
    req = urllib.request.Request(
        HOOK_URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token()}"},
    )
    try:
        urllib.request.urlopen(req, timeout=3).read()
    except OSError as exc:
        print(f"canary: could not report hit from {src_ip}: {exc}", file=sys.stderr, flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "metadata/1.0"

    def _handle(self) -> None:
        hit_ns = time.time_ns()
        src = self.client_address[0]
        if src.startswith("127.") and self.path == "/__health":
            self._reply(200, b"ok\n")
            return
        self._reply(404, b"not found\n")
        if not src.startswith("127."):
            print(f"canary hit from {src}: {self.command} {self.path}", flush=True)
            threading.Thread(target=report, args=(src, self.path, self.command, hit_ns), daemon=True).start()

    do_GET = do_POST = do_PUT = do_HEAD = _handle

    def _reply(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


def main() -> None:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.daemon_threads = True
    print("canary listening on :8080", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
