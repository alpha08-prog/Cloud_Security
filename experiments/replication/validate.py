"""Classifier vs human labels (docs/replication.md §4).

A label item is {"id", "onTopic", "type", "categories": {cat: none|concern|solution}, "axes": {...}}.
Off-topic items count as "none" everywhere, and so do works the classifier puts out of scope:
the comparison is between the entries each side would actually count.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import config, metrics, taxonomy
from .classify import Result

NONE = "none"


def predicted(r: Result) -> dict:
    cats = {c: NONE for c in taxonomy.CATEGORIES}
    axes = {a: NONE for a in taxonomy.AXES}
    if r.in_scope:
        for c in r.categories("concern"):
            cats[c] = "concern"
        for c in r.categories("solution"):
            cats[c] = "solution"
        for a in r.axes_concern:
            axes[a] = "concern"
        for a in r.axes_solution:
            axes[a] = "solution"
    return {"onTopic": r.in_scope, "type": "solution" if r.kind == "solution" else "concern",
            "categories": cats, "axes": axes}


def gold(label: dict) -> dict:
    if not label["onTopic"]:
        return {"onTopic": False, "type": None, "categories": {c: NONE for c in taxonomy.CATEGORIES},
                "axes": {a: NONE for a in taxonomy.AXES}}
    return label


def _cells(golds: list[dict], preds: list[dict], weights: list[float]) -> dict:
    out: dict = {"gate": metrics.binary([g["onTopic"] for g in golds], [p["onTopic"] for p in preds], weights)}
    for which, test in (("concern", lambda v: v != NONE), ("solution", lambda v: v == "solution")):
        out[which] = {c: metrics.binary([test(g["categories"][c]) for g in golds],
                                        [test(p["categories"][c]) for p in preds], weights)
                      for c in taxonomy.CATEGORIES}
    out["axes"] = {a: metrics.binary([g["axes"][a] != NONE for g in golds], [p["axes"][a] != NONE for p in preds],
                                     weights) for a in taxonomy.AXES}
    on = [i for i, g in enumerate(golds) if g["onTopic"]]
    out["type_pairs"] = [(golds[i]["type"], preds[i]["type"]) for i in on]
    out["type_weights"] = [weights[i] for i in on]
    return out


def summary(golds: list[dict], preds: list[dict], weights: list[float]) -> dict:
    c = _cells(golds, preds, weights)
    kappas = [b.kappa for b in c["concern"].values() if b.kappa is not None]
    type_table: dict[str, float] = {}
    for (g, p), w in zip(c["type_pairs"], c["type_weights"], strict=True):
        type_table[f"{g}->{p}"] = type_table.get(f"{g}->{p}", 0.0) + w
    return {
        "gate": c["gate"].dump(),
        "concern": {k: b.dump() for k, b in c["concern"].items()},
        "solution": {k: b.dump() for k, b in c["solution"].items()},
        "axes": {k: b.dump() for k, b in c["axes"].items()},
        "macroF1": {"concern": metrics.macro_f1(list(c["concern"].values())),
                    "solution": metrics.macro_f1(list(c["solution"].values()))},
        "microF1": {"concern": metrics.micro_f1(list(c["concern"].values())),
                    "solution": metrics.micro_f1(list(c["solution"].values()))},
        "meanKappa": sum(kappas) / len(kappas) if kappas else None,
        "typeKappa": metrics.kappa(c["type_pairs"], c["type_weights"]),
        "typeConfusion": type_table,
        "offTopic": sum(w for g, w in zip(golds, weights, strict=True) if not g["onTopic"]),
    }


def gate(s: dict) -> dict:
    values = {"macro_f1": s["macroF1"]["concern"], "virtualization_f1": s["concern"]["virtualization"]["f1"],
              "mean_kappa": s["meanKappa"], "type_kappa": s["typeKappa"]}
    checks = {k: {"value": v, "threshold": config.GATE[k], "met": v is not None and v >= config.GATE[k]}
              for k, v in values.items()}
    return {"met": all(c["met"] for c in checks.values()), "checks": checks}


def compare(labels: Sequence[dict], results: dict[str, Result], weights: dict[str, float] | None = None) -> dict:
    items = list(labels)
    golds = [gold(i) for i in items]
    preds = [predicted(results[i["id"]]) for i in items]
    w = [weights[i["id"]] if weights else 1.0 for i in items]
    s = summary(golds, preds, w)
    s["validityGate"] = gate(s)
    s["n"] = len(items)
    return s


def disagreements(labels: Sequence[dict], results: dict[str, Result]) -> list[dict]:
    """Per-item differences, for reading the dev set while tuning."""
    out = []
    for label in labels:
        g, p = gold(label), predicted(results[label["id"]])
        diff = {}
        if g["onTopic"] != p["onTopic"]:
            diff["onTopic"] = (g["onTopic"], p["onTopic"])
        if g["onTopic"] and g["type"] != p["type"]:
            diff["type"] = (g["type"], p["type"])
        for c in taxonomy.CATEGORIES:
            if g["categories"][c] != p["categories"][c]:
                diff[c] = (g["categories"][c], p["categories"][c])
        if diff:
            out.append({"id": label["id"], "diff": diff})
    return out


# ---------------------------------------------------------------------------- the test sample


def _test_items(test: dict, labels: dict) -> tuple[list[dict], list[tuple[dict, dict]], list[str]]:
    """-> (first-shown answers as label items, repeat pairs, missing screens)."""
    answers = labels.get("labels", {})
    missing = [s["screen"] for s in test["screens"] if s["screen"] not in answers]
    first: dict[str, dict] = {}
    again: dict[str, dict] = {}
    for s in test["screens"]:
        a = answers.get(s["screen"])
        if a is None:
            continue
        (again if s["repeat"] else first)[s["id"]] = {"id": s["id"], **a}
    pairs = [(first[i], again[i]) for i in sorted(again) if i in first]
    return [first[i] for i in sorted(first)], pairs, missing


def self_agreement(pairs: list[tuple[dict, dict]]) -> dict:
    """The annotator against themself on the hidden repeats."""
    topic = [(a["onTopic"], b["onTopic"]) for a, b in pairs]
    both = [(gold(a), gold(b)) for a, b in pairs]
    cats = [(x["categories"][c] != NONE, y["categories"][c] != NONE) for x, y in both for c in taxonomy.CATEGORIES]
    kinds = [(a["type"], b["type"]) for a, b in pairs if a["onTopic"] and b["onTopic"]]
    return {"pairs": len(pairs),
            "onTopicAgreement": sum(a == b for a, b in topic) / len(topic) if topic else None,
            "categoryKappa": metrics.kappa(cats) if cats else None,
            "typeKappa": metrics.kappa(kinds) if kinds else None}


def validate_test_sample(test: dict, labels: dict, results: dict[str, Result], *, b: int | None = None,
                    seed: int | None = None) -> dict:
    from . import samples
    items, pairs, missing = _test_items(test, labels)
    if missing:
        raise ValueError(f"{len(missing)} test screens are not labelled yet")
    weights = samples.weights(test)
    weighted = compare(items, results, weights)
    unweighted = compare(items, results)
    golds = [gold(i) for i in items]
    preds = [predicted(results[i["id"]]) for i in items]
    w = [weights[i["id"]] for i in items]
    where = samples.stratum_of(test)
    strata: dict[str, list[int]] = {}
    for k, i in enumerate(items):
        strata.setdefault(where[i["id"]], []).append(k)

    def stat(name: str):
        def f(idx: list[int]) -> float | None:
            s = summary([golds[k] for k in idx], [preds[k] for k in idx], [w[k] for k in idx])
            return {"macroF1": s["macroF1"]["concern"], "virtualizationF1": s["concern"]["virtualization"]["f1"],
                    "meanKappa": s["meanKappa"], "typeKappa": s["typeKappa"]}[name]
        return f

    b = b or config.BOOTSTRAP_B
    seed = config.BOOTSTRAP_SEED if seed is None else seed
    ci = {}
    for name in ("macroF1", "virtualizationF1", "meanKappa", "typeKappa"):
        reps = metrics.stratified_bootstrap(strata, stat(name), b=b, seed=f"{seed}-validity-{name}")
        ci[name] = list(metrics.interval(reps)) if len(reps) >= b // 2 else None
    weighted["ci"] = ci
    return {"n": len(items), "screens": len(test["screens"]), "repeats": len(pairs),
            "unsure": sum(1 for i in items if i.get("unsure")), "completedAt": labels.get("completedAt"),
            "weighted": weighted, "unweighted": unweighted, "selfAgreement": self_agreement(pairs)}
