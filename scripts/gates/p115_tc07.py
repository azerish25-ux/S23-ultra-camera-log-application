"""TC-P115-07 Guidance overrides user intent.

Host fixture. Capture advice may warn. It must not silently change shutter,
disable clipping warnings, or hide a camera-setting change.
"""

from __future__ import annotations


CASE_ID = "TC-P115-07"
NAME = "Guidance overrides user intent"
INTERVENTION = "Enable capture advice while the user has explicitly chosen manual exposure and focus."
EXPECTED = "Provide warnings or suggestions without hidden camera-setting changes."
NEGATIVE = "A cinematic preset that silently disables clipping warnings or changes shutter must fail."
REPEAT = "Repeat thermal advice, focus warnings, and incompatible virtual-lens framing."
REPEATS = ("thermal-advice", "focus-warning", "incompatible-virtual-lens")
PAYLOAD_KEYS = (
    "evidenceId",
    "adviceEnabled",
    "manualExposure",
    "manualFocus",
    "shutterChanged",
    "clippingWarningsDisabled",
    "hiddenChange",
    "repeat",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Record suggestion-only advice. Silent shutter or warning changes are rejected."""
    fields = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    if fields["shutterChanged"]:
        rejected.append("silent-shutter-change")
    if fields["clippingWarningsDisabled"]:
        rejected.append("silent-clipping-warning-disable")
    if fields["shutterChanged"] or fields["clippingWarningsDisabled"]:
        reasons.append(NEGATIVE)
    if fields["hiddenChange"]:
        rejected.append("hidden-camera-setting-change")
        reasons.append("hidden camera-setting change was not applied")
    manual = fields["manualExposure"] or fields["manualFocus"]
    if manual and (fields["shutterChanged"] or fields["clippingWarningsDisabled"] or fields["hiddenChange"]):
        rejected.append("guidance-overrides-manual-intent")
        reasons.append("manual exposure and focus were left unchanged")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("advice stayed a suggestion")
    preserved = [
        fields["evidenceId"],
        {
            "adviceEnabled": fields["adviceEnabled"],
            "manualExposure": fields["manualExposure"],
            "manualFocus": fields["manualFocus"],
            "shutterChanged": fields["shutterChanged"],
            "clippingWarningsDisabled": fields["clippingWarningsDisabled"],
            "hiddenChange": fields["hiddenChange"],
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    flags = {}
    for key in PAYLOAD_KEYS:
        if key in {"evidenceId", "repeat"}:
            continue
        if type(payload[key]) is not bool:
            raise ValueError(f"{key} must be a bool")
        flags[key] = payload[key]
    flags["evidenceId"] = evidence
    flags["repeat"] = repeat
    return flags


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS or not reasons or preserved[0] not in preserved:
        raise ValueError("result contract drifted")
    return result
