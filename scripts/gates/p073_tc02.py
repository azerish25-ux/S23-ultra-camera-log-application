"""TC-P073-02 exposure-domain confusion.

Intervention: Move exposure adjustment after the negative response while presenting
it as incident exposure.
Expected: Fail the declared graph contract and expose differing shadow, highlight,
and texture behavior.
Negative: One post-LUT contrast control cannot stand in for every physical stage.
"""

from __future__ import annotations


CASE_ID = "TC-P073-02"
INTERVENTION = "Move exposure adjustment after the negative response while presenting it as incident exposure."
EXPECTED = "Fail the declared graph contract and expose differing shadow, highlight, and texture behavior."
NEGATIVE = "One post-LUT contrast control cannot stand in for every physical stage."
REPEAT = "Repeat with exposure, development, printing, and final display grading controls."

_CONTROLS = ("exposure", "development", "printing", "display-grade")
_STAGES = ("incident-exposure", "post-negative", "development", "printing", "display-grade")
_PAYLOAD_KEYS = ("control", "stageDeclared", "stageApplied", "presentsAsIncident", "postLutContrastOnly")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "stage_aligned"}


def evaluate(payload: dict) -> dict:
    """Fail a graph that presents a later control as incident exposure."""
    control, declared, applied, presents, post_lut = _payload(payload)
    preserved = [
        f"control:{control}",
        f"declared:{declared}",
        f"applied:{applied}",
        "shadow",
        "highlight",
        "texture",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {control}"]
    rejected: list[str] = []
    false_incident = presents and applied != "incident-exposure"
    if declared != applied or false_incident:
        rejected.append("graph-contract")
        reasons.append("shadow, highlight, and texture behavior differ from the declared stage")
        reasons.append(f"{control} was applied at {applied} while declared as {declared}")
    if post_lut:
        rejected.append("post-lut-contrast")
        reasons.append(NEGATIVE)
        reasons.append(f"post-LUT contrast on {control} does not replace incident exposure, development, printing, and display grade")
    if rejected:
        decision = "rejected"
    else:
        decision = "stage_aligned"
        reasons.append(f"{control} stays at the declared stage {declared}")
        questions.append("stage alignment is not a qualified physical exposure measurement")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    control = payload["control"]
    if control not in _CONTROLS:
        raise ValueError("control is unsupported")
    declared = payload["stageDeclared"]
    applied = payload["stageApplied"]
    if declared not in _STAGES or applied not in _STAGES:
        raise ValueError("stage is unsupported")
    presents = payload["presentsAsIncident"]
    post_lut = payload["postLutContrastOnly"]
    for name, value in (("presentsAsIncident", presents), ("postLutContrastOnly", post_lut)):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
    return control, declared, applied, presents, post_lut


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P073-02 must not yield qualified or allowed")
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
