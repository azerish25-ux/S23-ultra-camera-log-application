"""TC-P057-07 double viewing transform.

Intervention: Apply a display or log transform twice through preview,
development, or editor configuration.
Expected: Detect the mismatch using reference patches and preserve separate
clean and rendered branches.
Negative: A generic player thumbnail must not certify correct color interpretation.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P057-07"
INTERVENTION = (
    "Apply a display or log transform twice through preview, development, or editor "
    "configuration."
)
EXPECTED = (
    "Detect the mismatch using reference patches and preserve separate clean and "
    "rendered branches."
)
NEGATIVE = "A generic player thumbnail must not certify correct color interpretation."

_PATHS = ("preview", "development", "editor")
_ASSIGNMENTS = ("manual", "auto-tag")
_PAYLOAD_KEYS = ("path", "assignment", "transformCount", "patchDelta", "thumbnailAgrees")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Keep clean and rendered branches apart. A thumbnail is not a certificate."""
    path, assignment, count, delta, thumbnail = _payload(payload)
    rendered = "double-transform" if count >= 2 else "single-transform" if count == 1 else "identity"
    preserved = [
        f"path:{path}",
        f"assignment:{assignment}",
        f"transform-count:{count}",
        f"patch-delta:{delta}",
        "branch:clean",
        f"branch:rendered:{rendered}",
        f"thumbnail-agrees:{str(thumbnail).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = ["clean and rendered branches stay separate"]
    if count >= 2:
        reasons.append(f"reference patch delta {delta} detected a repeated transform on {path}")
        rejected = ["double-viewing-transform"]
        if thumbnail:
            rejected.append("thumbnail-certifies-color")
            reasons.append(NEGATIVE)
        else:
            reasons.append("thumbnail agreement was not available and was not assumed")
        questions.append(f"{assignment} assignment did not repair the double transform")
        return _result("rejected", reasons, rejected, preserved, questions)
    if thumbnail:
        reasons.append(NEGATIVE)
        reasons.append("thumbnail agreement did not certify the single path")
        return _result("rejected", reasons, ["thumbnail-certifies-color"], preserved, questions)
    reasons.append("no double transform was detected")
    questions.append(f"{assignment} tags are not a color certificate")
    return _result("withheld", reasons, [], preserved, questions)


def _payload(payload: object) -> tuple[str, str, int, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    path = payload["path"]
    assignment = payload["assignment"]
    if path not in _PATHS:
        raise ValueError("path is unknown")
    if assignment not in _ASSIGNMENTS:
        raise ValueError("assignment is unknown")
    count = payload["transformCount"]
    if type(count) is not int or not 0 <= count <= 4:
        raise ValueError("transformCount must be an int from 0 through 4")
    delta = payload["patchDelta"]
    if not isinstance(delta, str) or _DECIMAL.fullmatch(delta) is None:
        raise ValueError("patchDelta must be a canonical non-negative decimal")
    if Decimal(delta) > Decimal("10"):
        raise ValueError("patchDelta is outside the host range")
    thumbnail = payload["thumbnailAgrees"]
    if type(thumbnail) is not bool:
        raise ValueError("thumbnailAgrees must be a bool")
    return path, assignment, count, delta, thumbnail


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
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
