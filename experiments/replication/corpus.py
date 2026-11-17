"""Load the committed OpenAlex snapshot, rebuild abstracts and apply the pre-registered
normalisation, exclusions and de-duplication (docs/replication.md §2)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import config, snapshot

STUBS = re.compile(r"abstract (is )?not available|no abstract|this article has been retracted|"
                   r"retraction notice|^\W*abstract\W*$", re.IGNORECASE)


@dataclass
class Work:
    id: str
    era: str
    year: int
    type: str
    title: str
    abstract: str
    venue: str | None
    publisher: str | None


@dataclass
class Flow:
    era: str
    population: int
    sampled: int
    unique: int
    excluded: dict[str, int] = field(default_factory=dict)
    analysed: int = 0


def rebuild_abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    positions = sorted((p, word) for word, ps in inverted.items() for p in ps)
    return " ".join(word for _, word in positions).replace("�", " ")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def load(era: str) -> tuple[list[Work], Flow]:
    records, _ = snapshot.read_jsonl_gz(config.CORPUS / f"openalex-{era}.jsonl.gz")
    manifest = __import__("json").loads((config.CORPUS / "manifest.json").read_text(encoding="utf-8"))
    flow = Flow(era=era, population=manifest["eras"][era]["population"], sampled=len(records),
                unique=len({r["id"] for r in records}))
    by_id: dict[str, dict] = {}
    for r in records:
        by_id.setdefault(r["id"], r)
    works: list[Work] = []
    seen: dict[str, Work] = {}
    excluded = {"no abstract": 0, "too short": 0, "too long": 0, "stub": 0, "duplicate": 0}
    # Deterministic order: by id, so the duplicate rule ("keep the non-preprint, earliest, lowest id") is stable.
    for r in sorted(by_id.values(), key=lambda r: r["id"]):
        abstract = rebuild_abstract(r.get("abstract_inverted_index"))
        words = len(abstract.split())
        if not abstract:
            excluded["no abstract"] += 1
            continue
        if STUBS.search(abstract[:200]):
            excluded["stub"] += 1
            continue
        if words < config.MIN_WORDS:
            excluded["too short"] += 1
            continue
        if words > config.MAX_WORDS:
            excluded["too long"] += 1
            continue
        loc = r.get("primary_location") or {}
        src = loc.get("source") or {}
        work = Work(id=r["id"].rsplit("/", 1)[-1], era=era, year=int(r.get("publication_year") or 0),
                    type=r.get("type") or "", title=(r.get("title") or "").strip(), abstract=abstract,
                    venue=src.get("display_name"), publisher=src.get("host_organization_name"))
        key = _norm(work.title) + "|" + _norm(abstract)[:100]
        if key in seen:
            excluded["duplicate"] += 1
            other = seen[key]
            better = (work.type != "preprint", -work.year) > (other.type != "preprint", -other.year)
            if better:
                works[works.index(other)] = work
                seen[key] = work
            continue
        seen[key] = work
        works.append(work)
    flow.excluded = excluded
    flow.analysed = len(works)
    return works, flow


def load_all() -> tuple[list[Work], list[Flow]]:
    works, flows = [], []
    for era in config.ERAS:
        w, f = load(era)
        works.extend(w)
        flows.append(f)
    return works, flows
