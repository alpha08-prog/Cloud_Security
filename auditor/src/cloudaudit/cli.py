"""cloudaudit command line.

    cloudaudit serve                       run the live service (API, exporter, detectors)
    cloudaudit audit --snapshot FILE       audit a saved snapshot (tests, fixtures)
    cloudaudit schema --out DIR            write the JSON Schemas for the report contract
    cloudaudit catalogue --format md|json  print the check catalogue
    cloudaudit validate DIR --schemas DIR  validate published results (needs the dev extras)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .catalogue import CATALOGUE, to_markdown
from .engine import build_report
from .models import AuditReport, Detection
from .policy import load_policy, load_waivers
from .report import to_console, to_sarif
from .snapshot import Snapshot

TESTBED = os.environ.get("TESTBED_DIR", "/workspace/testbed")


def _schema(model) -> dict:
    from pydantic import TypeAdapter  # noqa: PLC0415

    schema = TypeAdapter(model).json_schema(by_alias=True, mode="serialization")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


def write_schemas(out: Path) -> None:
    from .experiments import ExperimentResult  # noqa: PLC0415 (keeps import light for `serve`)

    out.mkdir(parents=True, exist_ok=True)
    docs = {
        "audit-report.schema.json": {**_schema(AuditReport), "$id": "isolab/audit-report.schema.json"},
        "detection.schema.json": {**_schema(Detection), "$id": "isolab/detection.schema.json"},
        "experiments.schema.json": {**_schema(ExperimentResult), "$id": "isolab/experiments.schema.json"},
    }
    for name, doc in docs.items():
        (out / name).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate(results: Path, schemas: Path) -> int:
    import jsonschema  # noqa: PLC0415 (dev extra; not in the runtime image)

    audit_schema = json.loads((schemas / "audit-report.schema.json").read_text(encoding="utf-8"))
    exp_schema = json.loads((schemas / "experiments.schema.json").read_text(encoding="utf-8"))
    sarif_schema = json.loads((schemas / "vendor" / "sarif-2.1.0.json").read_text(encoding="utf-8"))
    bad = 0
    for f in sorted([*results.glob("*.json"), *results.glob("*.sarif")]):
        if f.name == "manifest.json":
            continue
        doc = json.loads(f.read_text(encoding="utf-8"))
        schema = sarif_schema if f.suffix == ".sarif" else audit_schema if f.name.startswith("audit") else exp_schema
        try:
            jsonschema.validate(doc, schema)
            print(f"valid    {f.name}")
        except jsonschema.ValidationError as exc:
            bad += 1
            print(f"INVALID  {f.name}: {exc.message[:300]} at {list(exc.absolute_path)[:8]}")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cloudaudit", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8088)
    a = sub.add_parser("audit")
    a.add_argument("--snapshot", required=True)
    a.add_argument("--policy", default=f"{TESTBED}/policy.yaml")
    a.add_argument("--waivers", default=f"{TESTBED}/waivers.yaml")
    a.add_argument("--format", choices=["console", "json", "sarif"], default="console")
    sc = sub.add_parser("schema")
    sc.add_argument("--out", default="schemas")
    c = sub.add_parser("catalogue")
    c.add_argument("--format", choices=["md", "json"], default="md")
    v = sub.add_parser("validate")
    v.add_argument("results")
    v.add_argument("--schemas", default="schemas")
    args = parser.parse_args(argv)

    if args.cmd == "serve":
        from .service.app import run  # noqa: PLC0415

        run(port=args.port)
        return 0
    if args.cmd == "audit":
        snap = Snapshot.model_validate_json(Path(args.snapshot).read_text(encoding="utf-8"))
        report = build_report(snap, load_policy(args.policy), load_waivers(args.waivers))
        if args.format == "json":
            print(json.dumps(report.dump(), indent=2))
        elif args.format == "sarif":
            print(json.dumps(to_sarif(report), indent=2))
        else:
            print(to_console(report))
        return 0 if report.gate.passed else 1
    if args.cmd == "schema":
        write_schemas(Path(args.out))
        return 0
    if args.cmd == "validate":
        return validate(Path(args.results), Path(args.schemas))
    if args.cmd == "catalogue":
        if args.format == "md":
            sys.stdout.write(to_markdown() + "\n")
        else:
            print(json.dumps([c.dump() for c in CATALOGUE], indent=2))
        return 0
    return 2
