"""Result contract for experiments E1-E3 (protocol: docs/experiments.md) and the replication of
the survey's counting method (protocol: docs/replication.md).

The experiments themselves are run by scripts/lab.py (standard library only); it
writes JSON in exactly this shape, and `lab.py publish` + the web app's contract
tests validate it against the generated schema.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .models import SCHEMA_VERSION, Axis, Model, Requirement

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
    id: str = Field(pattern=r"^HR?\d+$")
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
    expect: dict[str, Literal["detect", "silent"]] = Field(description="per profile")
    expected_tenant: dict[str, str | None] = Field(description="per profile; null = unattributed workload")
    slo_ms: int
    requirements: list[Requirement]


class E3Outcome(Model):
    profile: ProfileName
    trigger_id: str
    expected: Literal["detect", "silent"]
    detected: bool
    rule: str | None
    tenant: str | None
    latency_ms: float | None
    within_slo: bool
    attribution_correct: bool | None
    as_expected: bool


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


# --------------------------------------------------------------------------- replication

Category = Literal["legal-issues", "compliance", "governance", "virtualization", "data-security", "interfaces",
                   "network-security"]
Interval = Annotated[list[float], Field(min_length=2, max_length=2, description="95% CI [low, high]")]


class RepEra(Model):
    id: str
    label: str
    seed: int
    first_year: int
    last_year: int
    partial: bool


class RepProtocol(Model):
    document: str
    query: str
    eras: list[RepEra]
    sample_per_era: int
    frozen_at: str
    rules_sha256: dict[str, str]
    corpus_sha256: dict[str, str]
    nvd_sha256: str
    bootstrap_b: int
    bootstrap_seed: int
    unit: str
    solution_rule: str
    deviations: list[str]


class RepFlow(Model):
    era: str
    population: int
    sampled: int
    unique: int
    excluded: dict[str, int]
    analysed: int
    in_scope: int


class RepCategory(Model):
    era: str = Field(description='"2012" (Figures 6/8), an era id, or "pooled"')
    category: Category
    concern_pct: float | None
    solution_pct: float | None
    gap_pts: float | None
    concern_ci: Interval | None
    solution_ci: Interval | None
    gap_ci: Interval | None
    concern_entries: int | None
    solution_entries: int | None


class RepSubcategory(Model):
    era: str
    subcategory: str
    category: Category
    concern_pct: float | None
    solution_pct: float | None
    concern_entries: int | None
    solution_entries: int | None


class RepAxis(Model):
    era: str
    axis: Axis
    concern_entries: int | None
    solution_entries: int | None
    ratio: float | None = Field(description="solution entries / concern entries")
    ratio_ci: Interval | None


class RepRobustness(Model):
    id: Literal["main", "RB1", "RB2", "RB3", "RB4"]
    label: str
    era: str
    gap_pts: float | None
    gap_ci: Interval | None


class RepScores(Model):
    tp: float
    fp: float
    fn: float
    tn: float
    precision: float | None
    recall: float | None
    f1: float | None
    kappa: float | None


class RepGateCheck(Model):
    value: float | None
    threshold: float
    met: bool


class RepGate(Model):
    met: bool
    checks: dict[str, RepGateCheck]


class RepAgreement(Model):
    n: int
    gate: RepScores = Field(description="relevance gate vs the on-topic flag")
    concern: dict[str, RepScores]
    solution: dict[str, RepScores]
    axes: dict[str, RepScores]
    macro_f1: dict[str, float | None]
    micro_f1: dict[str, float | None]
    mean_kappa: float | None
    type_kappa: float | None
    type_confusion: dict[str, float]
    off_topic: float
    validity_gate: RepGate
    ci: dict[str, Interval | None] | None = None


class RepSelfAgreement(Model):
    pairs: int
    on_topic_agreement: float | None
    category_kappa: float | None
    type_kappa: float | None


class RepValidation(Model):
    n: int
    screens: int
    repeats: int
    unsure: int
    completed_at: str | None
    weighted: RepAgreement
    unweighted: RepAgreement
    self_agreement: RepSelfAgreement
    dev: dict[str, RepAgreement] = Field(description="tuning sets (optimistic)")


class RepPublisher(Model):
    publisher: str
    works: int


class RepCveYear(Model):
    year: int
    total: int
    partial: bool
    counts: dict[str, int]
    per10k: dict[str, float | None] = Field(alias="per10k", description="CVEs per 10,000 published that year")


class RepCveSpot(Model):
    n: int
    correct: int
    precision: float | None
    n_with_d1: int
    correct_with_d1: int
    precision_with_d1: float | None


class RepCve(Model):
    source: str
    retrieved_at: str
    sha256: str
    candidates: int
    axes: list[str]
    not_measured: list[str]
    deviations: list[str]
    years: list[RepCveYear]
    spot_check: dict[str, RepCveSpot] | None


class ReplicationResult(Model):
    schema_version: str = SCHEMA_VERSION
    kind: Literal["replication"] = "replication"
    generated_at: str
    protocol: RepProtocol
    hypotheses: list[Hypothesis]
    validity_gate_met: bool
    flow: list[RepFlow]
    categories: list[RepCategory]
    subcategories: list[RepSubcategory]
    axes: list[RepAxis]
    robustness: list[RepRobustness]
    validation: RepValidation
    publishers: list[RepPublisher]
    cve: RepCve
    limitations: list[str]


# One schema covers every result file, discriminated by `kind`.
ExperimentResult = Annotated[E1Result | E2Result | E3Result | ReplicationResult, Field(discriminator="kind")]
