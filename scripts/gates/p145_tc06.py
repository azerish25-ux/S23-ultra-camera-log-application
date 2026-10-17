"""TC-P145-06 Update threatens private media.

Host fixture. An authorized update preserves sources, profiles, and recovery
data, or it refuses explicitly. A silent uninstall that papers over a signing
mismatch is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P145-06",
    "phase": "P145",
    "workstream": 19,
    "name": "Update threatens private media",
    "intervention": "Install an authorized signed update over a version containing sources, profiles, and recovery data.",
    "expected": "Preserve compatible data and provide explicit migration or refusal rather than destructive convenience.",
    "negative": "Uninstalling silently to solve signing mismatch must fail.",
    "repeat": "Repeat interrupted migration, rollback limits, and pending render jobs.",
}

NEGATIVE_TOKEN = "silent-uninstall-signing-mismatch"
NOT_PRESERVED = "private-media-not-preserved"
ACTIONS = ("migrate", "refuse", "silent-uninstall", "preserve")
EXPLICIT = frozenset({"migrate", "refuse", "preserve"})
SCENARIOS = ("interrupted-migration", "rollback-limits", "pending-render-jobs")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "layers",
    "releasePassed",
    "releaseSummary",
    "signed",
    "signingMismatch",
    "action",
    "sourcesPreserved",
    "profilesPreserved",
    "recoveryPreserved",
    "pendingRenderJobs",
    "migrationInterrupted",
    "rollbackWithinLimits",
    "scenario",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p145_build_the_layered_automated_test_system.py"
    spec = importlib.util.spec_from_file_location("p145_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_layers(payload, {
        "signed",
        "signingMismatch",
        "action",
        "sourcesPreserved",
        "profilesPreserved",
        "recoveryPreserved",
        "pendingRenderJobs",
        "migrationInterrupted",
        "rollbackWithinLimits",
        "scenario",
    })
    faults = list(bundle["faults"])
    signed = _GATE.require_bool(payload["signed"], "signed")
    mismatch = _GATE.require_bool(payload["signingMismatch"], "signingMismatch")
    action = _GATE.require_text(payload["action"], "action")
    _GATE.require(action in ACTIONS, "action is not recognized")
    sources = _GATE.require_bool(payload["sourcesPreserved"], "sourcesPreserved")
    profiles = _GATE.require_bool(payload["profilesPreserved"], "profilesPreserved")
    recovery = _GATE.require_bool(payload["recoveryPreserved"], "recoveryPreserved")
    pending = _GATE.require_int(payload["pendingRenderJobs"], "pendingRenderJobs")
    interrupted = _GATE.require_bool(payload["migrationInterrupted"], "migrationInterrupted")
    rollback_ok = _GATE.require_bool(payload["rollbackWithinLimits"], "rollbackWithinLimits")
    scenario = _GATE.require_text(payload["scenario"], "scenario")
    _GATE.require(scenario in SCENARIOS, "scenario is not recognized")
    kept = sources and profiles and recovery
    if action == "silent-uninstall" or (mismatch and action not in EXPLICIT):
        faults.append(NEGATIVE_TOKEN)
    if not kept:
        faults.append(NOT_PRESERVED)
    if interrupted and not kept:
        faults.append(NOT_PRESERVED)
    if not rollback_ok and not kept:
        faults.append(NOT_PRESERVED)
    if not signed and action == "migrate":
        faults.append("unsigned-migration")
    extra = [{
        "signed": signed,
        "signingMismatch": mismatch,
        "action": action,
        "sourcesPreserved": sources,
        "profilesPreserved": profiles,
        "recoveryPreserved": recovery,
        "pendingRenderJobs": pending,
        "migrationInterrupted": interrupted,
        "rollbackWithinLimits": rollback_ok,
        "scenario": scenario,
        "kept": kept,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        NOT_PRESERVED: CASE["expected"],
        "unsigned-migration": "migration requires an authorized signed update",
    }
    return _GATE.finish_layers(CASE, bundle, faults, extra, texts)
