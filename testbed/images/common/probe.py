"""Read-only isolation probes, run inside a tenant container by experiment E2.

Every probe either opens a TCP/HTTP connection with a short timeout or reads a
file. None of them writes, escalates, or measures another tenant's timing: the
point is to verify which boundaries are open, like testing a firewall rule.

Output is one JSON document on stdout:
    {"tenant": "c", "probes": [{"id": "P1", "outcome": "allowed|blocked|error", "detail": "..."}]}
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import struct
import sys
import threading

TIMEOUT = 2.0


def http_get(host: str, port: int, path: str) -> tuple[str, str]:
    """`allowed` if any HTTP response comes back, otherwise `blocked`."""
    try:
        conn = http.client.HTTPConnection(host, port, timeout=TIMEOUT)
        conn.request("GET", path, headers={"User-Agent": "isolab-probe"})
        status = conn.getresponse().status
        conn.close()
        return "allowed", f"HTTP {status} from {host}:{port}"
    except socket.gaierror:
        return "blocked", f"name {host} does not resolve"
    except (TimeoutError, socket.timeout):
        return "blocked", f"timeout connecting to {host}:{port}"
    except OSError as exc:
        return "blocked", f"{type(exc).__name__}: {exc.strerror or exc}"


def tcp_connect(host: str, port: int) -> tuple[str, str]:
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return "allowed", f"TCP connect to {host}:{port} succeeded"
    except socket.gaierror:
        return "blocked", f"name {host} does not resolve"
    except (TimeoutError, socket.timeout):
        return "blocked", f"timeout connecting to {host}:{port}"
    except OSError as exc:
        return "blocked", f"{type(exc).__name__}: {exc.strerror or exc}"


def default_gateway() -> str | None:
    try:
        with open("/proc/net/route") as f:
            for line in f.readlines()[1:]:
                fields = line.split()
                if fields[1] == "00000000":
                    return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
    except OSError:
        pass
    return None


def host_gateway() -> str | None:
    try:
        return socket.gethostbyname("host.docker.internal")
    except OSError:
        return default_gateway()


def loopback_control() -> tuple[str, str]:
    """Positive control: a listener on our own loopback must be reachable."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    threading.Thread(target=lambda: server.accept()[0].close(), daemon=True).start()
    outcome = tcp_connect("127.0.0.1", port)
    server.close()
    return outcome


def sees_process(marker: str) -> tuple[str, str]:
    """`allowed` if a process whose command line contains `marker` is visible."""
    seen = 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        seen += 1
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                if marker.encode() in f.read():
                    return "allowed", f"process matching '{marker}' visible as pid {pid}"
        except OSError:
            continue
    return "blocked", f"not visible among {seen} processes"


def engine_socket(path: str = "/var/run/docker.sock") -> tuple[str, str]:
    if not os.path.exists(path):
        return "blocked", f"{path} not present"
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.connect(path)
        s.sendall(b"GET /_ping HTTP/1.0\r\nHost: docker\r\n\r\n")
        reply = s.recv(256).decode(errors="replace")
        s.close()
        if " 200 " in reply.split("\r\n", 1)[0]:
            return "allowed", "engine API answered /_ping"
        return "blocked", f"socket present, unexpected reply: {reply[:40]!r}"
    except OSError as exc:
        return "blocked", f"socket present but not usable: {exc.strerror or exc}"


def readable(path: str) -> tuple[str, str]:
    try:
        with open(path, "rb") as f:
            f.read(64)
        return "allowed", f"{path} is readable"
    except FileNotFoundError:
        return "blocked", f"{path} not present"
    except OSError as exc:
        return "blocked", f"{path}: {exc.strerror or exc}"


def effective_capabilities() -> tuple[str, str]:
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("CapEff:"):
                value = int(line.split()[1], 16)
                if value:
                    return "allowed", f"CapEff={value:#x} ({bin(value).count('1')} capabilities)"
                return "blocked", "CapEff=0 (no capabilities)"
    return "error", "CapEff not found"


def suite(role: str, tenant_a_ip: str | None) -> list[dict]:
    """The probe set for one tenant; ids match docs/experiments.md (E2)."""
    probes: list[tuple[str, callable]] = []
    if role == "c":
        gateway = host_gateway()
        probes = [
            ("C3", loopback_control),
            ("P1", lambda: http_get("tenant-a", 8080, "/healthz")),
            ("P2", lambda: http_get(tenant_a_ip, 8080, "/healthz") if tenant_a_ip
             else ("error", "tenant-a IP not supplied")),
            ("P3", lambda: http_get(gateway, 18080, "/healthz") if gateway
             else ("blocked", "no host gateway")),
            ("P4", lambda: http_get("metadata", 8080, "/latest/meta-data/")),
            ("P5", lambda: http_get("prometheus", 9090, "/-/healthy")),
            ("P6", lambda: tcp_connect("1.1.1.1", 443)),
            ("P7", lambda: sees_process("payments_api")),
            ("P8", engine_socket),
            ("P9", lambda: readable("/host-etc/os-release")),
            ("P10", lambda: readable("/data/tenant-a/marker.txt")),
            ("P11", effective_capabilities),
        ]
    elif role == "b":
        probes = [
            ("P12", lambda: http_get("tenant-a", 8080, "/healthz")),
        ]
    results = []
    for probe_id, run in probes:
        try:
            outcome, detail = run()
        except Exception as exc:  # a probe must never crash the suite
            outcome, detail = "error", f"{type(exc).__name__}: {exc}"
        results.append({"id": probe_id, "outcome": outcome, "detail": detail})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suite")
    s.add_argument("--role", choices=["b", "c"], required=True)
    s.add_argument("--tenant-a-ip")
    g = sub.add_parser("http-get")
    g.add_argument("host")
    g.add_argument("port", type=int)
    g.add_argument("path")
    args = parser.parse_args()

    if args.cmd == "suite":
        doc = {"tenant": args.role, "probes": suite(args.role, args.tenant_a_ip)}
    else:
        outcome, detail = http_get(args.host, args.port, args.path)
        doc = {"outcome": outcome, "detail": detail}
    json.dump(doc, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
