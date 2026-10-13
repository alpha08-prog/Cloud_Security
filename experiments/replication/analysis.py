"""Shares, intervals, robustness checks and hypothesis verdicts (docs/replication.md §5).

Each in-scope abstract becomes a sparse vector of entry counts: concern and solution entries per
category for the main counting rule and for every robustness variant, plus the Figure-11
sub-issues. The cluster bootstrap resamples abstracts (all analysed works, with replacement)
within each era, sums the vectors once per replicate, and derives every share, gap and ratio
from those sums, so all variants are compared on the same resamples.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence

from . import config, metrics, taxonomy
from .classify import Result
from .corpus import Flow, Work

CATS = taxonomy.CATEGORIES
AXES = taxonomy.AXES
VIRT = "virtualization"
VIRT_ROWS = {"Isolation", "Hypervisor vulnerabilities"}
VARIANTS = {
    "main": "Rule B (scoped solutions), per (abstract, sub-category)",
    "RB1": "per (abstract, category) instead of per sub-category",
    "RB2": "rule A: a solution abstract answers every concern it raises",
    "RB3": "classic virtualization only (no container, serverless or TEE sentences)",
    "RB4": "peer-reviewed types only (article, conference paper, review)",
}
HR4_GROUPS = (("isolation", "cross-vm-attacks"), ("hypervisor-vulnerabilities", "data-leakage", "vm-identification"))

# Dense layout of the per-abstract vector: (block, size).
BLOCKS = [(f"{v}.{side}", len(CATS)) for v in VARIANTS for side in ("c", "s")] + [("axes.c", len(AXES)),
                                                                                    ("axes.s", len(AXES))]
OFFSET: dict[str, int] = {}
_o = 0
for _name, _size in BLOCKS:
    OFFSET[_name] = _o
    _o += _size
DIM = _o


def _per_category(subs: Sequence[str], presence: bool = False) -> list[int]:
    v = [0] * len(CATS)
    for s in subs:
        v[CATS.index(taxonomy.category_of(s))] += 1
    return [min(x, 1) for x in v] if presence else v


def _fold(axes: Sequence[str]) -> list[str]:
    return sorted({taxonomy.FOLD[a] for a in axes})


def vectors(work: Work, r: Result) -> dict[str, list[int]]:
    """Entry counts of one abstract per block (empty when out of scope)."""
    if not r.in_scope:
        return {}
    main_c, main_s = _per_category(r.concern), _per_category(r.solution)
    nonvirt = [s for s in r.concern if s not in VIRT_ROWS]
    nonvirt_s = [s for s in r.solution if s not in VIRT_ROWS]
    zeros = [0] * len(CATS)
    peer = work.type in config.PEER_REVIEWED
    return {
        "main.c": main_c, "main.s": main_s,
        "RB1.c": _per_category(r.concern, True), "RB1.s": _per_category(r.solution, True),
        "RB2.c": main_c, "RB2.s": _per_category(r.broadcast_solution),
        "RB3.c": _per_category(nonvirt + _fold(r.classic_axes)),
        "RB3.s": _per_category(nonvirt_s + _fold(r.classic_axes_solution)),
        "RB4.c": main_c if peer else zeros, "RB4.s": main_s if peer else zeros,
        "axes.c": [int(a in r.axes_concern) for a in AXES], "axes.s": [int(a in r.axes_solution) for a in AXES],
    }


def sparse(blocks: dict[str, list[int]]) -> list[tuple[int, int]]:
    return [(OFFSET[name] + i, v) for name, vals in blocks.items() for i, v in enumerate(vals) if v]


def _sum(units: list[list[tuple[int, int]]], counts: Counter | None = None) -> list[float]:
    acc = [0.0] * DIM
    for i, u in enumerate(units):
        c = 1 if counts is None else counts.get(i, 0)
        if c and u:
            for d, v in u:
                acc[d] += c * v
    return acc


def replicates(units: list[list[tuple[int, int]]], *, b: int, seed: str) -> list[list[float]]:
    rng = random.Random(seed)
    n = len(units)
    index = range(n)
    return [_sum(units, Counter(rng.choices(index, k=n))) for _ in range(b)]


# ---------------------------------------------------------------------------- derived quantities


def block(acc: Sequence[float], name: str) -> list[float]:
    size = dict(BLOCKS)[name]
    return list(acc[OFFSET[name]:OFFSET[name] + size])


def shares(acc: Sequence[float], variant: str = "main") -> dict[str, dict[str, float | None]]:
    out = {}
    c, s = block(acc, f"{variant}.c"), block(acc, f"{variant}.s")
    tc, ts = sum(c), sum(s)
    for k, cat in enumerate(CATS):
        cp = 100 * c[k] / tc if tc else None
        sp = 100 * s[k] / ts if ts else None
        out[cat] = {"concern": cp, "solution": sp, "gap": sp - cp if cp is not None and sp is not None else None}
    return out


def axis_ratio(acc: Sequence[float], axes: Sequence[str]) -> float | None:
    c, s = block(acc, "axes.c"), block(acc, "axes.s")
    cc = sum(c[AXES.index(a)] for a in axes)
    return sum(s[AXES.index(a)] for a in axes) / cc if cc else None


def hr4_difference(acc: Sequence[float]) -> float | None:
    a, b = (axis_ratio(acc, g) for g in HR4_GROUPS)
    return a - b if a is not None and b is not None else None


def _ci(values: list[float | None], b: int) -> list[float] | None:
    vals = [v for v in values if v is not None]
    return list(metrics.interval(vals)) if len(vals) >= b // 2 else None


def _r(x: float | None, nd: int = 2) -> float | None:
    return None if x is None else round(x, nd)


# ---------------------------------------------------------------------------- the analysis


def analyse(works: list[Work], flows: list[Flow], results: dict[str, Result], *, b: int | None = None,
            seed: int | None = None) -> dict:
    b = b or config.BOOTSTRAP_B
    seed = config.BOOTSTRAP_SEED if seed is None else seed
    eras = list(config.ERAS)
    by_era = {e: [w for w in works if w.era == e] for e in eras}
    units = {e: [sparse(vectors(w, results[w.id])) for w in by_era[e]] for e in eras}
    flow = {f.era: f for f in flows}
    weight = {e: flow[e].population / flow[e].analysed for e in eras}

    point = {e: _sum(units[e]) for e in eras}
    reps = {e: replicates(units[e], b=b, seed=f"{seed}-{e}") for e in eras}
    point["pooled"] = [sum(weight[e] * point[e][d] for e in eras) for d in range(DIM)]
    reps["pooled"] = [[sum(weight[e] * reps[e][k][d] for e in eras) for d in range(DIM)] for k in range(b)]
    periods = [*eras, "pooled"]

    categories = [{"era": "2012", "category": cat, "concernPct": float(c), "solutionPct": float(s),
                   "gapPts": float(s - c), "concernCi": None, "solutionCi": None, "gapCi": None,
                   "concernEntries": None, "solutionEntries": None}
                  for cat, (c, s) in taxonomy.PAPER_2012_CATEGORIES.items()]
    robustness = []
    for p in periods:
        rep_shares = {v: [shares(acc, v) for acc in reps[p]] for v in VARIANTS}
        pt = {v: shares(point[p], v) for v in VARIANTS}
        c_counts, s_counts = block(point[p], "main.c"), block(point[p], "main.s")
        for k, cat in enumerate(CATS):
            row = pt["main"][cat]
            categories.append({
                "era": p, "category": cat, "concernPct": _r(row["concern"]), "solutionPct": _r(row["solution"]),
                "gapPts": _r(row["gap"]),
                **{f"{x}Ci": [round(v, 2) for v in ci] if (ci := _ci([r[cat][x] for r in rep_shares["main"]], b))
                   else None for x in ("concern", "solution", "gap")},
                "concernEntries": None if p == "pooled" else int(c_counts[k]),
                "solutionEntries": None if p == "pooled" else int(s_counts[k]),
            })
        for v, label in VARIANTS.items():
            ci = _ci([r[VIRT]["gap"] for r in rep_shares[v]], b)
            robustness.append({"id": v, "label": label, "era": p, "gapPts": _r(pt[v][VIRT]["gap"]),
                               "gapCi": [round(x, 2) for x in ci] if ci else None})

    # Figures 5 and 7: sub-category shares (point estimates).
    subcats = []
    for p in periods:
        cc: Counter = Counter()
        sc: Counter = Counter()
        for e in (eras if p == "pooled" else [p]):
            for w in by_era[e]:
                r = results[w.id]
                if r.in_scope:
                    wt = weight[e] if p == "pooled" else 1
                    for s in r.concern:
                        cc[s] += wt
                    for s in r.solution:
                        sc[s] += wt
        tc, ts = sum(cc.values()), sum(sc.values())
        for sub, (cat, _) in taxonomy.SUBCATEGORIES.items():
            subcats.append({"era": p, "subcategory": sub, "category": cat,
                            "concernPct": _r(100 * cc[sub] / tc if tc else None),
                            "solutionPct": _r(100 * sc[sub] / ts if ts else None),
                            "concernEntries": None if p == "pooled" else int(cc[sub]),
                            "solutionEntries": None if p == "pooled" else int(sc[sub])})
    for sub, (c, s) in taxonomy.PAPER_2012_SUBCATEGORIES.items():
        subcats.append({"era": "2012", "subcategory": sub, "category": taxonomy.category_of(sub),
                        "concernPct": float(c), "solutionPct": float(s), "concernEntries": None,
                        "solutionEntries": None})

    # Figure 11: entries per sub-issue and the solution/concern ratio.
    axes = [{"era": "2012", "axis": a, "concernEntries": c, "solutionEntries": s, "ratio": round(s / c, 3),
             "ratioCi": None} for a, (c, s) in taxonomy.PAPER_2012_AXES.items()]
    for p in periods:
        ac, asol = block(point[p], "axes.c"), block(point[p], "axes.s")
        for k, a in enumerate(AXES):
            ci = _ci([axis_ratio(acc, [a]) for acc in reps[p]], b)
            axes.append({"era": p, "axis": a,
                         "concernEntries": None if p == "pooled" else int(ac[k]),
                         "solutionEntries": None if p == "pooled" else int(asol[k]),
                         "ratio": _r(axis_ratio(point[p], [a]), 3),
                         "ratioCi": [round(x, 3) for x in ci] if ci else None})

    last = eras[-1]
    gaps_last = [shares(acc)[VIRT]["gap"] for acc in reps[last]]
    most_negative = [
        all(g[VIRT]["gap"] is not None and (g[c]["gap"] is None or g[VIRT]["gap"] <= g[c]["gap"]) for c in CATS)
        for g in (shares(acc) for acc in reps[last])]
    hr4 = [hr4_difference(acc) for acc in reps["pooled"]]
    stats = {
        "gapLast": _r(shares(point[last])[VIRT]["gap"]), "gapLastCi": _ci(gaps_last, b),
        "gapFirst": _r(shares(point[eras[0]])[VIRT]["gap"]),
        "mostNegativeShare": sum(most_negative) / len(most_negative),
        "hr4": _r(hr4_difference(point["pooled"]), 3), "hr4Ci": _ci(hr4, b),
        "hr4Groups": {"isolation+cross-vm": _r(axis_ratio(point["pooled"], HR4_GROUPS[0]), 3),
                      "other three": _r(axis_ratio(point["pooled"], HR4_GROUPS[1]), 3)},
    }
    in_scope = {e: sum(1 for w in by_era[e] if results[w.id].in_scope) for e in eras}
    flow_rows = [{"era": f.era, "population": f.population, "sampled": f.sampled, "unique": f.unique,
                  "excluded": f.excluded, "analysed": f.analysed, "inScope": in_scope[f.era]} for f in flows]
    publishers = Counter((w.publisher or "unknown") for w in works if results[w.id].in_scope)
    return {"flow": flow_rows, "categories": categories, "subcategories": subcats, "axes": axes,
            "robustness": robustness, "stats": stats, "bootstrap": {"b": b, "seed": seed},
            "publishers": [{"publisher": p, "works": n} for p, n in publishers.most_common(12)]}


# ---------------------------------------------------------------------------- verdicts


def _verdict(supported: bool, refuted: bool) -> str:
    return "supported" if supported else "not-supported" if refuted else "inconclusive"


def _fmt_ci(ci: list[float] | None, nd: int = 1) -> str:
    return f"[{ci[0]:.{nd}f}, {ci[1]:.{nd}f}]" if ci else "[n/a]"


def hypotheses(stats: dict, validity: dict, eras: Sequence[str]) -> list[dict]:
    first, last = eras[0], eras[-1]
    g, ci = stats["gapLast"], stats["gapLastCi"]
    prefix = "" if validity["met"] else "Classifier validity gate not met. "
    out = [
        {"id": "HR1", "statement": f"The virtualization gap persists: G_v({last}) < 0",
         "verdict": _verdict(bool(ci and ci[1] < 0), bool(ci and ci[0] >= 0)),
         "detail": f"{prefix}G_v = {g:+.1f} pts, 95% CI {_fmt_ci(ci)}"},
    ]
    bridge = stats["gapFirst"]
    note = (f" Method bridge: G_v({first}) = {bridge:+.1f} pts"
            + (", more than 5 pts from -9, so the 2012 comparison is dominated by method differences."
               if bridge is not None and abs(bridge + 9) > 5 else "."))
    out.append({"id": "HR2", "statement": f"The gap is narrower than in 2012: G_v({last}) > -9",
                "verdict": _verdict(bool(ci and ci[0] > -9), bool(ci and ci[1] < -9)),
                "detail": f"{prefix}G_v = {g:+.1f} pts, 95% CI {_fmt_ci(ci)}.{note}"})
    share = stats["mostNegativeShare"]
    out.append({"id": "HR3", "statement": f"Virtualization is still the most negative category in {last}",
                "verdict": _verdict(share >= 0.90, share <= 0.10),
                "detail": f"{prefix}most negative in {100 * share:.1f}% of bootstrap replicates"})
    d, dci = stats["hr4"], stats["hr4Ci"]
    grp = stats["hr4Groups"]
    out.append({"id": "HR4",
                "statement": "Isolation + cross-VM are the least answered sub-issues (pooled solution/concern ratio "
                             "below the other three)",
                "verdict": _verdict(bool(dci and dci[1] < 0), bool(dci and dci[0] > 0)),
                "detail": f"{prefix}ratio {grp['isolation+cross-vm']} vs {grp['other three']}, difference "
                          + (f"{d:+.3f}" if d is not None else "n/a") + f", 95% CI {_fmt_ci(dci, 3)} "
                          "(2012: 0.10 vs 0.29)"})
    checks = validity["checks"]
    shown = ", ".join(f"{k.replace('_', ' ')} {v['value']:.2f} (>= {v['threshold']})" if v["value"] is not None
                      else f"{k.replace('_', ' ')} n/a" for k, v in checks.items())
    out.append({"id": "HR5", "statement": "Validity gate: the classifier agrees with the blind human labels",
                "verdict": "supported" if validity["met"] else "not-supported", "detail": shown})
    return out
