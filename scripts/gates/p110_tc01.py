"""TC-P110-01 History without reprojection.

Host fixture. Unaligned history is a computed depth trail, not a boolean stamp.
"""

from __future__ import annotations

CASE_ID = "TC-P110-01"
NAME = "History without reprojection"
INTERVENTION = "Move a known object while previous depth remains in its original pixel coordinates."
EXPECTED = "Reject unaligned history or warp it correctly before temporal blending."
NEGATIVE = "A stationary-pixel average that leaves depth trails must fail."
REPEAT = "Repeat translation, rotation, scale change, and camera motion."
NEGATIVE_TOKEN = "stationary-pixel-average-depth-trails"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = ("evidenceId", "repeat", "previous", "current", "shift", "blend")
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


def _depths(values, name: str) -> list[float]:
    _require(isinstance(values, list) and len(values) >= 1, name + " must be a non-empty list")
    numbers: list[float] = []
    for index, item in enumerate(values):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"{name}[{index}] must be a number")
        number = float(item)
        _require(number == number and abs(number) != float("inf"), f"{name}[{index}] must be finite")
        numbers.append(number)
    return numbers


def blend_history(previous: list[float], current: list[float], shift: int, blend: str) -> list[float]:
    """Average current depth with history, either in place or after a pixel warp."""
    output: list[float] = []
    count = len(current)
    for index, value in enumerate(current):
        if blend == "reprojected":
            source = index - shift
        elif blend == "stationary":
            source = index
        else:
            raise ValueError("blend must be stationary or reprojected")
        if 0 <= source < count:
            output.append(0.5 * (previous[source] + value))
        else:
            output.append(value)
    return output


def leaves_depth_trail(previous: list[float], current: list[float], output: list[float], shift: int) -> bool:
    """True when a moved object's previous depth still contaminates the vacated pixel."""
    if shift == 0:
        return False
    count = len(current)
    for origin in range(count):
        dest = origin + shift
        if not 0 <= dest < count:
            continue
        moved = previous[origin] == current[dest] and previous[origin] != current[origin]
        if moved and output[origin] != current[origin]:
            return True
    return False


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    _require(type(payload["shift"]) is int, "shift must be an int")
    previous = _depths(payload["previous"], "previous")
    current = _depths(payload["current"], "current")
    _require(len(previous) == len(current), "previous and current lengths must match")
    blend = payload["blend"]
    _require(blend in {"stationary", "reprojected"}, "blend must be stationary or reprojected")
    output = blend_history(previous, current, payload["shift"], blend)
    trail = leaves_depth_trail(previous, current, output, payload["shift"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if trail:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("stationary history left a depth trail at the vacated coordinate")
    else:
        decision = "recorded"
        reasons.append("history was aligned before blending; no depth trail remains")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
