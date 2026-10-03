"""TC-P047-01 neutral target invalidity.

Intervention: Replace the approved neutral patch with a clipped, textured,
specular, or incorrectly identified region.
Expected: Reject scale calibration or retain an explicitly provisional result
rather than fabricating a measured profile.
Negative: Whole-image average brightness cannot substitute for a known neutral
target.
"""

from __future__ import annotations

CASE_ID = "TC-P047-01"
INTERVENTION = (
    "Replace the approved neutral patch with a clipped, textured, specular, or "
    "incorrectly identified region."
)
EXPECTED = (
    "Reject scale calibration or retain an explicitly provisional result rather "
    "than fabricating a measured profile."
)
NEGATIVE = "Whole-image average brightness cannot substitute for a known neutral target."

_KINDS = (
    "approved-neutral",
    "clipped",
    "textured",
    "specular",
    "misidentified",
    "dark",
    "colored-illumination",
    "mixed-pixels",
    "partial-clip",
)
_TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789-:+."
_PAYLOAD_KEYS = (
    "patchKind",
    "wholeImageAverage",
    "sourceFrameId",
    "roi",
    "reportedBrightness",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "provisional")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject an invalid neutral, or keep an approved patch provisional."""
    kind, average, frame, roi, brightness = _payload(payload)
    preserved = [
        "frame:" + frame,
        "roi:" + roi,
        "patch:" + kind,
        "brightness:" + brightness,
    ]
    rejected: list[str] = []
    if kind != "approved-neutral":
        rejected.append("invalid-neutral:" + kind)
    if average:
        rejected.append("whole-image-average")
    if rejected:
        reasons = [EXPECTED, "scale calibration rejected", "measured profile not fabricated"]
        if average:
            reasons.append(NEGATIVE)
        if kind != "approved-neutral":
            reasons.append("invalid neutral target is not a measured profile")
        return _result("rejected", reasons, rejected, preserved, ["measured profile not fabricated"])
    return _result(
        "provisional",
        [
            EXPECTED,
            "approved neutral patch retained as provisional",
            "provisional result is not a fabricated measured profile",
        ],
        [],
        preserved,
        ["scale remains provisional on the host fixture"],
    )


def _payload(payload: object) -> tuple[str, bool, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    kind = payload["patchKind"]
    if kind not in _KINDS:
        raise ValueError("patchKind is unsupported")
    average = payload["wholeImageAverage"]
    if type(average) is not bool:
        raise ValueError("wholeImageAverage must be a bool")
    frame = _token(payload["sourceFrameId"], "sourceFrameId")
    roi = _token(payload["roi"], "roi")
    brightness = _decimal(payload["reportedBrightness"], "reportedBrightness")
    return kind, average, frame, roi, brightness


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or any(char not in _TOKEN for char in value):
        raise ValueError(label + " must be a canonical token")
    return value


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value[0] == "-":
        raise ValueError(label + " must be a canonical decimal string")
    body = value
    if "." in body:
        whole, frac = body.split(".", 1)
        if not frac or frac[-1] == "0" or not whole or not _digits(whole) or not _digits(frac):
            raise ValueError(label + " must be a canonical decimal string")
        if len(whole) > 1 and whole[0] == "0":
            raise ValueError(label + " must be a canonical decimal string")
    else:
        if not _digits(body) or (len(body) > 1 and body[0] == "0"):
            raise ValueError(label + " must be a canonical decimal string")
    return value


def _digits(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("neutral decision cannot be qualified or allowed")
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
