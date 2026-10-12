#!/usr/bin/env python3
"""IsoLab orchestrator: one entry point for the testbed, the audit and the experiments.

Standard library only, so it runs on the host Python (Windows, macOS, Linux, CI)
without installing anything. The auditor itself runs in a container.

    python scripts/lab.py doctor              check Docker, ports, line endings, CPU plan
    python scripts/lab.py cpus                (re)plan CPU placement from the real topology
    python scripts/lab.py up insecure|hardened
    python scripts/lab.py status
    python scripts/lab.py down

See `python scripts/lab.py --help` for the full command list.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from isolab import audit, compose, cpus, devtools, testbed, util  # noqa: E402


def cmd_doctor(args) -> int:
    return 0 if testbed.doctor() else 1


def cmd_cpus(args) -> int:
    placement = cpus.plan(cpus.read_topology())
    cpus.write_env(placement)
    for key, value in placement.env().items():
        print(f"{key}={value}")
    util.ok(f"wrote {cpus.ENV_FILE.relative_to(util.REPO)}")
    return 0


def cmd_config(args) -> int:
    print(compose.compose(args.profile, "config").stdout)
    return 0


def cmd_up(args) -> int:
    testbed.up(args.profile, build=not args.no_build)
    return 0


def cmd_down(args) -> int:
    testbed.down()
    return 0


def cmd_status(args) -> int:
    testbed.status()
    return 0


def _out(args) -> Path | None:
    return Path(args.out).resolve() if getattr(args, "out", None) else None


def cmd_audit(args) -> int:
    report = audit.audit(args.profile, _out(args))
    return 0 if report["gate"]["passed"] or args.profile == "insecure" else 1


def cmd_gate(args) -> int:
    return 0 if audit.gate(args.profile, _out(args)) else 1


def cmd_test(args) -> int:
    return devtools.test()


def cmd_contract(args) -> int:
    return devtools.contract()


def cmd_snapshot(args) -> int:
    audit.snapshot(compose.current_profile() or "hardened")
    return 0


def cmd_logs(args) -> int:
    profile = compose.current_profile() or args.profile or "hardened"
    out = compose.compose(profile, "--profile", "noisy", "logs", "--no-color", "--tail", str(args.tail),
                          *args.services, check=False)
    print(out.stdout, out.stderr, sep="")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="lab.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check the host before running anything").set_defaults(fn=cmd_doctor)
    sub.add_parser("cpus", help="plan CPU placement from the host topology").set_defaults(fn=cmd_cpus)

    p = sub.add_parser("config", help="print the merged compose config for a profile")
    p.add_argument("profile", choices=util.PROFILES)
    p.set_defaults(fn=cmd_config)

    p = sub.add_parser("up", help="build and start a profile (stops the other one first)")
    p.add_argument("profile", choices=util.PROFILES)
    p.add_argument("--no-build", action="store_true")
    p.set_defaults(fn=cmd_up)

    sub.add_parser("down", help="stop the testbed and delete its volumes").set_defaults(fn=cmd_down)
    sub.add_parser("status", help="show containers, placement and isolation settings").set_defaults(fn=cmd_status)

    p = sub.add_parser("audit", help="audit the running profile; save JSON + SARIF")
    p.add_argument("profile", choices=util.PROFILES)
    p.add_argument("--out", help="results directory (default results/runs/<platform>)")
    p.set_defaults(fn=cmd_audit)

    p = sub.add_parser("gate", help="hardened: policy/E2/E3 gates; insecure: negative control")
    p.add_argument("profile", choices=util.PROFILES)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_gate)

    sub.add_parser("snapshot", help="save a sanitized snapshot as a unit-test fixture").set_defaults(fn=cmd_snapshot)
    sub.add_parser("test", help="ruff + pytest for the auditor and orchestrator (in a container)").set_defaults(
        fn=cmd_test)
    sub.add_parser("contract", help="regenerate schemas/*.schema.json and docs/checks.md").set_defaults(
        fn=cmd_contract)

    p = sub.add_parser("logs", help="show service logs")
    p.add_argument("services", nargs="*")
    p.add_argument("--profile", choices=util.PROFILES)
    p.add_argument("--tail", type=int, default=50)
    p.set_defaults(fn=cmd_logs)

    args = parser.parse_args()
    try:
        return args.fn(args)
    except util.CommandError as exc:
        util.fail(str(exc))
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
