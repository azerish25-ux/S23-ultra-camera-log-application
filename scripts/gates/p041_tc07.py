"""TC-P041-07 unrecorded measurement conditions.

Removing illuminant, exposure, target identity, or source revision downgrades
or rejects the measurement claim. The exploratory data stays. An attractive
color result without that context is not the default measured profile.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P041-07"
INTERVENTION = (
    "Remove illuminant, exposure, target identity, or source revision from calibration evidence."
)
EXPECTED = (
    "Downgrade or reject the measurement claim while retaining the data for exploratory research."
)
NEGATIVE = (
    "An attractive color result without experimental context must not become the default measured profile."
)

_FIELDS = ("illuminant", "exposure", "target", "source-revision")
_ORIGINS = ("measurement", "author-import", "manufacturer-metadata")
_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,63}$")
_PAYLOAD_KEYS = (
    "missingFields",
    "authorAssertion",
    "origin",
    "attractiveColor",
    "exploratoryToken",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "exploratory", "assertion_retained", "provisional", "conditions_recorded"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Downgrade a measurement claim when experimental context is missing."""
    missing, assertion, origin, attractive, token = _payload(payload)
    preserved = [
        f"assertion:{assertion}",
        f"origin:{origin}",
        f"data:{token}",
        "missing:" + (",".join(missing) if missing else "none"),
    ]
    missing_claims = [f"missing-{field}" for field in missing]
    if missing and attractive:
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "attractive color was not adopted as the default measured profile"],
            ["attractive-color-without-context", *missing_claims],
            preserved,
            ["retained for exploratory research"],
        )
    if missing:
        return _result(
            "exploratory",
            [EXPECTED, "measurement claim downgraded", "exploratory data retained"],
            missing_claims,
            preserved,
            ["retained for exploratory research"],
        )
    if origin == "author-import":
        claims = ["imported-author-assertion"] if assertion == "measured" else []
        return _result(
            "assertion_retained",
            [
                EXPECTED,
                f"author assertion {assertion} was retained separately",
                "an imported assertion is not the default measured profile",
            ],
            claims,
            preserved,
            ["author assertion is not importer status"],
        )
    if origin == "manufacturer-metadata":
        return _result(
            "provisional",
            [
                EXPECTED,
                "manufacturer-metadata starting profile stays provisional",
                "provisional is not the default measured profile",
            ],
            ["manufacturer-starting-profile"],
            preserved,
            ["not a measured profile"],
        )
    reasons = [EXPECTED, "illuminant, exposure, target, and source revision were recorded"]
    if attractive:
        reasons.append("attractive color was not the measurement claim")
    return _result(
        "conditions_recorded",
        reasons,
        [],
        preserved,
        ["recorded conditions are not physical S23 qualification"],
    )


def _payload(payload: object) -> tuple[list[str], str, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    missing = payload["missingFields"]
    if not isinstance(missing, list):
        raise ValueError("missingFields must be a list")
    if any(field not in _FIELDS for field in missing):
        raise ValueError("missingFields contains an unknown condition")
    if len(missing) != len(set(missing)):
        raise ValueError("missingFields must be unique")
    ordered = [field for field in _FIELDS if field in missing]
    assertion = payload["authorAssertion"]
    if not isinstance(assertion, str) or _TOKEN.fullmatch(assertion) is None:
        raise ValueError("authorAssertion must be a token")
    origin = payload["origin"]
    if origin not in _ORIGINS:
        raise ValueError("origin must be measurement, author-import, or manufacturer-metadata")
    attractive = payload["attractiveColor"]
    if type(attractive) is not bool:
        raise ValueError("attractiveColor must be a bool")
    token = payload["exploratoryToken"]
    if not isinstance(token, str) or _TOKEN.fullmatch(token) is None:
        raise ValueError("exploratoryToken must be a token")
    return ordered, assertion, origin, attractive, token


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P041-07 must not yield qualified or allowed")
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
