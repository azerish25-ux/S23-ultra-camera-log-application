"""TC-P064-07 double viewing transform.

Intervention: Apply a display or log transform twice through preview,
development, or editor configuration.
Expected: Detect the mismatch using reference patches and preserve separate
clean and rendered branches.
Negative: A generic player thumbnail must not certify correct color interpretation.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P064-07"
INTERVENTION = "Apply a display or log transform twice through preview, development, or editor configuration."
EXPECTED = "Detect the mismatch using reference patches and preserve separate clean and rendered branches."
NEGATIVE = "A generic player thumbnail must not certify correct color interpretation."
REPEAT = "Repeat with manual editor assignments and automatically detected source tags."

_PATHS = ("preview", "development", "editor")
_ASSIGNMENTS = ("manual", "automatic")
_KINDS = ("display", "log")
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_PAYLOAD_KEYS = (
    "path",
    "assignment",
    "transformCount",
    "transformKind",
    "referencePatchMismatch",
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


def evaluate(payload: dict) -> dict:
    """Detect a doubled viewing transform and keep clean and rendered branches."""
    path, assignment, count, kind, mismatch, clean, rendered, thumbnail = _payload(payload)
    preserved = [
        f"path:{path}",
        f"assignment:{assignment}",
        f"transform-count:{count}",
        f"transform-kind:{kind}",
        f"clean:{clean}",
        f"rendered:{rendered}",
        f"reference-mismatch:{_flag(mismatch)}",
        f"thumbnail-certifies:{_flag(thumbnail)}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [REPEAT, "clean and rendered branches stay separate"]
    rejected: list[str] = []
    if count >= 2 and mismatch:
        rejected.append("double-viewing-transform")
        reasons.append("mismatch detected using reference patches")
    elif count >= 2:
        rejected.append("undetected-double-transform")
        reasons.append("a second viewing transform was not detected by reference patches")
    elif mismatch:
        rejected.append("patch-mismatch")
        reasons.append("reference patches disagree")
    if thumbnail:
        rejected.append("thumbnail-not-interpretation")
        reasons.append(NEGATIVE)
        questions.append("thumbnail was not treated as color interpretation")
    if rejected:
        decision = "rejected"
    else:
        decision = "withheld"
        reasons.append("single viewing transform kept separate clean and rendered branches")
        questions.append("a withheld viewing path is not a color certification")
    return _result(decision, reasons, rejected, preserved, questions)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    path = payload["path"]
    if path not in _PATHS:
        raise ValueError("path is unsupported")
    assignment = payload["assignment"]
    if assignment not in _ASSIGNMENTS:
        raise ValueError("assignment is unsupported")
    count = payload["transformCount"]
    if type(count) is not int or count not in {1, 2}:
        raise ValueError("transformCount must be 1 or 2")
    kind = payload["transformKind"]
    if kind not in _KINDS:
        raise ValueError("transformKind is unsupported")
    mismatch = payload["referencePatchMismatch"]
    thumbnail = payload["thumbnailCertifies"]
    if type(mismatch) is not bool:
        raise ValueError("referencePatchMismatch must be a bool")
    if type(thumbnail) is not bool:
        raise ValueError("thumbnailCertifies must be a bool")
    clean = payload["cleanBranch"]
    rendered = payload["renderedBranch"]
    if not isinstance(clean, str) or _TOKEN.fullmatch(clean) is None:
        raise ValueError("cleanBranch must be a token")
    if not isinstance(rendered, str) or _TOKEN.fullmatch(rendered) is None:
        raise ValueError("renderedBranch must be a token")
    if clean == rendered:
        raise ValueError("clean and rendered branches must differ")
    return path, assignment, count, kind, mismatch, clean, rendered, thumbnail


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P064-07 must not yield qualified or allowed")
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
