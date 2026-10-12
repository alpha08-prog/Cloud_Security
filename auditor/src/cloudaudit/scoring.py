"""Coverage scores per Figure 11 axis and per requirement.

    coverage = sum(weight(severity) * credit(status)) / sum(weight(severity))

weights: critical 4, high 3, medium 2, low 1
credit:  pass 1, warn 0.5, fail 0, error 0; a waived check earns 0 (accepted, not fixed)
skip:    left out of the denominator, but counted in `skipped` so the UI can show
         "evaluated n of m"

In words: the share of applicable checks that pass, where a critical control
counts four times as much as a low one, and unverifiable facts get half credit.
The unweighted pass rate is published alongside, so the weights can be seen not
to drive the conclusion.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from .models import AXES, REQUIREMENTS, CheckResult, CheckSpec, Score, Scores

WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}
CREDIT = {"pass": 1.0, "warn": 0.5, "fail": 0.0, "error": 0.0}


def _score(key: str, pairs: Iterable[tuple[CheckSpec, CheckResult]], weighted: bool = True) -> Score:
    earned = possible = 0.0
    evaluated = skipped = total = 0
    for spec, result in pairs:
        total += 1
        if result.status == "skip":
            skipped += 1
            continue
        evaluated += 1
        w = WEIGHT[spec.severity] if weighted else 1
        possible += w
        earned += 0.0 if result.waived else w * CREDIT[result.status]
    return Score(key=key, score=round(earned / possible, 4) if possible else None, earned=earned,
                 possible=possible, evaluated=evaluated, skipped=skipped, total=total)


def score(catalogue: list[CheckSpec], results: list[CheckResult]) -> Scores:
    by_id = {r.check_id: r for r in results}
    pairs = [(c, by_id[c.id]) for c in catalogue if c.id in by_id]

    def group(pred: Callable[[CheckSpec], bool]):
        return [(c, r) for c, r in pairs if pred(c)]

    return Scores(
        by_axis=[_score(a, group(lambda c, a=a: c.axis == a)) for a in AXES],
        by_requirement=[_score(r, group(lambda c, r=r: r in c.requirements)) for r in REQUIREMENTS],
        overall=_score("overall", pairs),
        unweighted_by_axis=[_score(a, group(lambda c, a=a: c.axis == a), weighted=False) for a in AXES],
    )
