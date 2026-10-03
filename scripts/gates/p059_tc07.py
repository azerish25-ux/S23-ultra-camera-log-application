"""TC-P059-07 double viewing transform.

Intervention: Apply a display or log transform twice through preview,
development, or editor configuration.
Expected: Detect the mismatch using reference patches and preserve separate
clean and rendered branches.
Negative: A generic player thumbnail must not certify correct color interpretation.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P059-07"
INTERVENTION = (
    "Apply a display or log transform twice through preview, development, or editor configuration."
)
EXPECTED = (
    "Detect the mismatch using reference patches and preserve separate clean and rendered branches."
)
NEGATIVE = "A generic player thumbnail must not certify correct color interpretation."

_STAGES = ("preview", "development", "editor")
_ASSIGNMENTS = ("manual", "automatic", "none")
_PAYLOAD_KEYS = (
    "stage",
    "assignment",
    "transformCount",
    "patchId",
    "cleanCode",
    "renderedCode",
    "thumbnailAgrees",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "mismatch_detected")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_NUMBER = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Detect a doubled viewing transform without certifying a thumbnail."""
    stage, assignment, count, patch, clean, rendered, thumbnail = _payload(payload)
    preserved = [
        "stage:" + stage,
        "assignment:" + assignment,
        f"transforms:{count}",
        "patch:" + patch,
        "clean:" + clean,
        "rendered:" + rendered,
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if count == 2 or clean != rendered:
        rejected.append("double-transform" if count == 2 else "patch-mismatch")
        reasons.append("reference patch mismatch kept the clean and rendered branches separate")
    if thumbnail:
        rejected.append("thumbnail-not-certification")
        reasons.append(NEGATIVE)
    if count == 2 or clean != rendered:
        decision = "mismatch_detected"
        questions = ["clean and rendered branches were not collapsed"]
    else:
        decision = "withheld"
        reasons.append("single transform still is not a certified color interpretation")
        questions = ["thumbnail was not used as a certificate"] if thumbnail else [
            "single viewing transform is not a qualification"
        ]
    if thumbnail and decision == "withheld":
        decision = "rejected"
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, int, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    assignment = payload["assignment"]
    if assignment not in _ASSIGNMENTS:
        raise ValueError("assignment is unsupported")
    count = payload["transformCount"]
    if count not in (1, 2) or type(count) is not int:
        raise ValueError("transformCount must be 1 or 2")
    patch = payload["patchId"]
    if not isinstance(patch, str) or _TOKEN.fullmatch(patch) is None:
        raise ValueError("patchId must be a token")
    clean = _number(payload["cleanCode"], "cleanCode")
    rendered = _number(payload["renderedCode"], "renderedCode")
    thumbnail = payload["thumbnailAgrees"]
    if type(thumbnail) is not bool:
        raise ValueError("thumbnailAgrees must be a bool")
    return stage, assignment, count, patch, clean, rendered, thumbnail


def _number(value: object, label: str) -> str:
    if not isinstance(value, str) or _NUMBER.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical decimal string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P059-07 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
