"""TC-P119-06 Rolling-shutter model violation.

Host fixture. Independent foreground motion blocks an unjustified global shear.
Advertising one global shear as universal rolling-shutter removal is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P119-06"
NAME = "Rolling-shutter model violation"
INTERVENTION = (
    "Place independently moving foreground content in a scene used for global camera-motion correction."
)
EXPECTED = "Restrict or qualify the correction rather than applying an unjustified global warp to every object."
NEGATIVE = "One global shear must not be advertised as universal rolling-shutter removal."
REPEAT = "Repeat pans, vibrations, moving subjects, and unknown readout timing."
CORRECTIONS = ("none", "restricted", "global-shear")
REPEATS = ("pan", "vibration", "moving-subject", "unknown-readout")
PAYLOAD_KEYS = (
    "evidenceId",
    "independentForeground",
    "correction",
    "advertisedUniversal",
    "readoutKnown",
    "repeat",
    "selectedLimitId",
    "measuredLimits",
    "guidance",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_CORE = None


def _core():
    global _CORE
    if _CORE is None:
        path = Path(__file__).resolve().parent / "p119_add_practical_cinematographic_guidance.py"
        spec = importlib.util.spec_from_file_location("p119_add_practical_cinematographic_guidance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CORE = module
    return _CORE


def evaluate(payload: dict) -> dict:
    """Reject a universal global shear. Restricted correction can still be recorded."""
    evidence, foreground, correction, advertised, readout_known, repeat, selected, limits, guidance = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {repeat}"]
    if advertised:
        rejected.append("global-shear-as-universal-rolling-shutter-removal")
        reasons.append(NEGATIVE)
    if foreground and correction == "global-shear":
        rejected.append("unjustified-global-warp")
        reasons.append("independent foreground motion blocks a global warp")
    if correction == "global-shear" and not readout_known:
        rejected.append("unknown-readout-global-warp")
        reasons.append("unknown readout timing blocks a global shear")
    judged = _core().judge_guidance(limits, selected, guidance)
    for claim in judged["rejectedClaims"]:
        if claim not in rejected:
            rejected.append(claim)
    reasons.extend(judged["reasons"])
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("correction stays inside the rolling-shutter evidence")
    preserved = [
        evidence,
        f"correction:{correction}",
        f"foreground:{str(foreground).lower()}",
        f"readoutKnown:{str(readout_known).lower()}",
    ]
    preserved.extend(judged["preservedResults"])
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    correction = payload["correction"]
    if correction not in CORRECTIONS:
        raise ValueError("correction is unsupported")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    foreground = payload["independentForeground"]
    advertised = payload["advertisedUniversal"]
    readout = payload["readoutKnown"]
    for label, value in (
        ("independentForeground", foreground),
        ("advertisedUniversal", advertised),
        ("readoutKnown", readout),
    ):
        if type(value) is not bool:
            raise ValueError(f"{label} must be a bool")
    return (
        evidence,
        foreground,
        correction,
        advertised,
        readout,
        repeat,
        payload["selectedLimitId"],
        payload["measuredLimits"],
        payload["guidance"],
    )


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS or not reasons or preserved[0] not in preserved:
        raise ValueError("result contract drifted")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    return result
