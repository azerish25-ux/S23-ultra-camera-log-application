"""TC-P061-07 double viewing transform.

Intervention: Apply a display or log transform twice through preview,
development, or editor configuration.
Expected: Detect the mismatch using reference patches and preserve separate
clean and rendered branches.
Negative: A generic player thumbnail must not certify correct color interpretation.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P061-07"
INTERVENTION = (
    "Apply a display or log transform twice through preview, development, or editor configuration."
)
EXPECTED = (
    "Detect the mismatch using reference patches and preserve separate clean and rendered branches."
)
NEGATIVE = "A generic player thumbnail must not certify correct color interpretation."
REPEAT = "Repeat with manual editor assignments and automatically detected source tags."

_STAGES = ("preview", "development", "editor")
_ASSIGNMENTS = ("manual", "auto-tag")
_PAYLOAD_KEYS = (
    "stage",
    "assignment",
    "applications",
    "cleanPatch",
    "renderedPatch",
    "expectedRendered",
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
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Detect a second viewing transform. Thumbnails do not certify the patches."""
    stage, assignment, applications, clean, rendered, expected, thumbnail = _payload(payload)
    preserved = [
        f"stage:{stage}",
        f"assignment:{assignment}",
        f"clean:{clean}",
        f"rendered:{rendered}",
        f"expected:{expected}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"repeat coverage includes {REPEAT}"]
    questions = ["clean and rendered branches were both preserved"]
    rejected: list[str] = []
    if applications == 2:
        rejected.append("double-viewing-transform")
        reasons.append("display or log transform was applied twice")
    if Decimal(rendered) != Decimal(expected):
        rejected.append("patch-mismatch")
        reasons.append("reference patch does not match the rendered branch")
    if thumbnail and rejected:
        rejected.append("thumbnail-not-certification")
        reasons.append(NEGATIVE)
    elif thumbnail:
        reasons.append("thumbnail agreement was ignored and did not certify interpretation")
        questions.append("generic player thumbnail is not certification")
    if rejected:
        decision = "rejected"
    else:
        decision = "branches_separated"
        reasons.append("one viewing transform matched the reference patch")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
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
    applications = payload["applications"]
    if type(applications) is not int or isinstance(applications, bool) or applications not in {1, 2}:
        raise ValueError("applications must be 1 or 2")
    clean = _decimal(payload["cleanPatch"], "cleanPatch")
    rendered = _decimal(payload["renderedPatch"], "renderedPatch")
    expected = _decimal(payload["expectedRendered"], "expectedRendered")
    thumbnail = payload["thumbnailAgrees"]
    if type(thumbnail) is not bool:
        raise ValueError("thumbnailAgrees must be a bool")
    return stage, assignment, applications, clean, rendered, expected, thumbnail


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value == "-0":
        raise ValueError(label + " must be a canonical signed decimal")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P061-07 must not yield qualified or allowed")
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
