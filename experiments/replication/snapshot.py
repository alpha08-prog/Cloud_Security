"""Deterministic JSONL(.gz) snapshots. The hash is taken over the *uncompressed* bytes,
because gzip output differs between zlib builds (e.g. zlib-ng on Windows)."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path


def dumps_jsonl(records: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records).encode("utf-8")


def write_jsonl_gz(path: Path, records: list[dict]) -> str:
    raw = dumps_jsonl(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    path.write_bytes(buf.getvalue())
    return hashlib.sha256(raw).hexdigest()


def read_jsonl_gz(path: Path) -> tuple[list[dict], str]:
    raw = gzip.decompress(path.read_bytes())
    records = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return records, hashlib.sha256(raw).hexdigest()


def file_sha256_lf(path: Path) -> str:
    """sha256 of a text file with line endings normalised to LF (stable across checkouts)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
