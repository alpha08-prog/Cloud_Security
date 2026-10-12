"""cloudaudit command line.

    cloudaudit serve                       run the live service (API, exporter, detectors)
    cloudaudit audit --snapshot FILE       audit a saved snapshot (tests, fixtures)
    cloudaudit schema --out DIR            write the JSON Schemas for the report contract
    cloudaudit catalogue --format md|json  print the check catalogue
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
    if args.cmd == "catalogue":
        if args.format == "md":
            sys.stdout.write(to_markdown() + "\n")
        else:
            print(json.dumps([c.dump() for c in CATALOGUE], indent=2))
        return 0
    return 2
