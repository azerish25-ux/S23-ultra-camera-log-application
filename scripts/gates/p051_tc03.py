"""TC-P051-03 boundary and halo support.

Intervention: Place an impulse or edge at the image boundary, row-buffer limit,
or tile seam.
Expected: Apply the documented border policy without stale reads, missing
support, or discontinuities.
Negative: Reading outside retained rows or ignoring required halos must fail.
"""

from __future__ import annotations

from fractions import Fraction

CASE_ID = "TC-P051-03"
INTERVENTION = (
    "Place an impulse or edge at the image boundary, row-buffer limit, or tile seam."
)
EXPECTED = (
    "Apply the documented border policy without stale reads, missing support, or discontinuities."
)
NEGATIVE = "Reading outside retained rows or ignoring required halos must fail."

_SITES = (
    "corner-nw",
    "corner-ne",
    "corner-sw",
    "corner-se",
    "kernel-north",
    "kernel-south",
    "tile-seam",
)
_PAYLOAD_KEYS = ("site", "impulse", "readOutside", "ignoreHalo", "staleSlot")
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
    """Omit missing rows. Outside reads, stale slots, and dropped halos fail."""
    site, impulse, read_outside, ignore_halo, stale_slot = _payload(payload)
    honest = _honest(site, impulse)
    preserved = [f"site:{site}", f"impulse:{impulse}", f"border:{site}:{honest}"]
    rejected: list[str] = []
    if read_outside:
        rejected.append("outside-retained-row")
    if stale_slot:
        rejected.append("stale-buffer-slot")
    if ignore_halo:
        rejected.append("ignored-halo")
    if rejected:
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "border policy was not applied"],
            rejected,
            preserved,
            ["support not taken from outside the retained rows"],
        )
    return _result(
        "border_applied",
        [EXPECTED, "missing rows omitted", f"border value {honest}"],
        [],
        preserved,
        [],
    )


def _canon(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _honest(site: str, impulse: int) -> str:
    """Hand borders for impulse placement. Missing samples are omitted, not zero-filled."""
    if site == "corner-nw":
        green = Fraction(impulse + 0, 2)
        return f"0,{_canon(green)},0"
    if site == "corner-ne":
        return f"0,{impulse},0"
    if site == "corner-sw":
        return f"0,{impulse},0"
    if site == "corner-se":
        green = Fraction(impulse, 3)
        return f"0,{_canon(green)},0"
    if site == "kernel-north":
        green = Fraction(impulse, 4)
        return f"0,{_canon(green)},0"
    if site == "kernel-south":
        green = Fraction(impulse, 3)
        return f"0,{_canon(green)},0"
    red = Fraction(impulse, 2)
    return f"{_canon(red)},0,0"


def _payload(payload: object) -> tuple[str, int, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is not a border, kernel limit, or tile seam")
    impulse = payload["impulse"]
    if type(impulse) is not int or not 1 <= impulse <= 100000:
        raise ValueError("impulse must be a positive int")
    return (
        site,
        impulse,
        _bool(payload["readOutside"], "readOutside"),
        _bool(payload["ignoreHalo"], "ignoreHalo"),
        _bool(payload["staleSlot"], "staleSlot"),
    )


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(label + " must be a bool")
    return value


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
