"""E5: isolated startup-control challenges; no deployed tenant is modified."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os


def study(repo: Path) -> dict:
    launcher = repo / "testbed/images/common/integrity.py"
    spec = importlib.util.spec_from_file_location("isolab_integrity", launcher)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="isolab-integrity-") as directory:
        root = Path(directory)
        script = root / "application.py"
        sentinel = root / "executed.txt"
        manifest = root / "allowlist.json"
        original = f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('executed')\n"
        script.write_text(original, encoding="utf-8")
        records = {str(path.resolve()): module.digest(path)
                   for path in (Path(sys.executable), script, launcher)}
        command = [sys.executable, str(launcher), "--manifest", str(manifest), "--", sys.executable, str(script)]
        rows = []
        for name in ("clean", "modified-script", "missing-script", "unlisted-script", "invalid-manifest"):
            sentinel.unlink(missing_ok=True)
            script.write_text(original, encoding="utf-8")
            manifest.write_text(json.dumps(records), encoding="utf-8")
            invocation = command.copy()
            if name == "modified-script":
                script.write_text(original + "# altered\n", encoding="utf-8")
            elif name == "missing-script":
                script.unlink()
            elif name == "unlisted-script":
                other = root / "unlisted.py"
                other.write_text(original, encoding="utf-8")
                invocation[-1] = str(other)
            elif name == "invalid-manifest":
                manifest.write_text("not JSON", encoding="utf-8")
            result = subprocess.run(invocation, env={**os.environ, "ISOLAB_INTEGRITY_ENFORCE": "1"},
                                    capture_output=True, text=True, timeout=15)
            expected = name == "clean"
            passed = result.returncode == (0 if expected else 78) and sentinel.exists() == expected
            rows.append({"case": name, "expectedExecution": expected, "executed": sentinel.exists(),
                         "exitCode": result.returncode, "passed": passed})
    return {"kind": "isolated-subprocess-startup-integrity", "source": "ACM 2025 M2 (selected startup aspect)",
            "cases": rows, "passed": all(row["passed"] for row in rows),
            "scope": "Trusted image manifest, launcher and builder; excludes post-start tampering and arbitrary exec."}


if __name__ == "__main__":
    print(json.dumps(study(Path(__file__).resolve().parents[1]), indent=2))
