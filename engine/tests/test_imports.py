# Owner: Dev A
import importlib

import pytest

MODULES = [
    "engine",
    "engine.types",
    "engine.blind_match",
    "engine.blind_match.encoder",
    "engine.blind_match.linkage",
    "engine.blind_match.similarity",
    "engine.blind_match.models",
    "engine.blind_match.service",
    "engine.signals",
    "engine.signals.base",
    "engine.signals.eligibility",
    "engine.signals.shared_contacts",
    "engine.signals.backdated",
    "engine.signals.attrition",
    "engine.signals.registry",
    "engine.signals.rules",
    "engine.anomaly",
    "engine.anomaly.isolation",
    "engine.scoring",
    "engine.scoring.integrity",
    "engine.eval",
    "engine.eval.harness",
    "engine.evaluation",
    "engine.evaluation.harness",
    "engine.routers",
    "engine.config",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name: str) -> None:
    assert importlib.import_module(name) is not None
