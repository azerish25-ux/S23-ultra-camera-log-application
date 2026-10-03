"""TC-P067-05 temporal chunk discontinuity.

Intervention: Resume or begin a chunk while a moving object and focus
transition cross its boundary.
Expected: Reconstruct required context and emit each output frame once with
stable temporal behavior.
Negative: Empty-history restart at every chunk must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P067-05"
INTERVENTION = "Resume or begin a chunk while a moving object and focus transition cross its boundary."
EXPECTED = "Reconstruct required context and emit each output frame once with stable temporal behavior."
NEGATIVE = "Empty-history restart at every chunk must fail."
REPEAT = "Repeat with scene cuts, overlap trimming, and replaced model identities."

_SITES = ("boundary", "scene-cut", "overlap-trim", "replaced-model")
_PAYLOAD_KEYS = (
    "chunkId",
    "site",
    "movingObject",
    "focusTransition",
    "emptyHistory",
    "contextReconstructed",
    "frameCount",
    "duplicateFrame",
    "stableTemporal",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "context_reconstructed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_COUNT = re.compile(r"[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Reconstruct chunk context once, or reject an empty-history restart."""
    chunk, site, moving, focus, empty, reconstructed, frames, duplicate, stable = _payload(payload)
    preserved = [
        chunk,
        f"site:{site}",
        f"moving:{str(moving).lower()}",
        f"focus:{str(focus).lower()}",
        f"frames:{frames}",
        f"context:{str(reconstructed).lower()}",
        f"stable:{str(stable).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"site {site}"]
    rejected: list[str] = []
    if not moving or not focus:
        decision = "withheld"
        reasons.append("moving object and focus transition did not both cross the chunk boundary")
        questions.append(f"chunk {chunk} was retained")
        return _result(decision, reasons, rejected, preserved, questions)
    if empty:
        rejected.append("empty-history-restart")
        reasons.append(NEGATIVE)
        reasons.append(f"chunk {chunk} did not restart from empty history")
    if not reconstructed:
        rejected.append("missing-context")
        reasons.append(f"chunk {chunk} did not reconstruct required context")
    if frames != "1" or duplicate:
        rejected.append("frame-not-once")
        reasons.append(f"chunk {chunk} emitted {frames} frames; duplicate={str(duplicate).lower()}")
    if not stable:
        rejected.append("unstable-temporal")
        reasons.append(f"chunk {chunk} temporal behavior was not stable")
    if rejected:
        decision = "rejected"
        questions.append(f"chunk {chunk} frame count {frames} was retained")
    else:
        decision = "context_reconstructed"
        reasons.append(f"chunk {chunk} emitted frame count {frames} with reconstructed context")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    chunk = payload["chunkId"]
    if not isinstance(chunk, str) or _TOKEN.fullmatch(chunk) is None:
        raise ValueError("chunkId must be a token")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    moving = payload["movingObject"]
    focus = payload["focusTransition"]
    empty = payload["emptyHistory"]
    reconstructed = payload["contextReconstructed"]
    duplicate = payload["duplicateFrame"]
    stable = payload["stableTemporal"]
    for name, value in (
        ("movingObject", moving),
        ("focusTransition", focus),
        ("emptyHistory", empty),
        ("contextReconstructed", reconstructed),
        ("duplicateFrame", duplicate),
        ("stableTemporal", stable),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
    frames = payload["frameCount"]
    if not isinstance(frames, str) or _COUNT.fullmatch(frames) is None:
        raise ValueError("frameCount must be a canonical positive integer string")
    return chunk, site, moving, focus, empty, reconstructed, frames, duplicate, stable


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P067-05 must not yield qualified or allowed")
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
