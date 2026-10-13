"""Analysis of the replication on a synthetic corpus: shares, gaps, intervals, robustness variants,
verdict rules and the published contract. No real corpus result is computed here."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from replication import analysis, config, taxonomy  # noqa: E402
from replication.classify import Result  # noqa: E402
from replication.corpus import Flow, Work  # noqa: E402

SUBS = [s for s in taxonomy.SUBCATEGORIES if s not in analysis.VIRT_ROWS]


def synthetic(seed: int = 1, per_era: int = 120):
    rng = random.Random(seed)
    works, results, flows = [], {}, []
    for era in config.ERAS:
        for k in range(per_era):
            wid = f"W{era[:4]}{k:04d}"
            works.append(Work(id=wid, era=era, year=int(era[:4]), type=rng.choice(["article", "preprint"]),
                              title="t", abstract="a", venue=None, publisher=rng.choice(["IEEE", "Springer"])))
            if rng.random() < 0.3:
                results[wid] = Result(id=wid, in_scope=False, gate_cloud=True, gate_security=False,
                                      gate_joint=False, kind="concern")
                continue
            concern = rng.sample(SUBS, rng.randint(1, 3))
            axes = sorted(rng.sample(taxonomy.AXES, rng.randint(1, 2))) if rng.random() < 0.15 else []
            concern = sorted(set(concern) | {taxonomy.FOLD[a] for a in axes})
            kind = rng.choice(["solution", "solution", "concern", "survey"])
            solution = sorted(rng.sample(concern, rng.randint(1, len(concern)))) if kind == "solution" else []
            axes_s = [a for a in axes if taxonomy.FOLD[a] in solution]
            results[wid] = Result(id=wid, in_scope=True, gate_cloud=True, gate_security=True, gate_joint=True,
                                  kind=kind, concern=concern, solution=solution, axes_concern=axes,
                                  axes_solution=axes_s, classic_axes=axes[:1], classic_axes_solution=axes_s[:1],
                                  broadcast_solution=list(concern) if kind == "solution" else [])
        flows.append(Flow(era=era, population=10 * per_era, sampled=per_era, unique=per_era, analysed=per_era))
    return works, flows, results


@pytest.fixture(scope="module")
def doc():
    works, flows, results = synthetic()
    return analysis.analyse(works, flows, results, b=200, seed=7), (works, flows, results)


def test_shares_sum_to_100_and_gap_is_the_difference(doc):
    a, _ = doc
    for era in [*config.ERAS, "pooled", "2012"]:
        rows = [r for r in a["categories"] if r["era"] == era]
        assert len(rows) == 7
        assert sum(r["concernPct"] for r in rows) == pytest.approx(100, abs=0.5)
        assert sum(r["solutionPct"] for r in rows) == pytest.approx(100, abs=0.5)
        for r in rows:
            assert r["gapPts"] == pytest.approx(r["solutionPct"] - r["concernPct"], abs=0.02)


def test_intervals_contain_their_estimates(doc):
    a, _ = doc
    for r in a["categories"]:
        for x, ci in (("concernPct", r["concernCi"]), ("solutionPct", r["solutionCi"]), ("gapPts", r["gapCi"])):
            if ci:
                assert ci[0] <= r[x] + 1e-6 and r[x] <= ci[1] + 1e-6, (r["era"], r["category"], x)


def test_counts_match_a_direct_count(doc):
    a, (works, _, results) = doc
    era = list(config.ERAS)[0]
    direct = sum(len(results[w.id].concern) for w in works if w.era == era and results[w.id].in_scope)
    rows = [r for r in a["categories"] if r["era"] == era]
    assert sum(r["concernEntries"] for r in rows) == direct
    subs = [r for r in a["subcategories"] if r["era"] == era]
    assert sum(r["concernEntries"] for r in subs) == direct


def test_bootstrap_is_deterministic():
    works, flows, results = synthetic()
    one = analysis.analyse(works, flows, results, b=50, seed=3)
    two = analysis.analyse(works, flows, results, b=50, seed=3)
    assert one == two


def test_robustness_variants_are_reported_per_period(doc):
    a, _ = doc
    ids = {(r["id"], r["era"]) for r in a["robustness"]}
    assert ids == {(v, p) for v in analysis.VARIANTS for p in [*config.ERAS, "pooled"]}
    main = {r["era"]: r["gapPts"] for r in a["robustness"] if r["id"] == "main"}
    cats = {r["era"]: r["gapPts"] for r in a["categories"] if r["category"] == "virtualization"}
    for era, g in main.items():
        assert g == cats[era]


def test_2012_reference_rows_match_the_paper(doc):
    a, _ = doc
    rows = {r["category"]: r for r in a["categories"] if r["era"] == "2012"}
    assert rows["virtualization"]["concernPct"] == 12 and rows["virtualization"]["solutionPct"] == 3
    ax = {r["axis"]: r for r in a["axes"] if r["era"] == "2012"}
    assert ax["cross-vm-attacks"]["ratio"] == pytest.approx(1 / 21, abs=1e-3)


@pytest.mark.parametrize("gap,ci,share,hr4ci,expect", [
    (-6.0, [-8.0, -4.0], 0.95, [-0.3, -0.1], ["supported", "supported", "supported", "supported"]),
    (-12.0, [-14.0, -10.0], 0.05, [0.1, 0.3], ["supported", "not-supported", "not-supported", "not-supported"]),
    (0.5, [-1.0, 2.0], 0.5, [-0.1, 0.1], ["inconclusive", "supported", "inconclusive", "inconclusive"]),
    (2.0, [0.5, 3.5], 0.0, None, ["not-supported", "supported", "not-supported", "inconclusive"]),
])
def test_verdict_rules(gap, ci, share, hr4ci, expect):
    stats = {"gapLast": gap, "gapLastCi": ci, "gapFirst": -3.0, "mostNegativeShare": share, "hr4": -0.2,
             "hr4Ci": hr4ci, "hr4Groups": {"isolation+cross-vm": 0.1, "other three": 0.3}}
    gate = {"met": True, "checks": {"macro_f1": {"value": 0.8, "threshold": 0.7, "met": True}}}
    hs = analysis.hypotheses(stats, gate, list(config.ERAS))
    assert [h["verdict"] for h in hs[:4]] == expect
    assert hs[4]["id"] == "HR5" and hs[4]["verdict"] == "supported"
    assert "method differences" in hs[1]["detail"]  # bridge -3 is more than 5 pts from -9


def test_failed_validity_gate_flags_every_hypothesis():
    stats = {"gapLast": -5.0, "gapLastCi": [-7.0, -3.0], "gapFirst": -9.0, "mostNegativeShare": 1.0, "hr4": None,
             "hr4Ci": None, "hr4Groups": {"isolation+cross-vm": None, "other three": None}}
    gate = {"met": False, "checks": {"type_kappa": {"value": 0.4, "threshold": 0.6, "met": False}}}
    hs = analysis.hypotheses(stats, gate, list(config.ERAS))
    assert all(h["detail"].startswith("Classifier validity gate not met") for h in hs[:4])
    assert hs[4]["verdict"] == "not-supported"


def test_published_rows_fit_the_contract(doc):
    exp = pytest.importorskip("cloudaudit.experiments")
    a, _ = doc
    for r in a["categories"]:
        exp.RepCategory.model_validate(r)
    for r in a["subcategories"]:
        exp.RepSubcategory.model_validate(r)
    for r in a["axes"]:
        exp.RepAxis.model_validate(r)
    for r in a["robustness"]:
        exp.RepRobustness.model_validate(r)
    for r in a["flow"]:
        exp.RepFlow.model_validate(r)


def synthetic_validation(results: dict) -> dict:
    from replication import validate
    ids = sorted(results)[:24]
    strata = {"2013-2017": {"A": {"N": 40, "n": 8, "ids": ids[:8]}, "B": {"N": 400, "n": 8, "ids": ids[8:16]},
                            "C": {"N": 300, "n": 8, "ids": ids[16:24]}}}
    screens = [{"screen": f"s{k:03d}", "id": i, "repeat": False} for k, i in enumerate(ids)]
    screens += [{"screen": "s900", "id": ids[0], "repeat": True}, {"screen": "s901", "id": ids[9], "repeat": True}]
    test = {"strata": strata, "screens": screens, "repeats": [ids[0], ids[9]]}
    labels = {"labels": {}}
    for s in screens:
        r = results[s["id"]]
        pred = validate.predicted(r)
        labels["labels"][s["screen"]] = {"onTopic": r.in_scope, "type": pred["type"] if r.in_scope else None,
                                         "categories": pred["categories"], "axes": pred["axes"], "unsure": False}
    return validate.validate_test_sample(test, labels, results, b=50, seed=1)


def test_validation_against_identical_labels_is_perfect(doc):
    _, (_, _, results) = doc
    v = synthetic_validation(results)
    assert v["n"] == 24 and v["repeats"] == 2
    assert v["weighted"]["validityGate"]["met"]
    assert v["selfAgreement"]["onTopicAgreement"] == 1.0
    assert v["weighted"]["macroF1"]["concern"] == pytest.approx(1.0)


def test_full_document_fits_the_contract(doc):
    exp = pytest.importorskip("cloudaudit.experiments")
    from replication import publish, validate
    a, (_, _, results) = doc
    v = synthetic_validation(results)
    dev = {"dev": validate.compare([{"id": i, "onTopic": False} for i in sorted(results)[:5]], results)}
    cve_doc = {"source": "NVD", "retrievedAt": "2026-10-13T00:00:00Z", "sha256": "0" * 64, "candidates": 1,
               "axes": ["isolation"], "notMeasured": ["vm-identification"], "deviations": ["D1"],
               "years": [{"year": 2026, "total": 10, "partial": True, "counts": {"isolation": 1, "any": 1},
                          "per10k": {"isolation": 1000.0, "any": 1000.0}}], "spotCheck": None}
    built = publish.build(flows_doc=a["flow"], analysis_doc=a, validation=v, dev=dev, cve_doc=cve_doc)
    model = exp.ReplicationResult.model_validate(built)
    assert [h.id for h in model.hypotheses] == ["HR1", "HR2", "HR3", "HR4", "HR5"]
    # Every key the publisher writes is the schema's alias (the model also accepts field names).
    assert model.model_dump(mode="json", by_alias=True, exclude_unset=True) == json.loads(json.dumps(built))


PUBLISHED = Path(__file__).resolve().parents[2] / "results" / "published" / "replication.json"


@pytest.mark.skipif(not PUBLISHED.exists(), reason="the replication is not published yet")
def test_committed_snapshot_reproduces_the_published_counts():
    from collections import Counter

    from replication import classify, corpus, freeze
    doc = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    assert doc["protocol"]["rulesSha256"] == freeze.hashes()
    works, flows = corpus.load_all()
    results = {w.id: classify.classify(w.id, w.title, w.abstract) for w in works}
    for f in flows:
        row = next(r for r in doc["flow"] if r["era"] == f.era)
        assert (row["analysed"], row["inScope"]) == (f.analysed, sum(
            1 for w in works if w.era == f.era and results[w.id].in_scope))
        concern: Counter = Counter()
        solution: Counter = Counter()
        for w in works:
            r = results[w.id]
            if w.era == f.era and r.in_scope:
                concern.update(taxonomy.category_of(s) for s in r.concern)
                solution.update(taxonomy.category_of(s) for s in r.solution)
        for cat in taxonomy.CATEGORIES:
            pub = next(r for r in doc["categories"] if r["era"] == f.era and r["category"] == cat)
            assert (pub["concernEntries"], pub["solutionEntries"]) == (concern[cat], solution[cat]), (f.era, cat)
