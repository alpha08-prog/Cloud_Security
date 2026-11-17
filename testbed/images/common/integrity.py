"""M2-inspired startup hashing and executable allowlist for trusted image builds.

This is a startup control, not runtime attestation. The builder, manifest and
launcher must be trusted; a compromised root or engine can bypass them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(manifest: Path, command: list[str]) -> list[str]:
    try:
        records = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(records, dict) or not records:
            return ["empty or invalid allowlist"]
        resolved = shutil.which(command[0]) if command else None
        if not resolved or str(Path(resolved).resolve()) not in records:
            return ["executable is not allowlisted"]
        if Path(resolved).name.lower().startswith("python"):
            arguments = command[1:]
            if arguments[:1] == ["-u"]:
                arguments = arguments[1:]
            if (not arguments or arguments[0].startswith("-")
                    or str(Path(arguments[0]).resolve()) not in records):
                return ["Python entry script is not allowlisted"]
        errors = []
        for name, expected in records.items():
            path = Path(name)
            if not path.is_absolute() or str(path.resolve()) != name:
                errors.append(f"noncanonical path: {name}")
            elif not path.is_file() or digest(path) != expected:
                errors.append(f"integrity mismatch: {name}")
        return errors
    except (OSError, ValueError, TypeError) as exc:
        return [f"manifest validation failed: {type(exc).__name__}"]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=Path("/opt/integrity/allowlist.json"))
    p.add_argument("--create", nargs="+")
    p.add_argument("--check", action="store_true", help="validate the command without executing it")
    p.add_argument("command", nargs=argparse.REMAINDER)
    args = p.parse_args()
    if args.create:
        paths = [Path(name).resolve(strict=True) for name in args.create]
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps({str(path): digest(path) for path in paths}, indent=2) + "\n")
        return 0
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        p.error("command required")
    if args.check or os.environ.get("ISOLAB_INTEGRITY_ENFORCE") == "1":
        errors = verify(args.manifest, command)
        if errors:
            print(json.dumps({"control": "ACM-M2-startup", "allowed": False, "errors": errors}), file=sys.stderr)
            return 78
        print(json.dumps({"control": "ACM-M2-startup", "allowed": True}), flush=True)
    if args.check:
        return 0
    os.execvp(command[0], command)
    return 0


if __name__ == "__main__":
    sys.exit(main())
