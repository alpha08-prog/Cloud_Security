"""`python scripts/lab.py rep ...`: the replication study's commands (docs/replication.md)."""

from __future__ import annotations

import argparse

from isolab import util

from . import config


def _fetch(args) -> int:
    from . import openalex
    openalex.fetch(force=args.force)
    return 0


def _cve_fetch(args) -> int:
    from . import nvd
    nvd.fetch(force=args.force)
    return 0


def _classified():
    from . import classify, corpus
    works, flows = corpus.load_all()
    return works, flows, {w.id: classify.classify(w.id, w.title, w.abstract) for w in works}


def _labels(name: str) -> dict | None:
    path = config.LABELS / f"{name}.json"
    return util.read_json(path) if path.exists() else None


def _status(args) -> int:
    from . import freeze, samples, snapshot
    for era in config.ERAS:
        path = config.CORPUS / f"openalex-{era}.jsonl.gz"
        if path.exists():
            _, digest = snapshot.read_jsonl_gz(path)
            manifest = util.read_json(config.CORPUS / "manifest.json")["eras"][era]
            (util.ok if digest == manifest["sha256"] else util.fail)(f"corpus {era}: sha256 {digest[:12]}")
        else:
            util.warn(f"corpus {era}: missing (run `rep fetch`)")
    nvd = config.NVD / "candidates.jsonl.gz"
    if nvd.exists():
        _, digest = snapshot.read_jsonl_gz(nvd)
        ok = digest == util.read_json(config.NVD / "manifest.json")["sha256"]
        (util.ok if ok else util.fail)(f"NVD candidates: sha256 {digest[:12]}")
    else:
        util.warn("NVD candidates: missing (run `rep cve-fetch`)")
    doc = freeze.load()
    if doc is None:
        util.warn("classifier: not frozen")
    else:
        try:
            freeze.check()
            util.ok(f"classifier: frozen {doc['frozenAt']}, hashes match")
        except freeze.FreezeError as e:
            util.fail(str(e))
    test = samples.load("test")
    if test is None:
        util.warn("test sample: not drawn")
    else:
        labels = _labels("test") or {"labels": {}}
        done = sum(1 for s in test["screens"] if s["screen"] in labels["labels"])
        (util.ok if done == len(test["screens"]) else util.info)(f"test labels: {done}/{len(test['screens'])}")
    return 0


def _dev(args) -> int:
    from . import validate
    _, _, results = _classified()
    out = {}
    for name in ("dev", "dev-virt"):
        labels = _labels(name)
        if labels is None:
            util.warn(f"no labels for {name}")
            continue
        s = validate.compare(labels["items"], results)
        out[name] = s
        g = s["validityGate"]
        util.info(f"{name} (tuning set, optimistic): n={s['n']} macro-F1 {s['macroF1']['concern']:.2f} "
                  f"mean kappa {s['meanKappa']:.2f} type kappa {s['typeKappa']:.2f} "
                  f"virtualization F1 {s['concern']['virtualization']['f1'] or 0:.2f} -> gate "
                  f"{'met' if g['met'] else 'NOT met'}")
    util.write_json(config.RUNS / "dev.json", out)
    return 0


def _freeze(args) -> int:
    from . import freeze
    doc = freeze.write()
    for name, digest in doc["files"].items():
        util.ok(f"frozen {name}: {digest[:16]}")
    util.info("add a changelog line to docs/replication.md and commit replication/freeze.json before `rep sample`")
    return 0


def _sample(args) -> int:
    from . import freeze, samples
    freeze.check()
    if samples.load("test") is not None:
        util.fail("replication/samples/test.json exists; the test sample is drawn once")
        return 1
    works, _, results = _classified()
    doc = samples.draw_test(works, results)
    doc["frozen"] = freeze.load()["files"]
    samples.save("test", doc)
    for era, strata in doc["strata"].items():
        util.ok(f"{era}: " + ", ".join(f"{k} {s['n']}/{s['N']}" for k, s in strata.items()))
    util.info(f"{len(doc['screens'])} screens; the annotator should not open replication/samples/test.json")
    return 0


def _annotate(args) -> int:
    from . import annotate, corpus, freeze
    freeze.check()
    works, _ = corpus.load_all()
    annotate.serve(works, port=args.port, open_browser=not args.no_browser)
    return 0


def _complete_test() -> tuple[dict, dict]:
    """The test sample and its labels; refuses while any screen is unlabelled, so the annotator
    never sees corpus results before finishing (docs/replication.md §4)."""
    from . import samples
    test = samples.load("test")
    labels = _labels("test")
    if test is None:
        raise util.CommandError("no test sample yet: `rep sample` after `rep freeze`")
    done = sum(1 for s in test["screens"] if labels and s["screen"] in labels["labels"])
    if done < len(test["screens"]):
        raise util.CommandError(f"test labels incomplete ({done}/{len(test['screens'])}): finish `rep annotate` first")
    return test, labels


def _validation(results: dict) -> dict:
    from . import validate
    test, labels = _complete_test()
    return validate.validate_test_sample(test, labels, results)


def _print_gate(v: dict) -> None:
    g = v["weighted"]["validityGate"]
    for name, c in g["checks"].items():
        value = "n/a" if c["value"] is None else f"{c['value']:.2f}"
        (util.ok if c["met"] else util.fail)(f"{name}: {value} (threshold {c['threshold']})")
    sa = v["selfAgreement"]
    util.info(f"self-agreement on {sa['pairs']} repeats: category kappa {sa['categoryKappa']}, "
              f"type kappa {sa['typeKappa']}; {v['unsure']} answers marked unsure")


def _validate(args) -> int:
    from . import freeze
    freeze.check()
    _complete_test()
    _, _, results = _classified()
    v = _validation(results)
    util.write_json(config.RUNS / "validation.json", v)
    _print_gate(v)
    return 0


def _analyze(args) -> int:
    from . import analysis, cve, freeze, validate
    freeze.check()
    _complete_test()
    works, flows, results = _classified()
    v = _validation(results)
    dev = {name: validate.compare(_labels(name)["items"], results) for name in ("dev", "dev-virt")}
    a = analysis.analyse(works, flows, results)
    c = cve.analyse()
    util.write_json(config.RUNS / "analysis.json", {"validation": v, "dev": dev, "analysis": a, "cve": c})
    _print_gate(v)
    for h in analysis.hypotheses(a["stats"], v["weighted"]["validityGate"], list(config.ERAS)):
        mark = {"supported": util.ok, "not-supported": util.fail}.get(h["verdict"], util.warn)
        mark(f"{h['id']} {h['verdict']}: {h['statement']} ({h['detail']})")
    util.info(f"wrote {(config.RUNS / 'analysis.json').relative_to(util.REPO).as_posix()}; `rep publish` next")
    return 0


def _cve_analyze(args) -> int:
    from . import cve
    c = cve.analyse()
    util.write_json(config.RUNS / "cve.json", c)
    for a, p in (c["spotCheck"] or {}).items():
        util.info(f"{a}: spot-check precision {p['precision']} (with D1 {p['precisionWithD1']}, n={p['nWithD1']})")
    last = c["years"][-1]
    util.ok(f"{c['candidates']} candidates; {last['year']} (partial): {last['counts']['any']} of {last['total']} CVEs")
    return 0


def _publish(args) -> int:
    from isolab import devtools

    from . import publish
    path = config.RUNS / "analysis.json"
    if not path.exists():
        raise util.CommandError("run `rep analyze` first")
    run = util.read_json(path)
    doc = publish.build(flows_doc=run["analysis"]["flow"], analysis_doc=run["analysis"], validation=run["validation"],
                        dev=run["dev"], cve_doc=run["cve"])
    publish.write(doc)
    if devtools.validate(util.PUBLISHED) != 0:
        raise util.CommandError("replication.json does not match schemas/experiments.schema.json")
    util.ok("published results/published/replication.json")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    rep = sub.add_parser("rep", help="replication of the survey's counting method (docs/replication.md)")
    rsub = rep.add_subparsers(dest="rep_cmd", required=True)

    p = rsub.add_parser("fetch", help="snapshot the OpenAlex samples into replication/corpus/")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=_fetch)

    p = rsub.add_parser("cve-fetch", help="snapshot NVD candidates and quarterly totals into replication/nvd/")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=_cve_fetch)

    rsub.add_parser("status", help="snapshots, freeze and labelling progress").set_defaults(fn=_status)
    rsub.add_parser("dev", help="classifier vs the dev labels (tuning sets)").set_defaults(fn=_dev)
    rsub.add_parser("freeze", help="hash the classifier rules into replication/freeze.json").set_defaults(fn=_freeze)
    rsub.add_parser("sample", help="draw the validation sample (after the freeze)").set_defaults(fn=_sample)

    rsub.add_parser("validate", help="classifier vs the blind test labels").set_defaults(fn=_validate)
    rsub.add_parser("analyze", help="shares, intervals, robustness and HR1-HR5 (needs complete labels)"
                    ).set_defaults(fn=_analyze)
    rsub.add_parser("cve-analyze", help="the descriptive CVE series").set_defaults(fn=_cve_analyze)
    rsub.add_parser("publish", help="write and validate results/published/replication.json").set_defaults(fn=_publish)

    p = rsub.add_parser("annotate", help="open the blind labelling form (127.0.0.1 only)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(fn=_annotate)
