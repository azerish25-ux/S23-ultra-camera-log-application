"""TC-P026-03 gap concealed by average rate.

A long interval plus compensating short intervals can keep the average near
the target. The source cadence defect is still reported and the original
timestamps are kept. A mean-only validator fails this fixture.
"""

from __future__ import annotations

CASE_ID = "TC-P026-03"
INTERVENTION = (
    "Insert a long interval and compensating short intervals so average frame rate remains near target."
)
EXPECTED = "Report the source cadence defect and preserve the original timing evidence."
NEGATIVE = "A mean-only validator must be killed by this fixture."
DEFECTS = (
    "compensated_gap",
    "duplicate_timestamps",
    "repeated_image_content",
    "missing_source_frame",
)
_PAYLOAD_KEYS = (
    "defect",
    "targetFps",
    "averageFps",
    "meanOnly",
    "timestamps",
    "sourceId",
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
    """Report the cadence defect. Do not clear it with an average rate."""
    fields = _payload(payload)
    reasons = [
        INTERVENTION,
        f"defect {fields['defect']}",
        f"target {fields['targetFps']} average {fields['averageFps']}",
    ]
    preserved = [f"t:{stamp}" for stamp in fields["timestamps"]] + [fields["sourceId"]]
    if fields["meanOnly"]:
        reasons.append(NEGATIVE)
        reasons.append("average rate near target does not clear the source gap")
        return _result(
            "rejected",
            reasons,
            ["mean-only-validator", fields["defect"]],
            preserved,
            [],
        )
    reasons.append(EXPECTED)
    reasons.append("original timestamps were preserved")
    return _result("cadence_defect", reasons, [fields["defect"]], preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    defect = payload["defect"]
    if defect not in DEFECTS:
        raise ValueError("defect is not a declared repeat")
    timestamps = payload["timestamps"]
    if not isinstance(timestamps, list) or len(timestamps) < 2:
        raise ValueError("timestamps must contain at least two stamps")
    stamps = [_stamp(item) for item in timestamps]
    return {
        "defect": defect,
        "targetFps": _fps(payload["targetFps"], "targetFps"),
        "averageFps": _fps(payload["averageFps"], "averageFps"),
        "meanOnly": _bool(payload["meanOnly"], "meanOnly"),
        "timestamps": stamps,
        "sourceId": _token(payload["sourceId"], "sourceId"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _fps(value: object, name: str) -> str:
    text = _token(value, name)
    whole, dot, frac = text.partition(".")
    if dot == "" and whole.isdigit() and whole[0] != "0":
        return text
    if (
        dot == "."
        and whole.isdigit()
        and whole[0] != "0"
        and frac.isdigit()
        and frac[-1] != "0"
    ):
        return text
    raise ValueError(f"{name} must be a canonical positive fps string")


def _stamp(value: object) -> str:
    if not isinstance(value, str) or not value or not value.isdigit():
        raise ValueError("timestamp must be a canonical non-negative integer string")
    if value != "0" and value[0] == "0":
        raise ValueError("timestamp must be a canonical non-negative integer string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P026-03 must not yield qualified or allowed")
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
