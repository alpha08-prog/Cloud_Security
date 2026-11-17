"""Agreement metrics and bootstraps (docs/replication.md §4-§5). Standard library only.

Every function takes optional weights so the same code gives design-weighted values for the
stratified test sample (weight N_h / n_h) and plain values for the dev set (weight 1).
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass


@dataclass
class Binary:
    tp: float
    fp: float
    fn: float
    tn: float

    @property
    def n(self) -> float:
        return self.tp + self.fp + self.fn + self.tn

    @property
    def precision(self) -> float | None:
        d = self.tp + self.fp
        return self.tp / d if d else None

    @property
    def recall(self) -> float | None:
        d = self.tp + self.fn
        return self.tp / d if d else None

    @property
    def f1(self) -> float | None:
        d = 2 * self.tp + self.fp + self.fn
        return 2 * self.tp / d if d else None

    @property
    def kappa(self) -> float | None:
        return kappa((), table={(True, True): self.tp, (False, True): self.fp, (True, False): self.fn,
                                (False, False): self.tn})

    def dump(self) -> dict:
        return {**asdict(self), "precision": self.precision, "recall": self.recall, "f1": self.f1,
                "kappa": self.kappa}


def binary(gold: Sequence[bool], pred: Sequence[bool], weights: Sequence[float] | None = None) -> Binary:
    w = weights or [1.0] * len(gold)
    tp = fp = fn = tn = 0.0
    for g, p, wi in zip(gold, pred, w, strict=True):
        if g and p:
            tp += wi
        elif p:
            fp += wi
        elif g:
            fn += wi
        else:
            tn += wi
    return Binary(tp, fp, fn, tn)


def kappa(pairs: Sequence[tuple[object, object]], weights: Sequence[float] | None = None,
          table: dict[tuple[object, object], float] | None = None) -> float | None:
    """Cohen's kappa for two raters over any label set. `pairs` are (gold, pred); `table`
    maps (gold, pred) -> weight and is used instead when given. None when undefined (one class)."""
    if table is None:
        table = {}
        for (g, p), wi in zip(pairs, weights or [1.0] * len(pairs), strict=True):
            table[(g, p)] = table.get((g, p), 0.0) + wi
    total = sum(table.values())
    if not total:
        return None
    labels = {g for g, _ in table} | {p for _, p in table}
    po = sum(v for (g, p), v in table.items() if g == p) / total
    pe = sum((sum(v for (g, _), v in table.items() if g == k) / total)
             * (sum(v for (_, p), v in table.items() if p == k) / total) for k in labels)
    if math.isclose(pe, 1.0):
        return None
    return (po - pe) / (1 - pe)


def macro_f1(results: Sequence[Binary]) -> float | None:
    f = [r.f1 for r in results if r.f1 is not None]
    return sum(f) / len(f) if f else None


def micro_f1(results: Sequence[Binary]) -> float | None:
    return Binary(sum(r.tp for r in results), sum(r.fp for r in results), sum(r.fn for r in results),
                  sum(r.tn for r in results)).f1


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile (numpy's default), q in [0, 100]."""
    s = sorted(values)
    if not s:
        raise ValueError("empty")
    k = (len(s) - 1) * q / 100
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def interval(values: Sequence[float], level: float = 95.0) -> tuple[float, float]:
    a = (100 - level) / 2
    return percentile(values, a), percentile(values, 100 - a)


def stratified_bootstrap(strata: dict[str, list[int]], stat: Callable[[list[int]], float | None], *, b: int,
                         seed: int | str) -> list[float]:
    """Resample item indices with replacement inside each stratum; return the B statistics
    that are defined. Strata are visited in sorted order so the result depends only on the seed."""
    rng = random.Random(seed)
    keys = sorted(strata)
    out = []
    for _ in range(b):
        idx: list[int] = []
        for k in keys:
            members = strata[k]
            idx += [members[rng.randrange(len(members))] for _ in members]
        v = stat(idx)
        if v is not None:
            out.append(v)
    return out
