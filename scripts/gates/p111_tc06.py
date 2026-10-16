"""TC-P111-06 Subject identity crossing.

Host fixture. The selected identity is followed. Low confidence holds focus.
Choosing the nearest face independently in every frame is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P111-06"
NAME = "Subject identity crossing"
INTERVENTION = "Let two similar subjects cross while one remains the user-selected focus target."
EXPECTED = "Follow the documented identity and target-loss policy without unexplained focus jumps."
NEGATIVE = "Choosing the nearest face independently in every frame must fail."
REPEAT = "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking."
PAYLOAD_KEYS = ("evidenceId", "repeat", "confidenceThreshold", "maxDistancePerFrame", "frameMs", "selectedIdentity", "frames")
TRACK_KEYS = {"identity", "confidence", "focus_distance"}
FRAME_KEYS = {"t_ms", "tracks", "appliedFocus", "appliedState", "appliedIdentity"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p111_implement_stable_focus_tracking_and_pulls_tc06",
    Path(__file__).resolve().parent / "p111_implement_stable_focus_tracking_and_pulls.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _flatten(frame: dict, selected: str, index: int) -> dict:
    if not isinstance(frame, dict) or set(frame) != FRAME_KEYS:
        raise ValueError(f"frame {index} keys are invalid")
    tracks = frame["tracks"]
    if not isinstance(tracks, list) or not tracks:
        raise ValueError(f"frame {index} tracks must be a non-empty list")
    parsed = []
    seen = set()
    for track_index, track in enumerate(tracks):
        if not isinstance(track, dict) or set(track) != TRACK_KEYS:
            raise ValueError(f"frame {index} track {track_index} keys are invalid")
        identity = _text(track["identity"], "identity")
        if identity in seen:
            raise ValueError("track identities must be unique in a frame")
        seen.add(identity)
        parsed.append(track)
    nearest = min(parsed, key=lambda track: (float(track["focus_distance"]), track["identity"]))
    selected_tracks = [track for track in parsed if track["identity"] == selected]
    if selected_tracks:
        best = max(selected_tracks, key=lambda track: (float(track["confidence"]), track["identity"]))
        identity = selected
        confidence = best["confidence"]
        proposed = best["focus_distance"]
    else:
        identity = nearest["identity"]
        confidence = 0.0
        proposed = nearest["focus_distance"]
    return {
        "t_ms": frame["t_ms"],
        "confidence": confidence,
        "proposedFocus": proposed,
        "appliedFocus": frame["appliedFocus"],
        "appliedState": frame["appliedState"],
        "identity": identity,
        "selectedIdentity": selected,
        "nearestFaceFocus": nearest["focus_distance"],
        "appliedIdentity": frame["appliedIdentity"],
    }


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    selected = _text(payload["selectedIdentity"], "selectedIdentity")
    frames = payload["frames"]
    if not isinstance(frames, list) or len(frames) < 2:
        raise ValueError("frames must contain at least 2 samples")
    flat = [_flatten(frame, selected, index) for index, frame in enumerate(frames)]
    for index, item in enumerate(flat):
        applied_identity = item["appliedIdentity"]
        if not isinstance(applied_identity, str) or not applied_identity.strip() or applied_identity != applied_identity.strip():
            raise ValueError(f"frame {index} appliedIdentity must be a non-empty string")
    observations = [{key: item[key] for key in item if key != "appliedIdentity"} for item in flat]
    judged = _GATE.judge_tracking(
        observations,
        payload["confidenceThreshold"],
        payload["maxDistancePerFrame"],
        payload["frameMs"],
    )
    rejected = list(judged["rejectedClaims"])
    nearest_choices = 0
    for item in flat:
        took_nearest = item["appliedIdentity"] != selected and _GATE._close(
            float(item["appliedFocus"]), float(item["nearestFaceFocus"])
        )
        if took_nearest:
            nearest_choices += 1
            if "nearest-face-independently-every-frame" not in rejected:
                rejected.append("nearest-face-independently-every-frame")
        elif item["appliedIdentity"] != selected and "unexplained-focus-jump" not in rejected:
            rejected.append("unexplained-focus-jump")
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        (
            f"duration_ms={judged['duration_ms']} "
            f"start_distance={_GATE.fmt(judged['start_distance'])} "
            f"end_distance={_GATE.fmt(judged['end_distance'])}"
        ),
        "policy:" + ",".join(
            f"{item['t_ms']}:{_GATE.fmt(item['focus_distance'])}:{item['state']}" for item in judged["expected"]
        ),
    ]
    if nearest_choices == len(flat):
        if _GATE.MUTANT not in rejected:
            rejected.append(_GATE.MUTANT)
        reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
        if NEGATIVE not in reasons and "jump-on-low-confidence" in rejected:
            reasons.append("low confidence jumped to a new target instead of holding")
        if NEGATIVE not in reasons and "nearest-face-independently-every-frame" in rejected:
            reasons.append(NEGATIVE)
    else:
        decision = "recorded"
        reasons.append("selected identity held through the cross; nearest face was not taken")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    preserved = [
        evidence,
        f"duration_ms:{judged['duration_ms']}",
        f"start_distance:{_GATE.fmt(judged['start_distance'])}",
        f"end_distance:{_GATE.fmt(judged['end_distance'])}",
    ]
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
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    if f"duration_ms:{judged['duration_ms']}" not in result["preservedResults"]:
        raise ValueError("pull duration dropped")
    return result
