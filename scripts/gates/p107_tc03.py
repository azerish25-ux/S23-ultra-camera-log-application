"""TC-P107-03 Relative-scale pumping.

Host reference. Stable background pairs are aligned by least squares.
Independent per-frame min-max normalization is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P107-03"
NAME = "Relative-scale pumping"
INTERVENTION = "Introduce a near object or scene-content change that alters raw model depth normalization."
EXPECTED = "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts."
NEGATIVE = "Independent min-max normalization per frame must fail."
REPEAT = "Repeat stationary backgrounds with changing foreground occupancy."
NEGATIVE_TOKEN = "per-frame-minmax"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "pairs",
    "holdout",
    "aligned_unit",
    "reference_unit",
    "force_unit_scale",
    "holdout_in_fit",
    "applyMutant",
    "per_frame_minmax",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _gate():
    path = Path(__file__).resolve().parent / "p107_align_relative_depth_scale_and_offset.py"
    spec = importlib.util.spec_from_file_location("p107_align_relative_depth_scale_and_offset", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    if type(payload["per_frame_minmax"]) is not bool:
        raise ValueError("per_frame_minmax must be a bool")
    fit = _gate().evaluate(
        {
            "caseId": CASE_ID,
            "evidenceId": evidence,
            "claim": payload["claim"],
            "pairs": payload["pairs"],
            "holdout": payload["holdout"],
            "aligned_unit": payload["aligned_unit"],
            "reference_unit": payload["reference_unit"],
            "force_unit_scale": payload["force_unit_scale"],
            "holdout_in_fit": payload["holdout_in_fit"],
            "applyMutant": payload["applyMutant"],
        }
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, *fit["reasons"]]
    rejected = list(fit["rejectedClaims"])
    if payload["per_frame_minmax"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("per-frame minimum and maximum were not used as the alignment")
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("decision must be recorded or rejected")
    questions = list(fit["openQuestions"])
    if REPEAT not in questions:
        questions.append(REPEAT)
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": fit["preservedResults"],
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
