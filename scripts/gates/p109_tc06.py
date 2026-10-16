"""TC-P109-06 Subject identity crossing.

Host fixture. Nearest-face reselection is rejected when identities cross.
A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P109-06"
NAME = "Subject identity crossing"
INTERVENTION = "Let two similar subjects cross while one remains the user-selected focus target."
EXPECTED = "Follow the documented identity and target-loss policy without unexplained focus jumps."
NEGATIVE = "Choosing the nearest face independently in every frame must fail."
REPEAT = "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking."
NEGATIVE_TOKEN = "nearest-face-independently-every-frame"
JUMP_TOKEN = "unexplained-focus-jump"
PAYLOAD_KEYS = ("evidenceId", "repeat", "selectedIdentity", "frames")
FRAME_KEYS = {"nearestFace", "chosenFocus", "policy"}
POLICIES = {"follow-selected", "nearest-face", "target-loss"}
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


def _name(value: object, message: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(), message)
    return value


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
    selected = _name(payload["selectedIdentity"], "selectedIdentity must be a non-empty string")
    frames = payload["frames"]
    _require(isinstance(frames, list) and len(frames) >= 1, "frames must be a non-empty list")
    rejected: list[str] = []
    jumps: list[str] = []
    nearest_frames: list[str] = []
    for index, frame in enumerate(frames):
        _require(isinstance(frame, dict) and set(frame) == FRAME_KEYS, f"frame {index} keys")
        nearest = _name(frame["nearestFace"], f"frame {index} nearestFace")
        chosen = _name(frame["chosenFocus"], f"frame {index} chosenFocus")
        policy = frame["policy"]
        _require(policy in POLICIES, f"frame {index} policy")
        if policy == "nearest-face":
            nearest_frames.append(str(index))
        elif policy == "follow-selected" and chosen != selected:
            jumps.append(f"{index}:{chosen}")
        elif policy == "target-loss" and chosen == nearest and nearest != selected:
            jumps.append(f"{index}:{chosen}")
    if nearest_frames:
        rejected.append(NEGATIVE_TOKEN)
    if jumps:
        rejected.append(JUMP_TOKEN)
    if nearest_frames or jumps:
        detail = (
            "nearest-face frames " + (",".join(nearest_frames) if nearest_frames else "none")
            + "; focus jumps " + (",".join(jumps) if jumps else "none")
        )
        return _finish(evidence, repeat, "rejected", rejected, detail)
    detail = f"focus stayed with {selected} or a documented target-loss state"
    return _finish(evidence, repeat, "recorded", [], detail)
