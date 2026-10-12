"""Thin wrapper around `docker compose` for the two testbed profiles."""

from __future__ import annotations

import json
import os
import secrets

from . import cpus, util

SECRETS = util.TESTBED / "secrets"


def env_for(profile: str) -> dict[str, str]:
    return {
        "ISOLAB_PROFILE": profile,
        "ISOLAB_PLATFORM": util.detect_platform(),
        "ISOLAB_CI": "true" if os.environ.get("GITHUB_ACTIONS") == "true" else "false",
        "GIT_SHA": util.git_sha(),
        **{k: v for k, v in os.environ.items() if k in ("STRESS_TIMEOUT", "WORK_ITERATIONS")},
    }


def files(profile: str) -> list[str]:
    if profile not in util.PROFILES:
        raise ValueError(f"profile must be one of {util.PROFILES}, got {profile!r}")
    return [
        "-f", str(util.TESTBED / "compose.yaml"),
        "-f", str(util.TESTBED / f"compose.{profile}.yaml"),
    ]


def base_cmd(profile: str) -> list[str]:
    cpus.ensure()
    return [
        "docker", "compose",
        "--project-name", util.PROJECT,
        "--project-directory", str(util.TESTBED),
        *files(profile),
        "--env-file", str(cpus.ENV_FILE),
    ]


def compose(profile: str, *args: str, check: bool = True, capture: bool = True, extra_env: dict | None = None,
            timeout: float | None = None):
    return util.run([*base_cmd(profile), *args], check=check, capture=capture,
                    env={**env_for(profile), **(extra_env or {})}, timeout=timeout)


def ensure_secrets() -> None:
    SECRETS.mkdir(parents=True, exist_ok=True)
    for name in ("canary_token", "grafana_admin"):
        path = SECRETS / name
        if not path.exists():
            path.write_text(secrets.token_urlsafe(24), encoding="utf-8", newline="\n")
        try:
            path.chmod(0o644)  # containers run as uid 10001 / 472 and must read it
        except OSError:
            pass


def config(profile: str) -> dict:
    ensure_secrets()
    return json.loads(compose(profile, "config", "--format", "json").stdout)


def current_profile() -> str | None:
    """The profile of the running testbed, read from the auditor's environment."""
    out = util.docker("ps", "--filter", f"label=com.docker.compose.project={util.PROJECT}",
                      "--filter", "label=com.docker.compose.service=auditor", "--format", "{{.ID}}", check=False)
    cid = out.strip().splitlines()[0] if out.strip() else ""
    if not cid:
        return None
    env = util.docker_json("inspect", "--format", "{{json .Config.Env}}", cid)
    for item in env or []:
        if item.startswith("ISOLAB_PROFILE="):
            return item.split("=", 1)[1]
    return None


def container_id(service: str) -> str | None:
    out = util.docker("ps", "-q", "--filter", f"label=com.docker.compose.project={util.PROJECT}",
                      "--filter", f"label=com.docker.compose.service={service}", check=False).strip()
    return out.splitlines()[0] if out else None


def container_name(service: str) -> str | None:
    out = util.docker("ps", "--format", "{{.Names}}", "--filter", f"label=com.docker.compose.project={util.PROJECT}",
                      "--filter", f"label=com.docker.compose.service={service}", check=False).strip()
    return out.splitlines()[0] if out else None


def inspect(service: str) -> dict | None:
    cid = container_id(service)
    return util.docker_json("inspect", cid)[0] if cid else None


def network_name(short: str) -> str:
    return f"{util.PROJECT}_{short}"
