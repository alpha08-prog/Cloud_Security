"""Non-destructive container verification of the selected ACM M2 control."""
import json
from datetime import UTC, datetime
from pathlib import Path
import subprocess
import tempfile


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    rows = []
    with tempfile.TemporaryDirectory(prefix="isolab-integrity-demo-") as directory:
        altered = Path(directory) / "altered.py"
        altered.write_text("raise RuntimeError('this altered application must never execute')\n")
        for image, app in [("isolab/payments-api:local", "/opt/app/payments_api.py"),
                           ("isolab/batch-analytics:local", "/opt/app/idle.py"),
                           ("isolab/legacy-app:hardened", "/opt/app/idle.py")]:
            image_id = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", image],
                                               text=True).strip()
            for tampered in (False, True):
                command = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                           "--security-opt", "no-new-privileges:true", "--user", "10001:10001",
                           "--label", "io.isolab.operator=true"]
                if tampered:
                    command += ["--mount", f"type=bind,source={altered},target={app},readonly"]
                command += ["--entrypoint", "python", image, "/opt/integrity/integrity.py", "--check",
                            "--", "python", "-u", app]
                result = subprocess.run(command, capture_output=True, text=True, timeout=45)
                passed = result.returncode == (78 if tampered else 0)
                rows.append({"image": image, "imageId": image_id, "tampered": tampered,
                             "exitCode": result.returncode, "passed": passed,
                             "output": (result.stdout + result.stderr).strip()})
                print(f"{'PASS' if passed else 'FAIL'} {image} {'tampered' if tampered else 'clean'}: {result.returncode}")
    report = {"generatedAt": datetime.now(UTC).isoformat(), "kind": "live-container-startup-check",
              "cases": rows, "passed": all(r["passed"] for r in rows)}
    out = root / "results/research/container-integrity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
