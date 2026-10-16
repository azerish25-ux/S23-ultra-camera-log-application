"""TC-P123-02 Mutable recipe during export.

Host fixture. A running development job stays bound to the recipe frozen when
the render began. Later slider edits create a new version. Reading live slider
values for successive output frames is rejected.
"""

from __future__ import annotations


CASE_ID = "TC-P123-02"
NAME = "Mutable recipe during export"
INTERVENTION = "Change UI parameters after a render has begun but before it finishes."
EXPECTED = "Keep the running job bound to its frozen recipe and create a new version for subsequent edits."
NEGATIVE = "Reading live slider values for successive output frames must fail."
REPEAT = "Repeat stock, focus, grain seed, output range, and source interpretation changes."
LEGAL_STATES = frozenset({"idle", "queued", "running", "checkpointed", "failed", "cancelled", "completed"})
RECIPE_KEYS = ("stock", "focus", "grainSeed", "outputRange", "sourceInterpretation")
REPEATS = {
    "stock": "stock",
    "focus": "focus",
    "grain-seed": "grainSeed",
    "output-range": "outputRange",
    "source-interpretation": "sourceInterpretation",
}
PAYLOAD_KEYS = (
    "evidenceId",
    "jobState",
    "frozenRecipe",
    "liveSliders",
    "frameSources",
    "runningVersion",
    "editVersion",
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
    """Reject live-slider frame reads and edits that mutate the running version."""
    fields = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    if fields["jobState"] != "running":
        rejected.append("job-not-running")
        reasons.append("frames are bound only while the job is running")
    live_frames = [index for index, source in enumerate(fields["frameSources"]) if source == "live"]
    if live_frames:
        rejected.append("live-slider-read-for-output-frame")
        reasons.append(NEGATIVE)
        reasons.append("live slider frames at " + ",".join(str(index) for index in live_frames))
    changed = [key for key in RECIPE_KEYS if fields["frozenRecipe"][key] != fields["liveSliders"][key]]
    if changed and fields["editVersion"] != fields["runningVersion"] + 1:
        rejected.append("running-job-not-versioned")
        reasons.append("subsequent edits must create a new version and leave the frozen recipe bound")
    if not changed and fields["editVersion"] != fields["runningVersion"]:
        rejected.append("version-changed-without-edit")
        reasons.append("the running version changed although the recipe did not")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("running job stayed bound to the frozen recipe")
    preserved = [
        fields["evidenceId"],
        {"frozenRecipe": dict(fields["frozenRecipe"]), "liveSliders": dict(fields["liveSliders"])},
        list(fields["frameSources"]),
        {"runningVersion": fields["runningVersion"], "editVersion": fields["editVersion"]},
    ]
    return _result(decision, reasons, rejected, preserved, ["physical S23 capture was not run", REPEAT])


def _recipe(value: object, label: str) -> dict:
    if not isinstance(value, dict) or set(value) != set(RECIPE_KEYS):
        raise ValueError(f"{label} keys are invalid")
    recipe = {}
    for key in RECIPE_KEYS:
        item = value[key]
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{label}.{key} must be a non-empty string")
        recipe[key] = item
    return recipe


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    state = payload["jobState"]
    if not isinstance(state, str) or state not in LEGAL_STATES:
        shown = state if isinstance(state, str) else type(state).__name__
        raise ValueError(f"unknown state name: {shown}")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    frozen = _recipe(payload["frozenRecipe"], "frozenRecipe")
    live = _recipe(payload["liveSliders"], "liveSliders")
    field = REPEATS[repeat]
    if frozen[field] == live[field]:
        raise ValueError("repeat field did not change")
    others = [key for key in RECIPE_KEYS if key != field and frozen[key] != live[key]]
    if others:
        raise ValueError("only the repeated recipe field may change")
    frames = payload["frameSources"]
    if not isinstance(frames, list) or not frames:
        raise ValueError("frameSources must be a non-empty list")
    if any(item not in {"frozen", "live"} for item in frames):
        raise ValueError("frame source must be frozen or live")
    running = payload["runningVersion"]
    edit = payload["editVersion"]
    if type(running) is not int or type(edit) is not int or running < 1 or edit < 1:
        raise ValueError("versions must be positive integers")
    return {
        "evidenceId": evidence,
        "jobState": state,
        "frozenRecipe": frozen,
        "liveSliders": live,
        "frameSources": list(frames),
        "runningVersion": running,
        "editVersion": edit,
        "repeat": repeat,
    }


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
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
