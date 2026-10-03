"""TC-P032-04 codec output contradicts request.

Intervention: Emit an actual stream with different depth, dimensions, transfer
tags, or selected tracks than requested.
Expected: Fail the corresponding output contract while retaining useful media
under an accurate status.
Negative: Trusting only configure parameters must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P032-04"
INTERVENTION = (
    "Emit an actual stream with different depth, dimensions, transfer tags, or selected "
    "tracks than requested."
)
EXPECTED = (
    "Fail the corresponding output contract while retaining useful media under an accurate status."
)
NEGATIVE = "Trusting only configure parameters must fail."

_DEPTHS = (8, 10)
_RANGES = ("full", "limited", "unspecified")
_TRACKS = ("video", "audio")
_PAYLOAD_KEYS = (
    "requestedDepth",
    "actualDepth",
    "requestedWidth",
    "requestedHeight",
    "actualWidth",
    "actualHeight",
    "requestedTransfer",
    "actualTransfer",
    "requestedColorRange",
    "actualColorRange",
    "requestedTracks",
    "actualTracks",
    "configureSucceeded",
    "trustConfigureOnly",
    "retainedMedia",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "contract_failed", "output_observed")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Compare emitted output with the request. Configure success is not enough."""
    fields = _payload(payload)
    mismatches: list[str] = []
    if fields["requestedDepth"] != fields["actualDepth"]:
        mismatches.append("depth")
    if (fields["requestedWidth"], fields["requestedHeight"]) != (
        fields["actualWidth"],
        fields["actualHeight"],
    ):
        mismatches.append("dimensions")
    if fields["requestedTransfer"] != fields["actualTransfer"]:
        mismatches.append("transfer")
    if fields["requestedColorRange"] != fields["actualColorRange"]:
        mismatches.append("color-range")
    if fields["requestedTracks"] != fields["actualTracks"]:
        mismatches.append("tracks")

    if fields["trustConfigureOnly"]:
        decision = "rejected"
        rejected = ["configure-only-trust", *mismatches]
    elif mismatches:
        decision = "contract_failed"
        rejected = mismatches
    else:
        decision = "output_observed"
        rejected = []

    preserved = list(fields["retainedMedia"])
    preserved.append(_side("requested", fields, "requested"))
    preserved.append(_side("actual", fields, "actual"))

    reasons = [EXPECTED]
    if fields["trustConfigureOnly"]:
        reasons.append(NEGATIVE)
        reasons.append(
            "configureSucceeded was "
            + ("true" if fields["configureSucceeded"] else "false")
            + " and is not the emitted contract"
        )
    if "depth" in mismatches and fields["requestedDepth"] == 10 and fields["actualDepth"] == 8:
        reasons.append("eight-bit output does not satisfy a ten-bit request")
    if "color-range" in mismatches:
        reasons.append("color-range metadata contradicts the request")
    if fields["retainedMedia"]:
        reasons.append("useful media is retained under an accurate status")
    else:
        reasons.append("no useful media was claimed as success")
    if decision == "output_observed":
        reasons.append("output observation is not ten-bit fidelity or cinema-camera equivalence")

    questions: list[str] = []
    if not fields["retainedMedia"]:
        questions.append("no useful media retained")
    if decision == "output_observed":
        questions.append("output observation is not ten-bit fidelity or cinema-camera equivalence")
    return _result(decision, reasons, rejected, preserved, questions)


def _side(name: str, fields: dict, prefix: str) -> str:
    tracks = "+".join(fields[prefix + "Tracks"]) if fields[prefix + "Tracks"] else "none"
    return (
        f"{name}:depth={fields[prefix + 'Depth']}:"
        f"{fields[prefix + 'Width']}x{fields[prefix + 'Height']}:"
        f"{fields[prefix + 'Transfer']}:{fields[prefix + 'ColorRange']}:{tracks}"
    )


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    parsed = {
        "requestedDepth": _depth(payload["requestedDepth"], "requestedDepth"),
        "actualDepth": _depth(payload["actualDepth"], "actualDepth"),
        "requestedWidth": _positive(payload["requestedWidth"], "requestedWidth"),
        "requestedHeight": _positive(payload["requestedHeight"], "requestedHeight"),
        "actualWidth": _positive(payload["actualWidth"], "actualWidth"),
        "actualHeight": _positive(payload["actualHeight"], "actualHeight"),
        "requestedTransfer": _text(payload["requestedTransfer"], "requestedTransfer"),
        "actualTransfer": _text(payload["actualTransfer"], "actualTransfer"),
        "requestedColorRange": _choice(payload["requestedColorRange"], "requestedColorRange"),
        "actualColorRange": _choice(payload["actualColorRange"], "actualColorRange"),
        "requestedTracks": _tracks(payload["requestedTracks"], "requestedTracks", allow_empty=False),
        "actualTracks": _tracks(payload["actualTracks"], "actualTracks", allow_empty=True),
        "configureSucceeded": _bool(payload["configureSucceeded"], "configureSucceeded"),
        "trustConfigureOnly": _bool(payload["trustConfigureOnly"], "trustConfigureOnly"),
        "retainedMedia": _media(payload["retainedMedia"]),
    }
    return parsed


def _depth(value: object, label: str) -> int:
    if type(value) is not int or value not in _DEPTHS:
        raise ValueError(f"{label} must be 8 or 10")
    return value


def _positive(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive int")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _choice(value: object, label: str) -> str:
    if not isinstance(value, str) or value not in _RANGES:
        raise ValueError(f"{label} must be full, limited, or unspecified")
    return value


def _tracks(value: object, label: str, allow_empty: bool) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    if not allow_empty and not value:
        raise ValueError(f"{label} must name at least one track")
    if len(value) != len(set(value)) or any(item not in _TRACKS for item in value):
        raise ValueError(f"{label} must be unique video/audio names")
    return list(value)


def _media(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) != len(set(value)):
        raise ValueError("retainedMedia must be a list of unique strings")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError("retainedMedia must be a list of unique strings")
    return list(value)


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("output decision cannot be qualified or allowed")
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
