"""The blind labelling form: token and Host checks, validation, atomic save and resume."""

from __future__ import annotations

import http.client
import http.server
import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from replication import annotate  # noqa: E402

TOKEN = "tok-123"
SCREENS = ["s001", "s002", "s003"]
TEXTS = {s: (f"Title {s}", f"<b>Abstract</b> of {s}") for s in SCREENS}

SOLUTION = {"onTopic": True, "type": "solution", "unsure": False,
            "categories": {"data-security": "solution", "virtualization": "concern"},
            "axes": {"isolation": "concern"}}


@pytest.fixture()
def server(tmp_path):
    store = annotate.Store(tmp_path / "test.json", SCREENS)
    port_ref = [0]
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                            annotate.make_handler(store, TEXTS, TOKEN, port_ref))
    port_ref[0] = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield store, port_ref[0], tmp_path / "test.json"
    httpd.shutdown()
    httpd.server_close()


def call(port, method, path, body=None, *, token=TOKEN, host=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Host": host or f"127.0.0.1:{port}", "Content-Type": "application/json"}
    if token:
        headers["X-Token"] = token
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
    r = conn.getresponse()
    data = r.read()
    conn.close()
    return r.status, data


def test_page_needs_the_token_and_a_local_host(server):
    _, port, _ = server
    assert call(port, "GET", f"/?t={TOKEN}")[0] == 200
    assert call(port, "GET", "/?t=wrong")[0] == 403
    assert call(port, "GET", f"/?t={TOKEN}", host="evil.example:80")[0] == 403
    assert call(port, "GET", "/api/screen", token=None)[0] == 403


def test_screen_shows_only_title_and_abstract(server):
    _, port, _ = server
    status, data = call(port, "GET", "/api/screen")
    doc = json.loads(data)
    assert status == 200 and doc["n"] == 0 and doc["title"] == "Title s001"
    assert set(doc) == {"n", "total", "done", "finished", "title", "abstract", "answer"}


def test_save_is_atomic_validated_and_resumable(server):
    store, port, path = server
    status, data = call(port, "POST", "/api/save", {"n": 0, "answer": SOLUTION})
    assert status == 200 and json.loads(data)["next"] == 1
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["labels"]["s001"]["categories"]["data-security"] == "solution"
    assert saved["labels"]["s001"]["axes"]["isolation"] == "concern"
    assert not list(path.parent.glob(".test-*"))  # no temp files left behind

    bad = {**SOLUTION, "type": "concern"}  # concern-only cannot mark a solution
    assert call(port, "POST", "/api/save", {"n": 1, "answer": bad})[0] == 400
    assert call(port, "POST", "/api/save", {"n": 9, "answer": SOLUTION})[0] == 400
    assert call(port, "POST", "/api/save", {"n": 1, "answer": SOLUTION}, token="wrong")[0] == 403

    call(port, "POST", "/api/save", {"n": 1, "answer": {"onTopic": False}})
    resumed = annotate.Store(path, SCREENS)
    assert resumed.done() == 2 and resumed.first_open() == 2
    assert json.loads(call(port, "GET", "/api/screen")[1])["n"] == 2


def test_clean_normalises_implied_fields():
    off = annotate.clean({"onTopic": False, "type": "solution"})
    assert off == {"onTopic": False, "unsure": False}
    a = annotate.clean({"onTopic": True, "type": "concern", "categories": {"virtualization": "none"},
                        "axes": {"isolation": "concern"}})
    assert a["axes"]["isolation"] == "none"  # sub-issues only count under a marked virtualization
    with pytest.raises(annotate.AnswerError):
        annotate.clean({"onTopic": True, "type": "solution", "categories": {"virtualization": "concern"},
                        "axes": {"isolation": "solution"}})
