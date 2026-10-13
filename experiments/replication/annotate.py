"""`lab.py rep annotate`: the blind labelling form (docs/replication.md §4).

A local web form on 127.0.0.1 only. The browser gets one screen at a time (title + abstract,
nothing else: no year, venue, id, stratum or classifier output). Every answer is written
atomically to replication/labels/test.json, keyed by opaque screen ids, so the session can be
closed and resumed at any point.

Requests must carry the session token (printed in the URL) and a Host header naming this server,
which keeps other pages and DNS-rebinding tricks from reading or writing labels.
"""

from __future__ import annotations

import http.server
import json
import os
import secrets
import tempfile
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from isolab import util

from . import config, samples, taxonomy
from .corpus import Work

LABELS = config.LABELS / "test.json"
PAGE = Path(__file__).with_name("annotate.html")

GUIDELINES = [
    "Judge only the title and abstract. Do not look the paper up.",
    "Off topic if the work is not about the security, privacy or compliance of cloud computing. "
    "Edge or fog computing that uses a cloud counts.",
    "Proposes a solution if the authors present their own scheme, system, framework, protocol, method, tool, "
    "architecture or policy that addresses a security, privacy or compliance problem, including detection and "
    "mitigation. Surveys, reviews, attack papers without a countermeasure, measurement studies and position "
    "papers are concern only.",
    "Per category: Concern when the abstract raises a specific problem in that category (a generic "
    "'security and privacy' phrase does not count); Solution when the proposed contribution addresses it "
    "(Solution implies Concern).",
    "Virtualization sub-issues: mark them only when Virtualization is marked.",
    "When unsure, choose the less specific option and tick 'unsure'.",
]

CATEGORIES = [
    ("network-security", "Network security", "transfer, firewalling / IDS / DoS, security configuration"),
    ("interfaces", "Interfaces", "API, administrative interface, user interface, authentication / access control"),
    ("data-security", "Data security", "cryptography / confidentiality, redundancy / integrity / backup, "
                                       "disposal / deletion"),
    ("virtualization", "Virtualization", "see the sub-issues below"),
    ("governance", "Governance", "data control, security control / risk management, lock-in / portability"),
    ("compliance", "Compliance", "SLA, loss of service / availability, audit / accountability, "
                                 "service conformity / certification"),
    ("legal-issues", "Legal issues", "data location / jurisdiction, e-discovery / forensics, "
                                     "provider privilege / insiders, legislation / regulation"),
]
AXES = [
    ("hypervisor-vulnerabilities", "Hypervisor vulnerabilities",
     "flaws in the hypervisor, VMM, container runtime or shared kernel"),
    ("isolation", "Isolation", "separation between VMs / tenants / containers, escape, noisy neighbour, TEEs"),
    ("cross-vm-attacks", "Cross-VM attacks", "one tenant attacking a co-resident tenant, side channels, placement"),
    ("data-leakage", "Data leakage", "data crossing a VM / tenant boundary"),
    ("vm-identification", "VM identification", "identifying, attributing or attesting workloads"),
]
assert [c for c, _, _ in CATEGORIES] and {c for c, _, _ in CATEGORIES} == set(taxonomy.CATEGORIES)
assert {a for a, _, _ in AXES} == set(taxonomy.AXES)

VALUES = ("none", "concern", "solution")


class AnswerError(ValueError):
    pass


def clean(answer: dict) -> dict:
    """Validate one answer from the form and normalise the implied fields."""
    if not isinstance(answer, dict) or not isinstance(answer.get("onTopic"), bool):
        raise AnswerError("onTopic must be true or false")
    unsure = bool(answer.get("unsure", False))
    if not answer["onTopic"]:
        return {"onTopic": False, "unsure": unsure}
    kind = answer.get("type")
    if kind not in ("solution", "concern"):
        raise AnswerError("type must be 'solution' or 'concern'")
    cats = answer.get("categories") or {}
    axes = answer.get("axes") or {}
    out_c = {c: cats.get(c, "none") for c in taxonomy.CATEGORIES}
    out_a = {a: axes.get(a, "none") for a in taxonomy.AXES}
    for v in (*out_c.values(), *out_a.values()):
        if v not in VALUES:
            raise AnswerError(f"bad value {v!r}")
    if kind == "concern" and "solution" in (*out_c.values(), *out_a.values()):
        raise AnswerError("a concern-only abstract cannot mark a solution")
    if out_c["virtualization"] == "none":
        out_a = {a: "none" for a in out_a}
    elif out_c["virtualization"] == "concern" and "solution" in out_a.values():
        raise AnswerError("a virtualization sub-issue cannot be a solution when virtualization is concern-only")
    return {"onTopic": True, "type": kind, "categories": out_c, "axes": out_a, "unsure": unsure}


class Store:
    """replication/labels/test.json, written atomically after every answer."""

    def __init__(self, path: Path, screens: list[str]):
        self.path, self.screens, self.lock = path, screens, threading.Lock()
        if path.exists():
            self.doc = util.read_json(path)
        else:
            self.doc = {"sample": "test", "annotator": "project author (blind, see docs/replication.md §4)",
                        "startedAt": util.utc_now(), "labels": {}}

    def answer(self, screen: str) -> dict | None:
        return self.doc["labels"].get(screen)

    def done(self) -> int:
        return sum(1 for s in self.screens if s in self.doc["labels"])

    def first_open(self) -> int:
        return next((k for k, s in enumerate(self.screens) if s not in self.doc["labels"]), len(self.screens))

    def save(self, screen: str, answer: dict) -> None:
        with self.lock:
            self.doc["labels"][screen] = {**clean(answer), "savedAt": util.utc_now()}
            self.doc["updatedAt"] = util.utc_now()
            if self.done() == len(self.screens):
                self.doc.setdefault("completedAt", util.utc_now())
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".test-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                json.dump(self.doc, f, indent=2)
                f.write("\n")
            os.replace(tmp, self.path)


def make_handler(store: Store, texts: dict[str, tuple[str, str]], token: str, port_ref: list[int]):
    page = PAGE.read_text(encoding="utf-8").replace("__GUIDELINES__", json.dumps(GUIDELINES)).replace(
        "__CATEGORIES__", json.dumps(CATEGORIES)).replace("__AXES__", json.dumps(AXES))

    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "rep-annotate"

        def log_message(self, fmt, *args):  # keep the terminal quiet
            pass

        def _allowed(self) -> bool:
            port = port_ref[0]
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
                return False
            return True

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                             "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, doc: object) -> None:
            self._send(code, json.dumps(doc).encode("utf-8"), "application/json; charset=utf-8")

        def _screen(self, k: int) -> dict:
            total = len(store.screens)
            if k >= total:
                return {"n": total, "total": total, "done": store.done(), "finished": True}
            screen = store.screens[k]
            title, abstract = texts[screen]
            return {"n": k, "total": total, "done": store.done(), "finished": False, "title": title,
                    "abstract": abstract, "answer": store.answer(screen)}

        def do_GET(self):  # noqa: N802
            if not self._allowed():
                return self._send(403, b"forbidden", "text/plain")
            url = urlparse(self.path)
            if url.path == "/":
                if parse_qs(url.query).get("t") != [token]:
                    return self._send(403, b"missing or wrong token: use the URL printed in the terminal",
                                      "text/plain")
                return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
            if self.headers.get("X-Token") != token:
                return self._json(403, {"error": "token"})
            if url.path == "/api/screen":
                q = parse_qs(url.query).get("n", [""])[0]
                k = int(q) if q.isdigit() else store.first_open()
                return self._json(200, self._screen(min(k, len(store.screens))))
            return self._json(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            if not self._allowed() or self.headers.get("X-Token") != token:
                return self._json(403, {"error": "forbidden"})
            if urlparse(self.path).path != "/api/save":
                return self._json(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > 64_000:
                return self._json(413, {"error": "too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                k = int(body["n"])
                if not 0 <= k < len(store.screens):
                    raise AnswerError("no such screen")
                store.save(store.screens[k], body["answer"])
            except (AnswerError, KeyError, TypeError, ValueError) as e:
                return self._json(400, {"error": str(e)})
            nxt = k + 1 if k + 1 < len(store.screens) and store.screens[k + 1] in store.doc["labels"] \
                else store.first_open()
            return self._json(200, {"ok": True, "next": nxt, "done": store.done()})

    return Handler


def serve(works: list[Work], *, port: int = 8765, open_browser: bool = True) -> None:
    test = samples.load("test")
    if test is None:
        raise SystemExit("no test sample yet: run `lab.py rep sample` after the freeze")
    by_id = {w.id: w for w in works}
    screens = [s["screen"] for s in test["screens"]]
    texts = {s["screen"]: (by_id[s["id"]].title, by_id[s["id"]].abstract) for s in test["screens"]}
    store = Store(LABELS, screens)
    token = secrets.token_urlsafe(24)
    port_ref = [port]
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), make_handler(store, texts, token, port_ref))
    port_ref[0] = httpd.server_address[1]
    url = f"http://127.0.0.1:{port_ref[0]}/?t={token}"
    util.ok(f"annotation form: {url}")
    util.info(f"{store.done()}/{len(screens)} screens labelled so far; answers save as you go to "
              f"{LABELS.relative_to(util.REPO).as_posix()}. Ctrl+C stops the server; run the command again to resume.")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        util.info(f"stopped with {store.done()}/{len(screens)} screens labelled")
