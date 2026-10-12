"""One consistent read of the engine and the host, taken before any check runs.

Checks are pure functions of a Snapshot. That makes them testable against JSON
fixtures (auditor/tests/fixtures) and means one audit never sees the world
change half-way through.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from . import host

L_PLANE = "io.isolab.plane"
L_TENANT = "io.isolab.tenant"
L_OWNER = "io.isolab.owner"
L_WORKLOAD = "io.isolab.workload-id"
L_SERVICE = "com.docker.compose.service"
L_PROJECT = "com.docker.compose.project"


class ObservedTenant(BaseModel):
    last_sample_age_s: float | None = None
    psi: bool = False


class SelfState(BaseModel):
    """The auditor's own live state, used by XVM-07 and ID-05."""

    watcher_heartbeat_age_s: float | None = None
    canary_healthy: bool | None = None
    rules_loaded: bool | None = None
    observed: dict[str, ObservedTenant] = Field(default_factory=dict, description="keyed by service name")


class Snapshot(BaseModel):
    taken_at: str
    profile: str
    platform: str
    ci: bool = False
    info: dict
    version: dict
    containers: list[dict]
    networks: list[dict]
    volumes: list[dict]
    images: dict[str, dict] = Field(default_factory=dict, description="image id -> trimmed inspect")
    host: host.HostFacts
    self_state: SelfState = Field(default_factory=SelfState)

    def sanitized(self) -> Snapshot:
        """Copy safe to commit as a fixture: env values, hostnames and IDs of the daemon removed."""
        doc = self.model_copy(deep=True)
        for c in doc.containers:
            c["Config"]["Env"] = [e.split("=", 1)[0] + "=<redacted>" for e in c["Config"].get("Env") or []]
            c["Config"]["Hostname"] = "<redacted>"
        for key in ("ID", "Name", "SystemTime", "RegistryConfig", "Swarm", "Plugins", "DockerRootDir"):
            doc.info.pop(key, None)
        # Replace the host path of the repository (it contains the user's home directory).
        repo = next((re.sub(r"[\\/]testbed$", "", m["Source"]) for c in doc.containers
                     for m in c.get("Mounts") or [] if m.get("Destination") == "/workspace/testbed"), None)
        text = doc.model_dump_json()
        if repo:
            text = text.replace(json.dumps(repo)[1:-1], "<repo>")  # as it appears inside the JSON text
        # Docker Desktop also shows binds in VM form (/run/desktop/mnt/host/c/Users/<name>/...).
        text = re.sub(r"(Users(?:/|\\\\)+)[^/\\\"]+", r"\1<user>", text)
        return Snapshot.model_validate_json(text)


def platform_of(info: dict) -> str:
    if os.environ.get("ISOLAB_PLATFORM"):
        return os.environ["ISOLAB_PLATFORM"]
    if os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("ISOLAB_CI") == "true":
        return "github-ubuntu"
    if "Docker Desktop" in str(info.get("OperatingSystem", "")):
        return "docker-desktop-wsl2" if "WSL2" in str(info.get("KernelVersion", "")) else "docker-desktop"
    return "linux"


def take(client, *, profile: str, self_state: SelfState | None = None, host_root: str = "/",
         cgroup_root: str = "/host/cgroup") -> Snapshot:
    """Read everything through the (read-only) engine API proxy plus /sys and /proc."""
    api = client.api
    info = api.info()
    version = api.version()
    containers = [api.inspect_container(c["Id"]) for c in api.containers(filters={"status": "running"})]
    networks = [api.inspect_network(n["Id"]) for n in api.networks()]
    volumes = (api.volumes() or {}).get("Volumes") or []
    images: dict[str, dict] = {}
    for c in containers:
        image_id = c.get("Image")
        if image_id and image_id not in images:
            try:
                img = api.inspect_image(image_id)
                images[image_id] = {
                    "RepoTags": img.get("RepoTags") or [],
                    "RepoDigests": img.get("RepoDigests") or [],
                    "Config": {"User": (img.get("Config") or {}).get("User", ""),
                               "Labels": (img.get("Config") or {}).get("Labels") or {}},
                }
            except Exception:  # image may be gone (e.g. --rm container racing)
                images[image_id] = {"RepoTags": [], "RepoDigests": [], "Config": {"User": "", "Labels": {}}}
    return Snapshot(
        taken_at=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        profile=profile,
        platform=platform_of(info),
        ci=os.environ.get("ISOLAB_CI") == "true",
        info=info,
        version=version,
        containers=containers,
        networks=networks,
        volumes=volumes,
        images=images,
        host=host.collect(host_root, cgroup_root),
        self_state=self_state or SelfState(),
    )


# --------------------------------------------------------------------------- helpers used by checks

def labels(c: dict) -> dict:
    return (c.get("Config") or {}).get("Labels") or {}


def service(c: dict) -> str:
    return labels(c).get(L_SERVICE) or c.get("Name", "").lstrip("/")


def plane(c: dict) -> str:
    """Workloads without a plane label are treated as tenants: untrusted by default."""
    return labels(c).get(L_PLANE) or "tenant"


def tenant(c: dict) -> str | None:
    return labels(c).get(L_TENANT)


def workload_id(c: dict) -> str | None:
    return labels(c).get(L_WORKLOAD)


def short_network(name: str, project: str = "isolab") -> str:
    return name.removeprefix(f"{project}_")


def now() -> float:
    return time.time()


_TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)?$")


def docker_time_ns(value: str) -> int:
    """Docker's RFC 3339 timestamps (nanosecond precision) -> epoch nanoseconds."""
    m = _TS.match((value or "").strip())
    if not m:
        return time.time_ns()
    head, frac, tz = m.groups()
    base = datetime.fromisoformat(head + ("+00:00" if tz in (None, "Z") else tz)).timestamp()
    return int(base) * 10**9 + int((frac or "0").ljust(9, "0")[:9])
