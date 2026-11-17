"""Dev and test samples (docs/replication.md §2 and §4)."""

from __future__ import annotations

import random

from isolab import util

from . import config
from .corpus import Work


def draw_dev(works: list[Work]) -> list[str]:
    ids = []
    for era in config.ERAS:
        pool = sorted(w.id for w in works if w.era == era)
        ids += random.Random(f"dev-{config.DEV_SEED}-{era}").sample(pool, config.DEV_PER_ERA)
    return ids


def save(name: str, doc: dict) -> None:
    util.write_json(config.SAMPLES / f"{name}.json", doc)


def load(name: str) -> dict | None:
    path = config.SAMPLES / f"{name}.json"
    return util.read_json(path) if path.exists() else None


STRATA = ("A", "B", "C")  # A: in scope + virtualization, B: in scope other, C: gate failed


def stratum(r) -> str:
    if not r.in_scope:
        return "C"
    return "A" if "virtualization" in r.categories() else "B"


def draw_test(works: list[Work], results: dict) -> dict:
    """The validation sample (docs/replication.md §4): stratified per era by classifier output,
    from analysed works outside both dev sets, plus hidden repeats, shown under opaque screen ids
    in a shuffled order."""
    excluded = set(load("dev")["ids"]) | set(load("dev-virt")["ids"])
    strata: dict[str, dict] = {}
    chosen: list[str] = []
    for era, sizes in config.TEST_STRATA.items():
        strata[era] = {}
        for name, n in zip(STRATA, sizes, strict=True):
            pool = sorted(w.id for w in works if w.era == era and w.id not in excluded
                          and stratum(results[w.id]) == name)
            ids = random.Random(f"test-{config.TEST_SEED}-{era}-{name}").sample(pool, n)
            strata[era][name] = {"N": len(pool), "n": n, "ids": ids}
            chosen += ids
    rng = random.Random(f"test-{config.TEST_SEED}-screens")
    repeats = rng.sample(sorted(chosen), config.TEST_REPEATS)
    items = [(i, False) for i in chosen] + [(i, True) for i in repeats]
    rng.shuffle(items)
    # A repeat is never shown within 10 screens of its first showing.
    for _ in range(1000):
        pos = {}
        clash = False
        for k, (i, _rep) in enumerate(items):
            if i in pos and k - pos[i] <= 10:
                clash = True
                break
            pos.setdefault(i, k)
        if not clash:
            break
        rng.shuffle(items)
    screens = [{"screen": f"s{k + 1:03d}", "id": i, "repeat": rep} for k, (i, rep) in enumerate(items)]
    return {"seed": config.TEST_SEED, "drawnAt": util.utc_now(), "strata": strata, "repeats": repeats,
            "screens": screens}


def weights(test: dict) -> dict[str, float]:
    """Inverse-probability weight N_h / n_h for every first-shown work."""
    return {i: s["N"] / s["n"] for era in test["strata"].values() for s in era.values() for i in s["ids"]}


def stratum_of(test: dict) -> dict[str, str]:
    return {i: f"{era}/{name}" for era, strata in test["strata"].items() for name, s in strata.items()
            for i in s["ids"]}
