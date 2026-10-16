"""TC-P109-02 Disoccluded background.

Host fixture. Newly visible pixels filled from invalid history are rejected.
A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P109-02"
NAME = "Disoccluded background"
INTERVENTION = "Reveal new background behind a moving foreground object where historical depth is invalid."
EXPECTED = "Use current evidence and uncertainty rather than smearing previous foreground values into the new region."
NEGATIVE = "Filling all newly visible pixels with old depth must fail."
REPEAT = "Repeat thin objects, hands, hair, and large foreground occluders."
NEGATIVE_TOKEN = "disoccluded-filled-with-old-depth"
PAYLOAD_KEYS = ("evidenceId", "repeat", "pixels")
PIXEL_KEYS = {"historicalValid", "historicalDepth", "currentDepth", "source"}
SOURCES = {"current", "uncertain", "history"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _depth(value: object, message: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), message)
    number = float(value)
    _require(number == number and number not in (float("inf"), float("-inf")), message)
    return number


def _finish(evidence: str, repeat: str, decision: str, rejected: list[str], detail: str) -> dict:
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(decision not in {"qualified", "allowed"}, "negative or unmeasured result must not be qualified")
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, detail]
    if decision == "rejected":
        reasons.append(NEGATIVE)
    else:
        reasons.append("narrower software result retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    pixels = payload["pixels"]
    _require(isinstance(pixels, list) and len(pixels) >= 1, "pixels must be a non-empty list")
    leaked: list[str] = []
    disoccluded = 0
    for index, pixel in enumerate(pixels):
        _require(isinstance(pixel, dict) and set(pixel) == PIXEL_KEYS, f"pixel {index} keys")
        _require(type(pixel["historicalValid"]) is bool, f"pixel {index} historicalValid")
        historical = _depth(pixel["historicalDepth"], f"pixel {index} historicalDepth")
        _depth(pixel["currentDepth"], f"pixel {index} currentDepth")
        _require(pixel["source"] in SOURCES, f"pixel {index} source")
        if pixel["historicalValid"] is False:
            disoccluded += 1
            if pixel["source"] == "history":
                leaked.append(f"{index}:{historical:.6f}")
    if leaked:
        detail = "newly visible pixels filled with old depth " + ",".join(leaked)
        return _finish(evidence, repeat, "rejected", [NEGATIVE_TOKEN], detail)
    detail = f"disoccluded pixels {disoccluded} use current evidence or uncertainty"
    return _finish(evidence, repeat, "recorded", [], detail)
