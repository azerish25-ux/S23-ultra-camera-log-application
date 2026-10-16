"""TC-P125-02 Mutable recipe during export.

Host fixture. Output frames stay on the frozen recipe. A live slider change
opens a new version and is not read into the running job.
"""

from __future__ import annotations


CASE_ID = "TC-P125-02"
NAME = "Mutable recipe during export"
INTERVENTION = "Change UI parameters after a render has begun but before it finishes."
EXPECTED = "Keep the running job bound to its frozen recipe and create a new version for subsequent edits."
NEGATIVE = "Reading live slider values for successive output frames must fail."
REPEAT = "Repeat stock, focus, grain seed, output range, and source interpretation changes."
LIVE_TOKEN = "live-slider-values-for-successive-frames"
VERSION_TOKEN = "edit-without-new-version"
REPEATS = ("stock", "focus", "grain-seed", "output-range", "source-interpretation")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frozenRecipe",
    "liveSliders",
    "frameValues",
    "newVersionCreated",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _scalar(value: object, label: str):
    if type(value) is bool or not isinstance(value, (str, int, float)):
        raise ValueError(f"{label} must be a string or number")
    if isinstance(value, float) and value != value:
        raise ValueError(f"{label} must be finite")
    if isinstance(value, str) and (not value.strip() or value != value.strip()):
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _recipe(value: object, label: str, keys: tuple[str, ...] | None) -> dict:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{label} must be a non-empty object")
    if keys is not None and set(value) != set(keys):
        raise ValueError(f"{label} keys must match the frozen recipe")
    parsed = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            raise ValueError("recipe key must be a non-empty string")
        parsed[key] = _scalar(item, f"{label}.{key}")
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    if type(payload["newVersionCreated"]) is not bool:
        raise ValueError("newVersionCreated must be a bool")
    frozen = _recipe(payload["frozenRecipe"], "frozenRecipe", None)
    if repeat not in frozen:
        raise ValueError("frozen recipe must contain the repeated field")
    keys = tuple(frozen)
    live = _recipe(payload["liveSliders"], "liveSliders", keys)
    frames = payload["frameValues"]
    if not isinstance(frames, list) or not frames:
        raise ValueError("frameValues must be a non-empty list")
    parsed_frames = [_recipe(frame, f"frameValues[{index}]", keys) for index, frame in enumerate(frames)]
    drifted = [index for index, frame in enumerate(parsed_frames) if frame != frozen]
    live_differs = live != frozen
    rejected: list[str] = []
    if drifted:
        rejected.append(LIVE_TOKEN)
    if live_differs and not payload["newVersionCreated"]:
        rejected.append(VERSION_TOKEN)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    if LIVE_TOKEN in rejected:
        reasons.append(NEGATIVE)
    if VERSION_TOKEN in rejected:
        reasons.append("a slider change after start must create a new version")
    if not rejected:
        reasons.append("running frames stayed on the frozen recipe")
        if live_differs:
            reasons.append("subsequent edit stored as a new version")
    preserved = [
        evidence,
        {
            "frozenRecipe": frozen,
            "liveSliders": live,
            "frameCount": len(parsed_frames),
            "driftedFrames": drifted,
            "newVersionCreated": payload["newVersionCreated"],
        },
    ]
    return _result("rejected" if rejected else "recorded", reasons, rejected, preserved)


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
