"""Run the auditor's tooling (pytest, ruff, schema/doc generation) in its dev container,
so nothing needs installing on the host."""

from __future__ import annotations

from . import util

DEV_IMAGE = "isolab/auditor-dev:local"


def _build() -> None:
    util.run(["docker", "build", "--quiet", "--target", "dev", "-t", DEV_IMAGE, str(util.REPO / "auditor")],
             timeout=900)


def _run(script: str, *, writable: bool = False) -> int:
    _build()
    mount = f"{util.REPO}:/repo" + ("" if writable else ":ro")
    proc = util.run(["docker", "run", "--rm", *util.operator_labels("devtools"), "--network", "none",
                     "-v", mount, DEV_IMAGE, "sh", "-c", script], check=False, capture=False, timeout=900)
    return proc.returncode


def test() -> int:
    """ruff + pytest for the auditor, then the orchestrator's own unit tests."""
    return _run("ruff check --no-cache src tests ../experiments && "
                "python -m pytest -q -p no:cacheprovider tests ../experiments/tests")


def validate(dest) -> int:
    """Validate published result files against the committed schemas (and SARIF 2.1.0)."""
    rel = dest.resolve().relative_to(util.REPO).as_posix()
    return _run(f"python -m cloudaudit validate /repo/{rel} --schemas /repo/schemas")


def contract() -> int:
    """Regenerate the JSON Schemas and docs/checks.md from the Python models."""
    return _run("python -m cloudaudit schema --out /repo/schemas && "
                "python -m cloudaudit catalogue --format md > /repo/docs/checks.md && "
                "echo 'wrote schemas/*.schema.json and docs/checks.md'", writable=True)
