"""The report contract shared with the web app.

These pydantic models are the single source of truth: `cloudaudit schema` writes
them out as JSON Schema (schemas/*.schema.json), which the TypeScript side
validates against. Field names are camelCase on the wire.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0.0"

# Figure 11's five virtualization sub-issues, as slugs of the taxonomy labels.
Axis = Literal["hypervisor-vulnerabilities", "cross-vm-attacks", "isolation", "data-leakage", "vm-identification"]
AXES: tuple[str, ...] = ("hypervisor-vulnerabilities", "cross-vm-attacks", "isolation", "data-leakage",
                         "vm-identification")
Status = Literal["pass", "warn", "fail", "error", "skip"]
Severity = Literal["critical", "high", "medium", "low"]
Requirement = Literal["R1", "R2", "R3", "R4"]
REQUIREMENTS: tuple[str, ...] = ("R1", "R2", "R3", "R4")
Scope = Literal["container", "network", "volume", "fleet", "host", "self"]
TargetKind = Literal["container", "network", "volume", "host", "auditor", "fleet"]
Profile = Literal["insecure", "hardened", "fixture"]
Platform = Literal["docker-desktop-wsl2", "docker-desktop", "github-ubuntu", "linux", "fixture"]

# Framework vocabularies, as slugs of the item labels in src/data/frameworks.ts.
Enisa = Literal["policy-organizational", "technical", "legal", "not-cloud-specific"]
Nist = Literal["cloud-provider", "consumer", "carrier", "broker", "auditor"]
CsaDomain = Literal[
    "governance-and-risk-management",
    "legal-issues",
    "compliance-and-audit",
    "information-management-and-data-security",
    "portability-and-interoperability",
    "traditional-security-business-continuity-and-disaster-recovery",
    "data-center-operations",
    "incident-response-notification-and-remediation",
    "application-security",
    "encryption-and-key-management",
    "identity-and-access-management",
    "virtualization",
    "security-as-a-service",
]


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    def dump(self) -> dict:
        # Explicit nulls are part of the contract ("no score", "no waiver", "unattributed").
        return self.model_dump(mode="json", by_alias=True)


# --------------------------------------------------------------------------- catalogue

class Frameworks(Model):
    csa_top_threats: list[int] = Field(description="CSA Top Threats, 1-7 in the paper's order (p.12-13)")
    csa_domains: list[CsaDomain] = Field(description="CSA Guidance domains as listed in the paper (p.12)")
    enisa: list[Enisa]
    nist: list[Nist]


class CheckSpec(Model):
    id: str = Field(pattern=r"^(ISO|HV|DL|XVM|ID)-\d{2}$")
    title: str
    description: str
    axis: Axis
    requirements: list[Requirement]
    severity: Severity
    scope: Scope
    taxonomy: list[str] = Field(description="Node ids from the paper's taxonomy (Figures 2-4)")
    frameworks: Frameworks
    remediation: str
    platform_notes: str | None = None


# --------------------------------------------------------------------------- results

class Location(Model):
    file: str
    line: int


Evidence = dict[str, str | int | float | bool | None | list[str]]


class Target(Model):
    kind: TargetKind
    ref: str = Field(description="Service, network or volume name. Never a container ID or hostname.")
    tenant: str | None = None
    workload_id: str | None = None
    status: Status
    message: str
    evidence: Evidence = Field(default_factory=dict)
    location: Location | None = None


class Waiver(Model):
    check_id: str
    platform: str = Field(description="Platform the waiver applies to, or '*'")
    target: str | None = None
    reason: str
    expires: date
    approved_by: str


class CheckResult(Model):
    check_id: str
    status: Status
    waived: bool = False
    waiver: Waiver | None = None
    message: str
    targets: list[Target]


class Score(Model):
    key: str
    score: float | None = Field(description="earned / possible, or null if nothing was evaluated")
    earned: float
    possible: float
    evaluated: int
    skipped: int
    total: int


class Scores(Model):
    by_axis: list[Score]
    by_requirement: list[Score]
    overall: Score
    unweighted_by_axis: list[Score]


class Gate(Model):
    fail_on: Severity
    passed: bool
    blocking: list[str]
    waived: list[str]
    expired_waivers: list[str]


class Environment(Model):
    platform: Platform
    docker_server_version: str
    api_version: str
    operating_system: str
    kernel_version: str
    cgroup_version: str
    cgroup_driver: str
    logical_cpus: int
    physical_cores: int
    smt_control: str | None
    smt_active: bool | None
    security_options: list[str]
    ci: bool


class Tool(Model):
    name: Literal["cloudaudit"] = "cloudaudit"
    version: str
    git_sha: str | None


class AuditReport(Model):
    schema_version: str = SCHEMA_VERSION
    kind: Literal["audit"] = "audit"
    generated_at: str
    profile: Profile
    tool: Tool
    environment: Environment
    policy_sha256: str
    catalogue: list[CheckSpec]
    results: list[CheckResult]
    scores: Scores
    gate: Gate


# --------------------------------------------------------------------------- detections

DetectionRule = Literal["DET-01", "DET-02", "DET-03", "DET-04", "DET-05", "DET-06", "DET-07", "DET-08", "DET-09"]


class Detection(Model):
    id: str
    rule: DetectionRule
    title: str
    severity: Severity
    requirements: list[Requirement]
    tenant: str | None
    workload_id: str | None
    service: str | None
    event_time_ns: int = Field(description="When the action happened (engine or canary clock, inside the VM)")
    detected_at_ns: int = Field(description="When the auditor raised the detection (same clock)")
    latency_ms: float
    message: str
    evidence: Evidence = Field(default_factory=dict)
