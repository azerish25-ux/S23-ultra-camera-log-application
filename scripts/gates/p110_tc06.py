"""TC-P110-06 Subject identity crossing.

Host fixture. The selected identity is held. Nearest-face each frame is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P110-06"
NAME = "Subject identity crossing"
INTERVENTION = "Let two similar subjects cross while one remains the user-selected focus target."
EXPECTED = "Follow the documented identity and target-loss policy without unexplained focus jumps."
NEGATIVE = "Choosing the nearest face independently in every frame must fail."
REPEAT = "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking."
NEGATIVE_TOKEN = "nearest-face-independently-each-frame"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = ("evidenceId", "repeat", "frames", "targetId", "policy")
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


def _frames(frames) -> list[dict]:
    _require(isinstance(frames, list) and len(frames) >= 1, "frames must be a non-empty list")
    parsed: list[dict] = []
    for index, frame in enumerate(frames):
        _require(isinstance(frame, dict) and set(frame) == {"candidates"}, f"frames[{index}] must contain candidates")
        candidates = frame["candidates"]
        _require(isinstance(candidates, list) and len(candidates) >= 1, f"frames[{index}] needs a candidate")
        seen: set[str] = set()
        clean = []
        for candidate_index, candidate in enumerate(candidates):
            _require(isinstance(candidate, dict) and set(candidate) == {"id", "distance"},
                     f"frames[{index}].candidates[{candidate_index}] keys drifted")
            identity = candidate["id"]
            _require(isinstance(identity, str) and identity.strip(), "candidate id must be a non-empty string")
            _require(identity not in seen, "duplicate candidate id")
            seen.add(identity)
            distance = candidate["distance"]
            _require(isinstance(distance, (int, float)) and not isinstance(distance, bool), "distance must be a number")
            number = float(distance)
            _require(number == number and abs(number) != float("inf"), "distance must be finite")
            clean.append({"id": identity, "distance": number})
        parsed.append({"candidates": clean})
    return parsed


def choose_targets(frames: list[dict], target: str, policy: str) -> list[str]:
    chosen: list[str] = []
    held = target
    for frame in frames:
        candidates = frame["candidates"]
        ids = {item["id"] for item in candidates}
        if policy == "nearest-face":
            pick = min(candidates, key=lambda item: (item["distance"], item["id"]))["id"]
        elif policy == "identity":
            if target in ids:
                pick = target
                held = target
            else:
                # Target loss: hold the documented identity. Do not jump to whoever is nearest.
                pick = held
        else:
            raise ValueError("policy must be identity or nearest-face")
        chosen.append(pick)
    return chosen


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    target = payload["targetId"]
    _require(isinstance(target, str) and target.strip(), "targetId must be a non-empty string")
    policy = payload["policy"]
    frames = _frames(payload["frames"])
    chosen = choose_targets(frames, target, policy)
    jumped = policy == "nearest-face" and any(item != target for item in chosen)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, "chosen " + ",".join(chosen)]
    rejected: list[str] = []
    if jumped:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("focus jumped away from the selected identity")
    else:
        decision = "recorded"
        if any(target not in {item["id"] for item in frame["candidates"]} for frame in frames):
            reasons.append("target loss held the documented identity without a nearest-face jump")
        else:
            reasons.append("focus followed the selected identity")
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
