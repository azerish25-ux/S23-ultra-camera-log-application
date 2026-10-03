"""TC-P058-07 double viewing transform.

Intervention: Apply a display or log transform twice through preview,
development, or editor configuration.
Expected: Detect the mismatch using reference patches and preserve separate
clean and rendered branches.
Negative: A generic player thumbnail must not certify correct color interpretation.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P058-07"
INTERVENTION = "Apply a display or log transform twice through preview, development, or editor configuration."
EXPECTED = "Detect the mismatch using reference patches and preserve separate clean and rendered branches."
NEGATIVE = "A generic player thumbnail must not certify correct color interpretation."

_STAGES = ("preview", "development", "editor")
_ASSIGNMENTS = ("manual", "auto-detected")
_PAYLOAD_KEYS = (
    "stage",
    "transformCount",
    "assignment",
    "patchId",
    "patchDelta",
    "cleanBranch",
    "renderedBranch",
    "thumbnailCertifies",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Detect a doubled viewing transform and keep clean and rendered branches."""
    stage, count, assignment, patch, delta, clean, rendered, thumbnail = _payload(payload)
    preserved = [
        f"stage:{stage}",
        f"assignment:{assignment}",
        f"patch:{patch}",
        f"delta:{delta}",
        f"clean:{clean}",
        f"rendered:{rendered}",
        f"transforms:{count}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"{assignment} assignment at {stage} does not certify color"]
    if thumbnail:
        rejected.append("thumbnail-not-certificate")
        reasons.append(NEGATIVE)
    if count >= 2:
        rejected.append("double-viewing-transform")
        reasons.append(f"reference patch {patch} delta {delta} shows a repeated transform")
    if clean == rendered:
        rejected.append("branches-collapsed")
        reasons.append("clean and rendered branches must stay separate")
    if rejected:
        decision = "rejected"
        questions.append("both branches remain in the inventory")
    elif count == 1:
        decision = "branches_separated"
        reasons.append("single transform kept separate clean and rendered branches")
    else:
        decision = "withheld"
        reasons.append("no viewing transform was certified")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    count = payload["transformCount"]
    if type(count) is not int or count not in {0, 1, 2}:
        raise ValueError("transformCount must be 0, 1, or 2")
    assignment = payload["assignment"]
    if assignment not in _ASSIGNMENTS:
        raise ValueError("assignment is unsupported")
    patch = payload["patchId"]
    clean = payload["cleanBranch"]
    rendered = payload["renderedBranch"]
    for name, value in (("patchId", patch), ("cleanBranch", clean), ("renderedBranch", rendered)):
        if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
            raise ValueError(name + " must be a token")
    delta = payload["patchDelta"]
    if not isinstance(delta, str) or _DECIMAL.fullmatch(delta) is None:
        raise ValueError("patchDelta must be a canonical decimal")
    if Decimal(delta) < 0:
        raise ValueError("patchDelta must be non-negative")
    thumbnail = payload["thumbnailCertifies"]
    if type(thumbnail) is not bool:
        raise ValueError("thumbnailCertifies must be a bool")
    return stage, count, assignment, patch, delta, clean, rendered, thumbnail


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P058-07 must not yield qualified or allowed")
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
