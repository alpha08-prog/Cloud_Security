"""Result contract for experiments E1-E3 (protocol: docs/experiments.md).

The experiments themselves are run by scripts/lab.py (standard library only); it
writes JSON in exactly this shape, and `lab.py publish` + the web app's contract
tests validate it against the generated schema.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .models import SCHEMA_VERSION, Model, Requirement

ProfileName = Literal["insecure", "hardened"]
Variant = Literal["full", "ci"]
Verdict = Literal["supported", "not-supported", "inconclusive"]


class RunEnvironment(Model):
    platform: str
    docker_server_version: str
    kernel_version: str
    logical_cpus: int
    physical_cores: int
    git_sha: str | None = None
    placement: dict[str, str] = Field(default_factory=dict, description="cpusets per role from cpus.env")


class Hypothesis(Model):
    id: str = Field(pattern=r"^H\d+$")
    statement: str
    verdict: Verdict
    detail: str


class Percentiles(Model):
    avg: float
    min: float
    med: float
    p90: float
    p95: float
    p99: float
    max: float


class _Base(Model):
    schema_version: str = SCHEMA_VERSION
    generated_at: str
    variant: Variant
    environment: RunEnvironment
    hypotheses: list[Hypothesis]


# --------------------------------------------------------------------------- E1


class E1Config(Model):
    rate_per_second: int
    warmup_seconds: int
    measure_seconds: int
    repetitions: int
    stress_workers: int
    work_iterations: int
    slo_p99_ms: float


class E1Run(Model):
    profile: ProfileName
    arm: Literal["baseline", "noisy"]
    repetition: int
    started_at: str
    latency_ms: Percentiles
    server_work_ms: Percentiles | None
    failed_rate: float
    dropped_iterations: int
    iterations: int
    noisy_cores_used: float | None = Field(description="CPU cores used by tenant-b during the window")
    victim_cpu_pressure_pct: float | None = Field(description="share of time tenant-a had runnable tasks waiting")
    throttled_seconds: dict[str, float] = Field(default_factory=dict, description="per tenant, during the window")
    valid: bool
    invalid_reason: str | None = None


class E1ProfileSummary(Model):
    profile: ProfileName
    baseline_p99_ms: float | None
    noisy_p99_ms: float | None
    interference_factor: float | None
    slo_met_under_noise: bool | None
    valid_runs: int
    total_runs: int


class E1Result(_Base):
    kind: Literal["e1"] = "e1"
    config: E1Config
    runs: list[E1Run]
    summary: list[E1ProfileSummary]


# --------------------------------------------------------------------------- E2

Outcome = Literal["allowed", "blocked", "error"]


class E2Probe(Model):
    id: str = Field(pattern=r"^[CP]\d+$")
    description: str
    source: str
    destination: str
    control: bool
    axis: str
    expected: dict[str, Literal["allowed", "blocked", "platform-dependent"]]


class E2Outcome(Model):
    profile: ProfileName
    probe_id: str
    outcome: Outcome
    detail: str
    as_expected: bool


class E2ProfileSummary(Model):
    profile: ProfileName
    open_paths: int
    probes: int
    controls_passed: int
    controls: int


class E2Result(_Base):
    kind: Literal["e2"] = "e2"
    probes: list[E2Probe]
    results: list[E2Outcome]
    summary: list[E2ProfileSummary]


# --------------------------------------------------------------------------- E3


class E3Trigger(Model):
    id: str = Field(pattern=r"^T\d+$")
    description: str
    expected_rule: str
    expected_tenant: str | None
    slo_ms: int
    requirements: list[Requirement]
    profiles: list[ProfileName]


class E3Outcome(Model):
    profile: ProfileName
    trigger_id: str
    detected: bool
    rule: str | None
    tenant: str | None
    latency_ms: float | None
    within_slo: bool
    attribution_correct: bool


class E3FalsePositive(Model):
    profile: ProfileName
    rule: str
    tenant: str | None
    message: str


class E3ProfileSummary(Model):
    profile: ProfileName
    detection_rate: float
    detected: int
    expected: int
    false_positives: int
    median_latency_ms: float | None
    max_latency_ms: float | None
    attribution_accuracy: float | None


class E3Result(_Base):
    kind: Literal["e3"] = "e3"
    quiet_window_seconds: int
    triggers: list[E3Trigger]
    results: list[E3Outcome]
    false_positives: list[E3FalsePositive]
    summary: list[E3ProfileSummary]


# One schema covers all three result files, discriminated by `kind`.
ExperimentResult = Annotated[E1Result | E2Result | E3Result, Field(discriminator="kind")]
