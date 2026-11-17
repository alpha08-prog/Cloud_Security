"""The descriptive CVE supplement (docs/replication.md §6): virtualization-related CVEs per year,
per 10,000 published CVEs, from the committed NVD snapshot."""

from __future__ import annotations

import random
import re
from collections import Counter, defaultdict

from isolab import util

from . import classify, config, samples, snapshot

AXES = ["virtualization-layer", "isolation", "cross-vm-attacks", "data-leakage"]
SPOT_PER_AXIS = 20

# Deviation D1 (docs/replication.md changelog, after the freeze): Linux-kernel CVE texts embed
# syzkaller/KASAN crash dumps whose "Hardware name: QEMU Standard PC" line names the VM the fuzzer
# ran on, not the affected component. The dump is cut off before classification.
KERNEL = "In the Linux kernel, the following vulnerability has been resolved"
CRASH_DUMP = re.compile(r"^[ \t]*(?:\[\s*\d+\.\d+\s*\]|BUG:|WARNING:|Call Trace:|Hardware name:|CPU: \d|RIP:|Oops"
                        r"|-+\[ cut here \]|==+|Modules linked in:|Workqueue:|general protection fault|kernel BUG|\? )",
                        re.MULTILINE)


def description(text: str) -> str:
    if not text.startswith(KERNEL):
        return text
    m = CRASH_DUMP.search(text)
    return text[:m.start()] if m else text


def load() -> tuple[list[dict], list[dict], dict]:
    candidates, digest = snapshot.read_jsonl_gz(config.NVD / "candidates.jsonl.gz")
    manifest = util.read_json(config.NVD / "manifest.json")
    if digest != manifest["sha256"]:
        raise util.CommandError("replication/nvd/candidates.jsonl.gz does not match its manifest")
    totals = util.read_json(config.NVD / "totals.json")
    unique = {c["id"]: c for c in candidates}
    return [unique[k] for k in sorted(unique)], totals, manifest


def tagged(candidates: list[dict], *, strip_dumps: bool = True) -> dict[str, list[str]]:
    prep = description if strip_dumps else (lambda t: t)
    return {c["id"]: classify.classify_cve(prep(c["description"])) for c in candidates}


def series(candidates: list[dict], totals: list[dict], tags: dict[str, list[str]], retrieved: str) -> list[dict]:
    per_year: dict[int, int] = defaultdict(int)
    for q in totals:
        per_year[int(q["start"][:4])] += q["total"]
    counts: dict[int, Counter] = defaultdict(Counter)
    for c in candidates:
        year = int(c["published"][:4])
        if year < config.NVD_FIRST_YEAR:
            continue
        for a in tags[c["id"]]:
            counts[year][a] += 1
        if tags[c["id"]]:
            counts[year]["any"] += 1
    last = int(retrieved[:4])
    rows = []
    for year in range(config.NVD_FIRST_YEAR, last + 1):
        total = per_year.get(year, 0)
        cnt = {a: counts[year][a] for a in [*AXES, "any"]}
        rows.append({"year": year, "total": total, "partial": year == last, "counts": cnt,
                     "per10k": {a: round(10_000 * n / total, 2) if total else None for a, n in cnt.items()}})
    return rows


def draw_spot(tags: dict[str, list[str]], candidates: list[dict]) -> dict:
    eligible = {c["id"] for c in candidates if int(c["published"][:4]) >= config.NVD_FIRST_YEAR}
    out = {}
    for a in AXES:
        pool = sorted(i for i, t in tags.items() if a in t and i in eligible)
        out[a] = random.Random(f"cve-spot-{a}").sample(pool, min(SPOT_PER_AXIS, len(pool)))
    return {"perAxis": SPOT_PER_AXIS, "drawnAt": util.utc_now(), "ids": out}


def spot_precision(spot: dict, labels: dict, tags: dict[str, list[str]]) -> dict[str, dict]:
    """Precision per axis on the spot sample, for the frozen rule and with D1. D1 only removes tags,
    so the sampled items it keeps are a random sample of what it tags."""
    out = {}
    for a, ids in spot["ids"].items():
        judged = labels["labels"].get(a, {})
        frozen = [judged[i] for i in ids if i in judged]
        kept = [judged[i] for i in ids if i in judged and a in tags[i]]
        out[a] = {"n": len(frozen), "correct": sum(frozen),
                  "precision": round(sum(frozen) / len(frozen), 2) if frozen else None,
                  "nWithD1": len(kept), "correctWithD1": sum(kept),
                  "precisionWithD1": round(sum(kept) / len(kept), 2) if kept else None}
    return out


def analyse() -> dict:
    candidates, totals, manifest = load()
    tags = tagged(candidates)
    spot = samples.load("cve-spot")
    labels_path = config.LABELS / "cve-spot.json"
    precision = spot_precision(spot, util.read_json(labels_path), tags) if spot and labels_path.exists() else None
    return {"source": manifest["source"], "retrievedAt": manifest["retrievedAt"], "sha256": manifest["sha256"],
            "candidates": len(candidates), "axes": AXES, "notMeasured": ["vm-identification"],
            "deviations": ["D1: kernel crash dumps removed before classification"],
            "years": series(candidates, totals, tags, manifest["retrievedAt"]), "spotCheck": precision}
