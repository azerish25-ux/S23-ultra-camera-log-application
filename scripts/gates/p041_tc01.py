"""TC-P041-01 neutral target invalidity.

Replace an approved neutral patch with a clipped, textured, specular, or
incorrectly identified region. Whole-image average brightness is not a known
neutral target and must not become a measured profile.
"""

from __future__ import annotations

CASE_ID = "TC-P041-01"
INTERVENTION = (
    "Replace the approved neutral patch with a clipped, textured, specular, or "
    "incorrectly identified region."
)
EXPECTED = (
    "Reject scale calibration or retain an explicitly provisional result rather than "
    "fabricating a measured profile."
)
NEGATIVE = "Whole-image average brightness cannot substitute for a known neutral target."

_TARGETS = (
    "approved",
    "clipped",
    "textured",
    "specular",
    "incorrect",
    "dark",
    "colored",
    "mixed",
    "partial-clip",
)
_ILLUMINANTS = ("D65", "tungsten", "colored", "narrow")
_PAYLOAD_KEYS = (
    "target",
    "illuminant",
    "provisional",
    "wholeImageAverage",
    "patchId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "provisional", "neutral_checked"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject an invalid neutral or keep an explicitly provisional result."""
    target, illuminant, provisional, whole, patch = _payload(payload)
    preserved = [f"patch:{patch}", f"target:{target}", f"illuminant:{illuminant}"]
    reasons = [EXPECTED]
    if whole:
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "whole-image average was not used as a neutral target"],
            ["whole-image-average"],
            preserved,
            ["measured profile was not fabricated"],
        )
    if target != "approved":
        claims = [f"invalid-neutral:{target}"]
        reasons.append(f"neutral target {target} is not an approved patch")
        if provisional:
            return _result(
                "provisional",
                reasons + ["explicitly provisional result is not a measured profile"],
                claims,
                preserved,
                ["explicitly provisional; not a measured profile"],
            )
        return _result(
            "rejected",
            reasons + ["scale calibration rejected"],
            claims,
            preserved,
            ["measured profile was not fabricated"],
        )
    return _result(
        "neutral_checked",
        reasons + ["approved patch was checked and was not fabricated into a measured profile"],
        [],
        preserved,
        ["not a measured profile"],
    )


def _payload(payload: object) -> tuple[str, str, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    target = payload["target"]
    illuminant = payload["illuminant"]
    if target not in _TARGETS:
        raise ValueError("target is not a known neutral-patch class")
    if illuminant not in _ILLUMINANTS:
        raise ValueError("illuminant is not a known class")
    provisional = payload["provisional"]
    whole = payload["wholeImageAverage"]
    if type(provisional) is not bool or type(whole) is not bool:
        raise ValueError("provisional and wholeImageAverage must be bools")
    patch = payload["patchId"]
    if not isinstance(patch, str) or not patch or patch != patch.strip():
        raise ValueError("patchId must be a non-empty string")
    return target, illuminant, provisional, whole, patch


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P041-01 must not yield qualified or allowed")
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
