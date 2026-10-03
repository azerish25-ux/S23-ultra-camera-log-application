"""TC-P062-07 double viewing transform.

Intervention: Apply a display or log transform twice through preview,
development, or editor configuration.
Expected: Detect the mismatch using reference patches and preserve separate
clean and rendered branches.
Negative: A generic player thumbnail must not certify correct color interpretation.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P062-07"
INTERVENTION = "Apply a display or log transform twice through preview, development, or editor configuration."
EXPECTED = "Detect the mismatch using reference patches and preserve separate clean and rendered branches."
NEGATIVE = "A generic player thumbnail must not certify correct color interpretation."
REPEAT = "Repeat with manual editor assignments and automatically detected source tags."

_ROUTES = ("preview", "development", "editor", "manual-assignment", "auto-tag")
_KINDS = ("display", "log")
_PAYLOAD_KEYS = (
    "sampleId",
    "route",
    "transformKind",
    "transformCount",
    "referencePatch",
    "observedPatch",
    "thumbnailCertifies",
    "cleanBranch",
    "renderedBranch",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Reject a second viewing transform and thumbnail-only certification."""
    fields = _payload(payload)
    preserved = [
        fields["sampleId"],
        f"route:{fields['route']}",
        f"kind:{fields['transformKind']}",
        f"count:{fields['transformCount']}",
        f"reference:{fields['referencePatch']}",
        f"observed:{fields['observedPatch']}",
        f"clean:{fields['cleanBranch']}",
        f"rendered:{fields['renderedBranch']}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [REPEAT]
    patches_differ = Decimal(fields["referencePatch"]) != Decimal(fields["observedPatch"])
    if fields["transformCount"] >= 2:
        rejected.append("double-viewing-transform")
        if patches_differ:
            reasons.append(
                f"reference {fields['referencePatch']} does not match observed {fields['observedPatch']}"
            )
        else:
            reasons.append("transform count is 2; patch equality does not cancel the second application")
    elif patches_differ:
        rejected.append("patch-mismatch")
        reasons.append(
            f"reference {fields['referencePatch']} does not match observed {fields['observedPatch']}"
        )
    if fields["thumbnailCertifies"]:
        rejected.append("thumbnail-not-certificate")
        reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
        reasons.append("clean and rendered branches were both retained")
    else:
        decision = "branches_preserved"
        reasons.append("one viewing transform matches the reference patch")
        reasons.append("clean and rendered branches stay separate")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    if payload["route"] not in _ROUTES:
        raise ValueError("route is unsupported")
    if payload["transformKind"] not in _KINDS:
        raise ValueError("transformKind is unsupported")
    count = payload["transformCount"]
    if type(count) is not int or isinstance(count, bool) or not 1 <= count <= 4:
        raise ValueError("transformCount must be an int from 1 through 4")
    _decimal(payload["referencePatch"], "referencePatch")
    _decimal(payload["observedPatch"], "observedPatch")
    if type(payload["thumbnailCertifies"]) is not bool:
        raise ValueError("thumbnailCertifies must be a bool")
    if payload["cleanBranch"] != "clean-log" or payload["renderedBranch"] != "rendered-delivery":
        raise ValueError("branches must be clean-log and rendered-delivery")
    if payload["cleanBranch"] == payload["renderedBranch"]:
        raise ValueError("branches must stay separate")
    return payload


def _decimal(value: object, name: str) -> None:
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value == "-0":
        raise ValueError(name + " must be a canonical signed decimal")


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P062-07 must not yield qualified or allowed")
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
