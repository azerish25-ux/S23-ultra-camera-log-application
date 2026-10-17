"""TC-P151-06 Update threatens private media.

Host reference. An update must preserve sources, profiles, and recovery data
or refuse explicitly. A silent uninstall, including one used to clear a signing
mismatch, is rejected. A drop in retained counts is destructive and rejected.
Release-note badge rules still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P151-06",
    "phase": "P151",
    "workstream": 19,
    "name": "Update threatens private media",
    "intervention": "Install an authorized signed update over a version containing sources, profiles, and recovery data.",
    "expected": "Preserve compatible data and provide explicit migration or refusal rather than destructive convenience.",
    "negative": "Uninstalling silently to solve signing mismatch must fail.",
    "repeat": "Repeat interrupted migration, rollback limits, and pending render jobs.",
}

NEGATIVE_TOKEN = "silent-uninstall-for-signing-mismatch"
DESTRUCTIVE_UPDATE = "destructive-update"
COUNT_KEYS = (
    "sourcesBefore",
    "profilesBefore",
    "recoveryBefore",
    "sourcesAfter",
    "profilesAfter",
    "recoveryAfter",
)
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "claims",
    "implementedFeatures",
    "aspirationalRequirements",
    "knownFailures",
    "signed",
    "migration",
    *COUNT_KEYS,
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p151_generate_honest_release_notes_and_capability_badges.py"
    spec = importlib.util.spec_from_file_location("p151_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _counts(payload: dict) -> dict:
    counts = {}
    for key in COUNT_KEYS:
        value = _GATE.require_int(payload[key], key)
        _GATE.require(value >= 0, key + " must be >= 0")
        counts[key] = value
    return counts


def _update_faults(signed: bool, migration: str, counts: dict) -> list[str]:
    faults: list[str] = []
    if migration == "silent-uninstall":
        faults.append(NEGATIVE_TOKEN)
    decreased = (
        counts["sourcesAfter"] < counts["sourcesBefore"]
        or counts["profilesAfter"] < counts["profilesBefore"]
        or counts["recoveryAfter"] < counts["recoveryBefore"]
    )
    if decreased or migration not in {"explicit", "refused"}:
        faults.append(DESTRUCTIVE_UPDATE)
    if not signed and migration == "silent-uninstall":
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    signed = _GATE.require_bool(payload["signed"], "signed")
    migration = _GATE.require_text(payload["migration"], "migration")
    _GATE.require(migration in _GATE.MIGRATIONS, "migration is not recognized")
    counts = _counts(payload)
    faults = list(bundle["faults"])
    faults.extend(_update_faults(signed, migration, counts))
    extra = [{"signed": signed, "migration": migration, **counts}]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            DESTRUCTIVE_UPDATE: CASE["expected"],
        },
    )
