"""TC-P042-01 neutral target invalidity.

A clipped, textured, specular, or misidentified region is not a neutral patch.
A whole-image average is not a substitute. Provisional results stay labeled
and never become a measured profile.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P042-01"
INTERVENTION = (
    "Replace the approved neutral patch with a clipped, textured, specular, "
    "or incorrectly identified region."
)
EXPECTED = (
    "Reject scale calibration or retain an explicitly provisional result "
    "rather than fabricating a measured profile."
)
NEGATIVE = "Whole-image average brightness cannot substitute for a known neutral target."

_REGIONS = (
    "approved_neutral",
    "clipped",
    "textured",
    "specular",
    "misidentified",
    "whole_image",
)
_REPEATS = ("dark_patches", "colored_illumination", "mixed_pixels", "partial_clipping")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_BRIGHTNESS = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")
_PAYLOAD_KEYS = ("patchId", "regionClass", "repeat", "meanBrightness", "provisional")
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
    """Reject a fake neutral, or keep an explicitly provisional result."""
    patch_id, region, repeat, brightness, provisional = _payload(payload)
    preserved = [
        f"patch:{patch_id}",
        f"mean-brightness:{brightness}",
        f"repeat:{repeat}",
        f"region:{region}",
    ]
    if region == "whole_image":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "whole-image average was not used as a neutral target"],
            ["whole-image-average"],
            preserved,
            ["no measured profile was fabricated"],
        )
    if provisional:
        return _result(
            "provisional",
            [EXPECTED, INTERVENTION, f"provisional result for {region} under {repeat}"],
            [],
            preserved,
            ["provisional is not a measured profile"],
        )
    return _result(
        "rejected",
        [EXPECTED, INTERVENTION, f"scale calibration rejected for {region} under {repeat}"],
        [f"invalid-neutral:{region}", f"repeat:{repeat}"],
        preserved,
        ["scale calibration was not fabricated"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    patch_id = _token(payload["patchId"], "patchId")
    region = _choice(payload["regionClass"], _REGIONS, "regionClass")
    repeat = _choice(payload["repeat"], _REPEATS, "repeat")
    brightness = payload["meanBrightness"]
    if not isinstance(brightness, str) or _BRIGHTNESS.fullmatch(brightness) is None:
        raise ValueError("meanBrightness must be a canonical non-negative decimal")
    provisional = payload["provisional"]
    if type(provisional) is not bool:
        raise ValueError("provisional must be a bool")
    return patch_id, region, repeat, brightness, provisional


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} is not an allowed value")
    return value


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a token")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P042-01 must not yield qualified or allowed")
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
