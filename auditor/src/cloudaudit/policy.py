"""Policy (what 'good' means) and waivers (accepted, time-boxed exceptions)."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .models import Waiver


class _P(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class ProviderException(_P):
    service: str
    checks: list[str]
    reason: str


class MinVersions(_P):
    docker_server: str
    kernel: str


class Observation(_P):
    stats_interval_seconds: float = 5
    stale_after_seconds: float = 15
    heartbeat_stale_seconds: float = 30


class GatePolicy(_P):
    fail_on: str = "high"


class Policy(_P):
    version: int
    required_labels: dict[str, list[str]] = Field(description="plane -> labels every workload of that plane needs")
    capability_allowlist: list[str] = Field(default_factory=list)
    sensitive_paths: list[str]
    engine_sockets: list[str]
    secret_env_pattern: str
    min_versions: MinVersions
    sysctls: dict[str, int]
    provider_exceptions: list[ProviderException] = Field(default_factory=list)
    ignore_services: list[str] = Field(default_factory=list)
    observation: Observation = Field(default_factory=Observation)
    gate: GatePolicy = Field(default_factory=GatePolicy)
    sha256: str = ""

    def exception_for(self, service: str, check_id: str) -> ProviderException | None:
        for e in self.provider_exceptions:
            if e.service == service and check_id in e.checks:
                return e
        return None


def load_policy(path: str | Path) -> Policy:
    raw = Path(path).read_bytes()
    policy = Policy.model_validate(yaml.safe_load(raw))
    policy.sha256 = hashlib.sha256(raw).hexdigest()
    return policy


def load_waivers(path: str | Path) -> list[Waiver]:
    p = Path(path)
    if not p.exists():
        return []
    doc = yaml.safe_load(p.read_text()) or []
    return [Waiver.model_validate(w) for w in doc]


def find_waiver(waivers: list[Waiver], check_id: str, platform: str, targets: list[str]) -> Waiver | None:
    for w in waivers:
        if w.check_id != check_id or w.platform not in ("*", platform):
            continue
        if w.target and w.target not in targets:
            continue
        return w
    return None


def is_expired(w: Waiver, today: date | None = None) -> bool:
    return w.expires < (today or date.today())
