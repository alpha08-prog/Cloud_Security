"""The classifier freeze (docs/replication.md §3): the rules are hashed before the test set is
drawn, and every later step refuses to run against different rules."""

from __future__ import annotations

from pathlib import Path

from isolab import util

from . import config, snapshot

HERE = Path(__file__).resolve().parent
FROZEN = ("lexicon.py", "classify.py")


class FreezeError(util.CommandError):
    pass


def hashes() -> dict[str, str]:
    return {name: snapshot.file_sha256_lf(HERE / name) for name in FROZEN}


def inputs() -> dict[str, str]:
    """The data the frozen rules were tuned on, recorded next to them."""
    out = {}
    for path in (config.CORPUS / "manifest.json", config.NVD / "manifest.json", config.SAMPLES / "dev.json",
                 config.SAMPLES / "dev-virt.json", config.LABELS / "dev.json", config.LABELS / "dev-virt.json"):
        out[path.relative_to(util.REPO).as_posix()] = snapshot.file_sha256_lf(path)
    return out


def load() -> dict | None:
    return util.read_json(config.FREEZE) if config.FREEZE.exists() else None


def write() -> dict:
    if config.FREEZE.exists():
        raise FreezeError(f"{config.FREEZE.relative_to(util.REPO)} exists; the classifier is already frozen")
    doc = {"frozenAt": util.utc_now(), "files": hashes(), "inputs": inputs()}
    util.write_json(config.FREEZE, doc)
    return doc


def check() -> dict:
    """Raise unless the rules on disk are the frozen ones."""
    doc = load()
    if doc is None:
        raise FreezeError("the classifier is not frozen yet: run `lab.py rep freeze` first")
    now = hashes()
    changed = [name for name, digest in doc["files"].items() if now.get(name) != digest]
    if changed:
        raise FreezeError(f"frozen rules changed since {doc['frozenAt']}: {', '.join(changed)} "
                          "(revert them, or log a deviation in docs/replication.md before re-freezing)")
    return doc
