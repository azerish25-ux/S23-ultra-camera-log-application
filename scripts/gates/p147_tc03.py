"""TC-P147-03 Hostile imported file.

Host reference. A subject import is recorded only when magic matches, sizes
match within 0, the header was validated before allocation, and no archive
path contains '../'. Trusting a disagreeing extension or accepting an
unvalidated header is rejected. Escaping storage or corrupting retained media
is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P147-03",
    "phase": "P147",
    "workstream": 19,
    "name": "Hostile imported file",
    "intervention": "Submit malformed lengths, excessive dimensions, nonfinite transforms, or archive traversal paths.",
    "expected": "Reject within bounded resource limits without escaping storage or corrupting retained media.",
    "negative": "Trusting extensions or unvalidated headers must fail.",
    "repeat": "Repeat parser truncation, decompression pressure, and repeated invalid imports.",
}

NEGATIVE_TOKEN = "trusted-extension-or-unvalidated-header"
HOSTILE_ACCEPTED = "hostile-import-not-rejected"
STORAGE_DAMAGE = "storage-escape-or-media-corruption"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "imports",
    "corpus",
    "subject",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p147_secure_media_and_profile_import_boundaries.py"
    spec = importlib.util.spec_from_file_location("p147_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _subject_faults(subject: dict) -> list[str]:
    faults: list[str] = []
    trusted = subject["trust_extension"] and subject["magic_disagrees"]
    accepted_unvalidated = subject["accepted"] and subject["header_validated"] is False
    if trusted or accepted_unvalidated:
        faults.append(NEGATIVE_TOKEN)
    if subject["accepted"] and subject["faults"]:
        faults.append(HOSTILE_ACCEPTED)
    if subject["escaped"] or subject["source_corrupted"]:
        faults.append(STORAGE_DAMAGE)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    subject = _GATE.parse_import(payload["subject"], "subject", {"accepted"})
    faults = list(bundle["faults"])
    faults.extend(_subject_faults(subject))
    extra = [{
        "id": subject["id"],
        "accepted": subject["accepted"],
        "decision": subject["decision"],
        "faults": list(subject["faults"]),
        "magic_disagrees": subject["magic_disagrees"],
        "header_validated": subject["header_validated"],
        "declared_size": subject["declared_size"],
        "actual_size": subject["actual_size"],
        "paths": list(subject["paths"]),
        "escaped": subject["escaped"],
        "source_corrupted": subject["source_corrupted"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            HOSTILE_ACCEPTED: CASE["expected"],
            STORAGE_DAMAGE: "escaping storage or corrupting retained media is rejected",
        },
    )
