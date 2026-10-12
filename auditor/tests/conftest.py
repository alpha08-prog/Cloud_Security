from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from cloudaudit.policy import load_policy, load_waivers
from cloudaudit.snapshot import Snapshot

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"
TESTBED = ROOT / "testbed"
SCHEMAS = ROOT / "schemas"
# Waivers are judged against a fixed day so the tests don't start failing on their expiry date.
TODAY = date(2026, 10, 12)


def load_snapshot(name: str) -> Snapshot:
    return Snapshot.model_validate_json((FIXTURES / "snapshots" / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def policy():
    return load_policy(TESTBED / "policy.yaml")


@pytest.fixture(scope="session")
def waivers():
    return load_waivers(TESTBED / "waivers.yaml")


@pytest.fixture(scope="session")
def insecure() -> Snapshot:
    return load_snapshot("insecure-desktop")


@pytest.fixture(scope="session")
def hardened() -> Snapshot:
    return load_snapshot("hardened-desktop")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
