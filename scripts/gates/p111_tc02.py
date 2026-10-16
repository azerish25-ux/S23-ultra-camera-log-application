"""TC-P111-02 Disoccluded background.

Host fixture. Newly visible pixels filled with old depth are rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P111-02"
NAME = "Disoccluded background"
INTERVENTION = "Reveal new background behind a moving foreground object where historical depth is invalid."
EXPECTED = "Use current evidence and uncertainty rather than smearing previous foreground values into the new region."
NEGATIVE = "Filling all newly visible pixels with old depth must fail."
REPEAT = "Repeat thin objects, hands, hair, and large foreground occluders."
NEGATIVE_TOKEN = "old-depth-fill-on-disocclusion"
PAYLOAD_KEYS = ("evidenceId", "repeat", "revealed")
PIXEL_KEYS = {"id", "fill"}
FILLS = {"old_depth", "current_evidence", "uncertain"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    revealed = payload["revealed"]
    if not isinstance(revealed, list) or not revealed:
        raise ValueError("revealed must be a non-empty list")
    seen = set()
    old = 0
    current = 0
    uncertain = 0
    for index, item in enumerate(revealed):
        if not isinstance(item, dict) or set(item) != PIXEL_KEYS:
            raise ValueError(f"revealed {index} keys are invalid")
        pixel_id = _text(item["id"], f"revealed {index} id")
        if pixel_id in seen:
            raise ValueError("revealed ids must be unique")
        seen.add(pixel_id)
        fill = item["fill"]
        if fill not in FILLS:
            raise ValueError(f"revealed {index} fill is invalid")
        if fill == "old_depth":
            old += 1
        elif fill == "current_evidence":
            current += 1
        else:
            uncertain += 1
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"revealed={len(revealed)} old_depth={old} current_evidence={current} uncertain={uncertain}",
    ]
    rejected: list[str] = []
    if old:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("previous foreground depth was smeared into newly visible pixels")
    else:
        decision = "recorded"
        reasons.append("disocclusion used current evidence or uncertainty")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"old_depth:{old}", f"current_evidence:{current}", f"uncertain:{uncertain}"],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
