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

    p = rsub.add_parser("annotate", help="open the blind labelling form (127.0.0.1 only)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(fn=_annotate)
