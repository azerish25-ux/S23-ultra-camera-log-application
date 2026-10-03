"""TC-P050-03 boundary and halo support.

Intervention: Place an impulse or edge at the image boundary, row-buffer limit,
or tile seam.
Expected: Apply the documented border policy without stale reads, missing
support, or discontinuities.
Negative: Reading outside retained rows or ignoring required halos must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P050-03"
INTERVENTION = (
    "Place an impulse or edge at the image boundary, row-buffer limit, or tile seam."
)
EXPECTED = (
    "Apply the documented border policy without stale reads, missing support, or "
    "discontinuities."
)
NEGATIVE = "Reading outside retained rows or ignoring required halos must fail."

_POLICY = "replicate-nearest-retained-sample"
_CORNERS = ("tl", "tr", "bl", "br")
_SUPPORTS = ("north", "east", "south", "west", "seam")
_PLACES = _CORNERS + _SUPPORTS
_FEATURES = ("impulse", "edge")
_PAYLOAD_KEYS = (
    "place",
    "feature",
    "halo",
    "retainedRows",
    "rowLimit",
    "readOutside",
    "ignoreHalo",
    "staleRead",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "border_applied")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Apply the retained-row border policy. Outside reads and missing halos fail."""
    place, feature, halo, retained, row_limit, outside, ignore, stale = _payload(payload)
    preserved = [
        f"place:{place}",
        f"feature:{feature}",
        f"policy:{_POLICY}",
        f"halo:{halo}",
        f"retained-rows:{retained}",
        f"row-limit:{row_limit}",
    ]
    rejected: list[str] = []
    if outside:
        rejected.append("outside-retained-rows")
    if ignore:
        rejected.append("ignored-halo")
    if stale:
        rejected.append("stale-read")
    if rejected:
        reasons = [EXPECTED, NEGATIVE, "border policy was not satisfied"]
        return _result("rejected", reasons, rejected, preserved, ["support was not invented"])
    reasons = [
        EXPECTED,
        f"border policy {_POLICY}",
        "no stale read",
        "required halo stays inside retained rows",
        f"place:{place}",
    ]
    return _result("border_applied", reasons, [], preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    place = payload["place"]
    if place not in _PLACES:
        raise ValueError("place must be a corner or kernel-support boundary")
    feature = payload["feature"]
    if feature not in _FEATURES:
        raise ValueError("feature must be impulse or edge")
    halo = payload["halo"]
    if type(halo) is not int or not 1 <= halo <= 4:
        raise ValueError("halo must be an int from 1 through 4")
    retained = payload["retainedRows"]
    row_limit = payload["rowLimit"]
    if type(retained) is not int or retained < halo:
        raise ValueError("retainedRows must cover the halo")
    if type(row_limit) is not int or row_limit < retained:
        raise ValueError("rowLimit must reach the retained rows")
    outside = payload["readOutside"]
    ignore = payload["ignoreHalo"]
    stale = payload["staleRead"]
    for label, value in (
        ("readOutside", outside),
        ("ignoreHalo", ignore),
        ("staleRead", stale),
    ):
        if type(value) is not bool:
            raise ValueError(label + " must be a bool")
    return place, feature, halo, retained, row_limit, outside, ignore, stale


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("border decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
