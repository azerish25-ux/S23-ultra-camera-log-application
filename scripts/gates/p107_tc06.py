"""TC-P107-06 Subject identity crossing.

Host reference. Focus follows the documented identity, not the nearest face.
"""

from __future__ import annotations

CASE_ID = "TC-P107-06"
NAME = "Subject identity crossing"
INTERVENTION = "Let two similar subjects cross while one remains the user-selected focus target."
EXPECTED = "Follow the documented identity and target-loss policy without unexplained focus jumps."
NEGATIVE = "Choosing the nearest face independently in every frame must fail."
REPEAT = "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking."
NEGATIVE_TOKEN = "nearest-face-per-frame"
FRAME_KEYS = {"frame_id", "selected_id", "nearest_face_id", "target_visible", "policy"}
POLICIES = {"documented-identity", "nearest-face", "target-loss-hold", "target-loss-reset"}
PAYLOAD_KEYS = ("evidenceId", "repeat", "target_id", "frames")
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


def _token(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _token(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    target = _token(payload["target_id"], "target_id")
    frames = payload["frames"]
    _require(isinstance(frames, list) and frames, "frames must be a non-empty list")
    jumps = 0
    nearest = 0
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    previous: str | None = None
    for index, frame in enumerate(frames):
        _require(isinstance(frame, dict) and set(frame) == FRAME_KEYS, f"frames[{index}] has invalid keys")
        _token(frame["frame_id"], f"frames[{index}].frame_id")
        selected = _token(frame["selected_id"], f"frames[{index}].selected_id")
        _token(frame["nearest_face_id"], f"frames[{index}].nearest_face_id")
        _require(type(frame["target_visible"]) is bool, "target_visible must be a bool")
        policy = frame["policy"]
        _require(policy in POLICIES, "policy is unsupported")
        if policy == "nearest-face":
            nearest += 1
        visible = frame["target_visible"]
        if visible and selected != target:
            jumps += 1
            rejected.append("unexplained-focus-jump")
        if not visible and policy == "target-loss-hold" and selected != target:
            jumps += 1
            rejected.append("target-loss-policy")
        if not visible and policy == "target-loss-reset" and selected != "none":
            rejected.append("target-loss-policy")
        if not visible and policy == "documented-identity":
            rejected.append("target-loss-policy")
        if previous is not None and selected != previous and visible and selected != target:
            jumps += 1
        previous = selected
    if nearest:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    reasons.append(f"nearest_face_frames={nearest}")
    reasons.append(f"focus_jumps={jumps}")
    if not rejected:
        reasons.append("documented identity retained")
    # de-duplicate while keeping order
    deduped: list[str] = []
    for item in rejected:
        if item not in deduped:
            deduped.append(item)
    decision = "rejected" if deduped else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": deduped,
        "preservedResults": [evidence, f"focus_jumps={jumps}"],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
