"""Run-level comparison metrics. No synthetic results are publishable here."""
from __future__ import annotations

import math
import random
import statistics


def confusion(labels, predictions):
    if not labels or len(labels) != len(predictions):
        raise ValueError("Nonempty aligned observations required")
    if any(x not in (0, 1) for x in [*labels, *predictions]):
        raise ValueError("Binary observations required")
    counts = {key: 0 for key in ("tp", "tn", "fp", "fn")}
    for actual, predicted in zip(labels, predictions):
        counts[{(1, 1): "tp", (0, 0): "tn", (0, 1): "fp", (1, 0): "fn"}[actual, predicted]] += 1
    tp, tn, fp, fn = (counts[k] for k in ("tp", "tn", "fp", "fn"))
    def ratio(a, b):
        return a / b if b else None
    return dict(counts, precision=ratio(tp, tp + fp), recall=ratio(tp, tp + fn),
                falsePositiveRate=ratio(fp, fp + tn), f1=ratio(2 * tp, 2 * tp + fp + fn))


def split_runs(run_ids, seed=20261117):
    """Paper's 40/30/30 split, by independent execution, never by window."""
    ids = sorted(set(run_ids))
    if len(ids) != len(run_ids) or len(ids) < 10:
        raise ValueError("At least ten unique independent runs required")
    random.Random(seed).shuffle(ids)
    train, validation = int(.4 * len(ids)), int(.3 * len(ids))
    return {r: ("train" if i < train else "validation" if i < train + validation else "test")
            for i, r in enumerate(ids)}


def median_interval(values, seed=20261117, draws=10000):
    """Percentile bootstrap of independent run summaries (not requests)."""
    if len(values) < 2 or not all(math.isfinite(v) for v in values):
        raise ValueError("Two or more finite independent run values required")
    rng = random.Random(seed)
    estimates = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(draws))
    return {"median": statistics.median(values), "low": estimates[int(.025 * draws)],
            "high": estimates[min(draws - 1, int(.975 * draws))], "n": len(values)}


def validate_predictions(rows):
    seen, splits = set(), {}
    for row in rows:
        key = (row["method"], row["runId"], row["timestamp"])
        if key in seen:
            raise ValueError("Duplicate prediction")
        seen.add(key)
        if row["split"] not in ("train", "validation", "test"):
            raise ValueError("Unknown split")
        previous = splits.setdefault(row["runId"], row["split"])
        if previous != row["split"]:
            raise ValueError("Run leakage across splits")
        if not math.isfinite(row["score"]) or not 0 <= row["score"] <= 1:
            raise ValueError("Invalid probability")
        if row["label"] not in (0, 1):
            raise ValueError("Invalid label")
    methods = {r["method"] for r in rows}
    observations = [{(r["runId"], r["timestamp"], r["label"], r["split"])
                     for r in rows if r["method"] == method} for method in methods]
    if not observations or any(items != observations[0] for items in observations):
        raise ValueError("Methods must evaluate identical observations")
