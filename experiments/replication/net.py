"""Polite HTTP for public APIs: spacing, retries with back-off, and an on-disk page cache
so long fetches can be resumed. Standard library only."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from isolab import util

USER_AGENT = "IsoLab-replication/1.0 (+https://github.com/alpha08-prog/Cloud_Security)"
_last_call: dict[str, float] = {}


def get_json(url: str, *, cache_dir: Path | None, min_interval: float, headers: dict | None = None,
             retries: int = 8) -> dict:
    """GET a JSON document, waiting `min_interval` s between calls to the same host."""
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    cached = cache_dir / f"{key}.json" if cache_dir else None
    if cached and cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    host = urllib.parse.urlsplit(url).netloc
    delay = 2.0
    for attempt in range(retries):
        wait = _last_call.get(host, 0) + min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                doc = json.loads(r.read().decode("utf-8"))
            if cached:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_text(json.dumps(doc), encoding="utf-8")
            return doc
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                retry_after = exc.headers.get("Retry-After")
                pause = float(retry_after) if retry_after and retry_after.isdigit() else delay
                util.warn(f"HTTP {exc.code} from {host}; retrying in {pause:.0f}s")
                time.sleep(pause)
                delay = min(delay * 2, 120)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < retries - 1:
                util.warn(f"{type(exc).__name__} talking to {host}; retrying in {delay:.0f}s")
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            raise
    raise RuntimeError("unreachable")
