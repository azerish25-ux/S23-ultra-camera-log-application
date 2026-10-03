"""TC-P053-06 defect versus real highlight.

Intervention: Place a persistent sensor defect beside a real small moving
bright feature.
Expected: Correct only the supported defect and preserve the real scene feature
under the declared policy.
Negative: Removing every isolated bright pixel must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P053-06"
INTERVENTION = "Place a persistent sensor defect beside a real small moving bright feature."
EXPECTED = (
    "Correct only the supported defect and preserve the real scene feature under the declared policy."
)
NEGATIVE = "Removing every isolated bright pixel must fail."

_POLICIES = ("measured-map", "intensity-threshold")
_FRAME_KEYS = ("id", "defectValue", "highlightX", "highlightY", "highlightValue")
_PAYLOAD_KEYS = (
    "policy",
    "frames",
    "defectX",
    "defectY",
    "supported",
    "persistent",
    "nearSaturated",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "defect_corrected")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Correct a supported persistent defect. Do not erase the moving highlight."""
    policy, frames, defect_x, defect_y, supported, persistent, near_saturated = _payload(payload)
    preserved = [f"defect:{defect_x},{defect_y}", f"policy:{policy}"]
    if near_saturated:
        preserved.append("saturated-boundary")
    for frame in frames:
        preserved.append(f"frame:{frame['id']}:defect={frame['defectValue']}")
        preserved.append(
            f"frame:{frame['id']}:highlight="
            f"{frame['highlightX']},{frame['highlightY']}:{frame['highlightValue']}"
        )
    reasons = [EXPECTED, INTERVENTION]
    positions = {(frame["highlightX"], frame["highlightY"]) for frame in frames}
    if policy == "intensity-threshold":
        return _result(
            "rejected",
            reasons + [NEGATIVE],
            ["remove-every-isolated-bright-pixel"]
            + [
                f"highlight:{frame['id']}:{frame['highlightX']},{frame['highlightY']}"
                for frame in frames
            ],
            preserved,
            ["threshold removal erases the moving feature"],
        )
    if len(positions) < 2:
        return _result(
            "withheld",
            reasons + ["highlight did not move across frames"],
            ["highlight-not-moving"],
            preserved,
            ["a stationary bright pixel is not identified as the moving feature"],
        )
    if not supported or not persistent:
        claims: list[str] = []
        if not supported:
            claims.append("unsupported-defect")
        if not persistent:
            claims.append("not-persistent")
        return _result(
            "withheld",
            reasons + ["defect was not corrected"],
            claims,
            preserved,
            list(claims),
        )
    reasons.append("supported defect corrected; moving highlight preserved")
    return _result(
        "defect_corrected",
        reasons,
        [],
        preserved,
        ["correction is not physical S23 qualification"],
    )


def _payload(payload: object) -> tuple[str, list[dict], int, int, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    policy = payload["policy"]
    if policy not in _POLICIES:
        raise ValueError("policy is unknown")
    frames = payload["frames"]
    if not isinstance(frames, list) or len(frames) < 2:
        raise ValueError("frames must contain at least two frames")
    parsed: list[dict] = []
    seen: set[str] = set()
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict) or set(frame) != set(_FRAME_KEYS):
            raise ValueError(f"frame {index} keys are invalid")
        ident = frame["id"]
        if not isinstance(ident, str) or _TOKEN.fullmatch(ident) is None or ident in seen:
            raise ValueError(f"frame {index} id must be a unique token")
        seen.add(ident)
        numbers = (
            frame["defectValue"],
            frame["highlightX"],
            frame["highlightY"],
            frame["highlightValue"],
        )
        if any(type(item) is not int or item < 0 for item in numbers):
            raise ValueError(f"frame {index} coordinates and values must be non-negative ints")
        parsed.append({
            "id": ident,
            "defectValue": numbers[0],
            "highlightX": numbers[1],
            "highlightY": numbers[2],
            "highlightValue": numbers[3],
        })
    defect_x = payload["defectX"]
    defect_y = payload["defectY"]
    if type(defect_x) is not int or type(defect_y) is not int or defect_x < 0 or defect_y < 0:
        raise ValueError("defect coordinates must be non-negative ints")
    flags = (payload["supported"], payload["persistent"], payload["nearSaturated"])
    if any(type(item) is not bool for item in flags):
        raise ValueError("support flags must be bools")
    return policy, parsed, defect_x, defect_y, flags[0], flags[1], flags[2]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("highlight decision cannot be qualified or allowed")
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
