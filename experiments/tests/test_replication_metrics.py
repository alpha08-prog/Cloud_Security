"""Agreement metrics and bootstraps of the replication, checked against textbook values."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from replication import metrics  # noqa: E402


def test_binary_counts_and_scores():
    gold = [True, True, True, False, False, False, True, False]
    pred = [True, True, False, True, False, False, True, False]
    b = metrics.binary(gold, pred)
    assert (b.tp, b.fp, b.fn, b.tn) == (3, 1, 1, 3)
    assert b.precision == pytest.approx(0.75)
    assert b.recall == pytest.approx(0.75)
    assert b.f1 == pytest.approx(0.75)
    assert b.kappa == pytest.approx(0.5)  # po = .75, pe = .5


def test_kappa_textbook_example():
    # Cohen (1960)-style 2x2: 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no -> kappa = 0.4
    pairs = [(1, 1)] * 20 + [(1, 0)] * 5 + [(0, 1)] * 10 + [(0, 0)] * 15
    assert metrics.kappa(pairs) == pytest.approx(0.4)


def test_kappa_multiclass_and_weights():
    pairs = [("a", "a"), ("b", "b"), ("c", "c"), ("a", "b")]
    assert metrics.kappa(pairs) == pytest.approx((0.75 - 0.3125) / (1 - 0.3125))
    # Weights act as repeated items.
    assert metrics.kappa([(1, 1), (0, 0), (1, 0)], [2, 2, 1]) == pytest.approx(
        metrics.kappa([(1, 1)] * 2 + [(0, 0)] * 2 + [(1, 0)]))


def test_kappa_undefined_for_a_single_class():
    assert metrics.kappa([(1, 1), (1, 1)]) is None


def test_weighted_binary():
    b = metrics.binary([True, False], [True, True], weights=[3.0, 1.0])
    assert (b.tp, b.fp) == (3.0, 1.0)
    assert b.precision == pytest.approx(0.75)


def test_macro_and_micro_f1():
    a = metrics.Binary(tp=8, fp=2, fn=2, tn=88)   # F1 0.8
    b = metrics.Binary(tp=1, fp=1, fn=3, tn=95)   # F1 1/3
    assert metrics.macro_f1([a, b]) == pytest.approx((0.8 + 1 / 3) / 2)
    assert metrics.micro_f1([a, b]) == pytest.approx(18 / (18 + 3 + 5))


def test_percentile_matches_numpy_linear():
    v = [1, 2, 3, 4, 5]
    assert metrics.percentile(v, 50) == 3
    assert metrics.percentile(v, 25) == 2
    assert metrics.percentile(v, 2.5) == pytest.approx(1.1)
    assert metrics.interval(list(range(101))) == (2.5, 97.5)


def test_stratified_bootstrap_is_deterministic_and_stays_in_strata():
    strata = {"a": [0, 1, 2], "b": [3, 4]}
    seen = []

    def stat(idx):
        seen.append(idx)
        return sum(idx)

    one = metrics.stratified_bootstrap(strata, stat, b=50, seed=2012)
    two = metrics.stratified_bootstrap(strata, lambda idx: sum(idx), b=50, seed=2012)
    assert one == two
    for idx in seen:
        assert len(idx) == 5
        assert all(i in (0, 1, 2) for i in idx[:3]) and all(i in (3, 4) for i in idx[3:])
