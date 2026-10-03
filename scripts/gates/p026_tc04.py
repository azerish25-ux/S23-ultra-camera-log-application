"""TC-P026-04 codec output contradicts the request.

The emitted stream may differ in depth, dimensions, transfer, or tracks.
The output contract fails and the media stays under an accurate status.
Trusting only the configure parameters must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P026-04"
INTERVENTION = (
    "Emit an actual stream with different depth, dimensions, transfer tags, or selected tracks than requested."
)
EXPECTED = "Fail the corresponding output contract while retaining useful media under an accurate status."
NEGATIVE = "Trusting only configure parameters must fail."
CONTRADICTIONS = (
    "eight_bit_after_ten_bit",
    "wrong_color_range",
    "wrong_dimensions",
    "wrong_transfer_tag",
    "wrong_selected_tracks",
)
INACCURATE = {"qualified", "allowed", "acceptable-log"}
_PAYLOAD_KEYS = (
    "contradiction",
    "configureOnly",
    "mediaId",
    "requested",
    "emitted",
    "status",
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
    """Fail the output contract. Do not trust configure parameters alone."""
    fields = _payload(payload)
    reasons = [INTERVENTION, f"contradiction {fields['contradiction']}", f"status {fields['status']}"]
    preserved = [fields["mediaId"], fields["requested"], fields["emitted"], fields["status"]]
    rejected: list[str] = []
    if fields["configureOnly"]:
        rejected.append("configure-parameters-only")
        reasons.append(NEGATIVE)
    if fields["status"] in INACCURATE:
        rejected.append("inaccurate-status")
        reasons.append("status must not relabel the contradiction as qualified, allowed, or Log")
    if rejected:
        rejected.append(fields["contradiction"])
        decision = "rejected"
    else:
        rejected.append(fields["contradiction"])
        decision = "output_contract_failed"
        reasons.append(EXPECTED)
        reasons.append("useful media retained under an accurate status")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    contradiction = payload["contradiction"]
    if contradiction not in CONTRADICTIONS:
        raise ValueError("contradiction is not a declared repeat")
    status = _token(payload["status"], "status")
    return {
        "contradiction": contradiction,
        "configureOnly": _bool(payload["configureOnly"], "configureOnly"),
        "mediaId": _token(payload["mediaId"], "mediaId"),
        "requested": _token(payload["requested"], "requested"),
        "emitted": _token(payload["emitted"], "emitted"),
        "status": status,
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P026-04 must not yield qualified or allowed")
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
