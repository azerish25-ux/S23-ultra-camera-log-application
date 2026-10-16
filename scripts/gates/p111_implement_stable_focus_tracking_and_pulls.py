#!/usr/bin/env python3
"""P111 Implement stable focus tracking and pulls.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P111-01 through TC-P111-08 modules.

The pull limiter is ``max_distance_per_frame``. ``pull_limiter`` returns the
furthest focus a single frame may reach. A curve labelled as a smooth pull
whose sampled one-frame step is larger than that limit is rejected. Focus
between keys is linear. Past the last key the last distance is held and the
state is ``held``; claiming interpolation there is rejected. Tracking loss
(confidence below the threshold, or a different identity) holds the last
focus and sets state ``held`` instead of jumping to a nearer face.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P111"
TITLE = "Implement stable focus tracking and pulls"
WORKSTREAM = 14
SLUG = "implement_stable_focus_tracking_and_pulls"
DEPENDENCIES = ("P110",)
GOAL = "Make intentional focus motion distinct from model instability."
METHOD = (
    "Track a selected subject identity with confidence and explicit loss behavior. "
    "Smooth focus in a defined coordinate domain, support keyframed pulls, and avoid "
    "abrupt target changes when subjects cross. Store focus decisions in the recipe "
    "for reproducibility."
)
FIXTURE = "Two people cross paths while the selected subject briefly leaves the frame."
ORACLE = (
    "The system follows its documented hold or reacquire policy rather than jumping "
    "to the nearer face silently."
)
MUTANT = "Select the nearest detected face independently in every frame."
DELIVERABLE = "Focus tracker and deterministic focus-curve tests"
PULL_LIMITER = "max_distance_per_frame"

ABS_TOL = 1e-9
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "frameMs",
    "maxDistancePerFrame",
    "confidenceThreshold",
    "labelledSmooth",
    "pull",
    "query",
    "tracking",
}
QUERY_KEYS = {"t_ms", "reportedFocus", "reportedState", "claimsInterpolationBeyondKeys"}
TRACK_KEYS = {
    "t_ms",
    "confidence",
    "proposedFocus",
    "appliedFocus",
    "appliedState",
    "identity",
    "selectedIdentity",
    "nearestFaceFocus",
}
PULL_KEY_KEYS = {"t_ms", "focus_distance"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
REPORTED_STATES = {"interpolated", "held", "key"}
APPLIED_STATES = {"tracking", "held"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fmt(value: float) -> str:
    text = format(float(value), ".12g")
    if "e" in text or "E" in text:
        text = format(float(value), ".12f").rstrip("0").rstrip(".")
    return text


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=ABS_TOL)


def _exceeds(step: float, limit: float) -> bool:
    return step > limit and not _close(step, limit)


def _text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _number(value: Any, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def _positive_distance(value: Any, label: str) -> float:
    number = _number(value, label)
    require(number > 0.0, f"{label} must be > 0")
    return number


def _whole_ms(value: Any, label: str) -> int:
    require(type(value) is int and value >= 0, f"{label} must be an int >= 0")
    return value


def _unit_interval(value: Any, label: str) -> float:
    number = _number(value, label)
    require(0.0 <= number <= 1.0, f"{label} must be inside [0, 1]")
    return number


def parse_pull(keys: Any) -> list[dict[str, Any]]:
    """Validate a focus pull: a list of ``{t_ms, focus_distance}``."""
    require(isinstance(keys, list) and len(keys) >= 2, "pull must contain at least 2 keys")
    parsed: list[dict[str, Any]] = []
    previous_t = -1
    for index, item in enumerate(keys):
        require(isinstance(item, dict) and set(item) == PULL_KEY_KEYS, f"pull key {index} must contain t_ms and focus_distance")
        t_ms = _whole_ms(item["t_ms"], f"pull key {index} t_ms")
        distance = _positive_distance(item["focus_distance"], f"pull key {index} focus_distance")
        require(t_ms > previous_t, "pull keys must be strictly increasing in t_ms")
        parsed.append({"t_ms": t_ms, "focus_distance": distance})
        previous_t = t_ms
    return parsed


def describe_pull(keys: list[dict]) -> dict[str, Any]:
    """Retain pull duration and the start and end focus distances."""
    parsed = parse_pull(keys)
    return {
        "duration_ms": parsed[-1]["t_ms"] - parsed[0]["t_ms"],
        "start_distance": parsed[0]["focus_distance"],
        "end_distance": parsed[-1]["focus_distance"],
    }


def interpolate_focus(keys: list[dict], t_ms: int) -> dict[str, Any]:
    """Linearly interpolate focus at ``t_ms``.

    Outside the key span the nearest endpoint is held. The state is ``held``.
    This does not extrapolate past the last key and does not report
    ``interpolated`` outside the span.
    """
    parsed = parse_pull(keys)
    t_ms = _whole_ms(t_ms, "t_ms")
    first = parsed[0]
    last = parsed[-1]
    if t_ms < first["t_ms"] or t_ms > last["t_ms"]:
        anchor = first if t_ms < first["t_ms"] else last
        return {
            "t_ms": t_ms,
            "focus_distance": anchor["focus_distance"],
            "state": "held",
            "beyond_keys": True,
        }
    for index, key in enumerate(parsed):
        if key["t_ms"] == t_ms:
            return {
                "t_ms": t_ms,
                "focus_distance": key["focus_distance"],
                "state": "key",
                "beyond_keys": False,
            }
        nxt = parsed[index + 1]
        if key["t_ms"] < t_ms < nxt["t_ms"]:
            span = nxt["t_ms"] - key["t_ms"]
            alpha = (t_ms - key["t_ms"]) / span
            distance = key["focus_distance"] + alpha * (nxt["focus_distance"] - key["focus_distance"])
            return {
                "t_ms": t_ms,
                "focus_distance": distance,
                "state": "interpolated",
                "beyond_keys": False,
            }
    raise ValueError("t_ms fell through interpolation")


def pull_limiter(previous_distance: float, proposed_distance: float, max_distance_per_frame: float) -> float:
    """Limit one frame of focus motion to ``max_distance_per_frame``.

    A requested step larger than the limit is not returned unchanged. The sign
    of the pull is preserved. A step equal to the limit is allowed.
    """
    previous = _positive_distance(previous_distance, "previous_distance")
    proposed = _positive_distance(proposed_distance, "proposed_distance")
    limit = _positive_distance(max_distance_per_frame, "max_distance_per_frame")
    delta = proposed - previous
    if not _exceeds(abs(delta), limit):
        return proposed
    return previous + math.copysign(limit, delta)


def _frame_times(parsed: list[dict[str, Any]], frame_ms: int) -> list[int]:
    require(type(frame_ms) is int and frame_ms > 0, "frameMs must be an int > 0")
    start = parsed[0]["t_ms"]
    end = parsed[-1]["t_ms"]
    require((end - start) % frame_ms == 0, "pull duration must be a whole number of frames")
    for key in parsed:
        require((key["t_ms"] - start) % frame_ms == 0, "pull keys must lie on the frame grid")
    times: list[int] = []
    t_ms = start
    while t_ms <= end:
        times.append(t_ms)
        t_ms += frame_ms
    return times


def max_one_frame_step(keys: list[dict], frame_ms: int) -> float:
    """Largest absolute focus change between adjacent frame samples of a pull."""
    parsed = parse_pull(keys)
    times = _frame_times(parsed, frame_ms)
    samples = [interpolate_focus(parsed, t_ms)["focus_distance"] for t_ms in times]
    if len(samples) < 2:
        return 0.0
    return max(abs(samples[index] - samples[index - 1]) for index in range(1, len(samples)))


def _parse_observation(item: Any, index: int) -> dict[str, Any]:
    require(isinstance(item, dict) and set(item) == TRACK_KEYS, f"tracking {index} keys are invalid")
    state = item["appliedState"]
    require(state in APPLIED_STATES, f"tracking {index} appliedState is invalid")
    return {
        "t_ms": _whole_ms(item["t_ms"], f"tracking {index} t_ms"),
        "confidence": _unit_interval(item["confidence"], f"tracking {index} confidence"),
        "proposedFocus": _positive_distance(item["proposedFocus"], f"tracking {index} proposedFocus"),
        "appliedFocus": _positive_distance(item["appliedFocus"], f"tracking {index} appliedFocus"),
        "appliedState": state,
        "identity": _text(item["identity"], f"tracking {index} identity"),
        "selectedIdentity": _text(item["selectedIdentity"], f"tracking {index} selectedIdentity"),
        "nearestFaceFocus": _positive_distance(item["nearestFaceFocus"], f"tracking {index} nearestFaceFocus"),
    }


def judge_tracking(
    observations: list[dict],
    confidence_threshold: float,
    max_distance_per_frame: float,
    frame_ms: int,
) -> dict[str, Any]:
    """Apply hold-on-loss and the pull limiter to a tracking sequence.

    Confidence below ``confidence_threshold``, or an identity other than the
    selected subject, holds the last focus and sets state ``held``. It does
    not adopt the proposed or nearest-face distance. While locked, focus may
    move toward the selected distance by at most ``max_distance_per_frame``
    per frame.
    """
    require(isinstance(observations, list) and observations, "tracking must be a non-empty list")
    require(type(frame_ms) is int and frame_ms > 0, "frameMs must be an int > 0")
    threshold = _unit_interval(confidence_threshold, "confidenceThreshold")
    limit = _positive_distance(max_distance_per_frame, "max_distance_per_frame")
    parsed = [_parse_observation(item, index) for index, item in enumerate(observations)]
    selected = parsed[0]["selectedIdentity"]
    for index, item in enumerate(parsed):
        require(item["selectedIdentity"] == selected, "selected identity must stay constant")
        if index:
            require(item["t_ms"] > parsed[index - 1]["t_ms"], "tracking times must be strictly increasing")
            require((item["t_ms"] - parsed[0]["t_ms"]) % frame_ms == 0, "tracking times must lie on the frame grid")
    expected: list[dict[str, Any]] = []
    rejected: list[str] = []
    previous: float | None = None
    previous_t: int | None = None
    for item in parsed:
        locked = item["identity"] == selected and item["confidence"] >= threshold
        below = item["confidence"] < threshold
        if previous is None:
            require(locked, "tracking must start with a confident lock on the selected identity")
            focus = item["proposedFocus"]
            state = "tracking"
            allowance = limit
        else:
            frames = (item["t_ms"] - previous_t) / frame_ms
            require(frames == int(frames) and frames > 0, "tracking times must advance by whole frames")
            allowance = limit * frames
            if not locked:
                focus = previous
                state = "held"
            else:
                focus = pull_limiter(previous, item["proposedFocus"], allowance)
                state = "tracking"
        if not _close(item["appliedFocus"], focus):
            jumped = _exceeds(abs(item["appliedFocus"] - (previous if previous is not None else focus)), allowance)
            if state == "held" and below:
                _add(rejected, "jump-on-low-confidence")
            elif state == "held":
                _add(rejected, "unexplained-focus-jump")
            elif jumped:
                _add(rejected, "one-frame-jump-exceeds-pull-limiter")
            else:
                _add(rejected, "focus-policy-mismatch")
        if item["appliedState"] != state:
            if state == "held":
                _add(rejected, "tracking-loss-not-held")
            else:
                _add(rejected, "reported-state-mismatch")
        if (
            not locked
            and _close(item["appliedFocus"], item["nearestFaceFocus"])
            and not _close(item["nearestFaceFocus"], focus)
        ):
            _add(rejected, "nearest-face-independently-every-frame")
        expected.append(
            {
                "t_ms": item["t_ms"],
                "focus_distance": focus,
                "state": state,
                "identity": selected,
            }
        )
        previous = focus
        previous_t = item["t_ms"]
    nearest_every_frame = all(
        _close(item["appliedFocus"], item["nearestFaceFocus"]) for item in parsed
    )
    diverged = any(
        not _close(item["nearestFaceFocus"], sample["focus_distance"])
        for item, sample in zip(parsed, expected)
    )
    if nearest_every_frame and diverged:
        _add(rejected, MUTANT)
    return {
        "expected": expected,
        "rejectedClaims": rejected,
        "duration_ms": parsed[-1]["t_ms"] - parsed[0]["t_ms"],
        "start_distance": expected[0]["focus_distance"],
        "end_distance": expected[-1]["focus_distance"],
    }


def _add(items: list[str], token: str) -> None:
    if token not in items:
        items.append(token)


def _parse_query(query: Any) -> dict[str, Any]:
    require(isinstance(query, dict) and set(query) == QUERY_KEYS, "query keys are invalid")
    state = query["reportedState"]
    require(state in REPORTED_STATES, "reportedState is invalid")
    require(type(query["claimsInterpolationBeyondKeys"]) is bool, "claimsInterpolationBeyondKeys must be a bool")
    return {
        "t_ms": _whole_ms(query["t_ms"], "query t_ms"),
        "reportedFocus": _positive_distance(query["reportedFocus"], "reportedFocus"),
        "reportedState": state,
        "claimsInterpolationBeyondKeys": query["claimsInterpolationBeyondKeys"],
    }


def _recipe(samples: list[dict[str, Any]]) -> str:
    parts = [f"{item['t_ms']}:{fmt(item['focus_distance'])}:{item['state']}" for item in samples]
    return ",".join(parts)


def assess(document: dict) -> dict[str, Any]:
    """Judge a host focus-pull and tracking fixture.

    The decision is only ``recorded`` or ``rejected``. Evidence, pull duration,
    and start/end distances stay in the result either way. Physical S23 capture
    is not run.
    """
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = _text(document["evidenceId"], "evidenceId")
    claim = _text(document["claim"], "claim")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    require(type(document["labelledSmooth"]) is bool, "labelledSmooth must be a bool")
    frame_ms = document["frameMs"]
    require(type(frame_ms) is int and frame_ms > 0, "frameMs must be an int > 0")
    limit = _positive_distance(document["maxDistancePerFrame"], "maxDistancePerFrame")
    threshold = _unit_interval(document["confidenceThreshold"], "confidenceThreshold")
    parsed = parse_pull(document["pull"])
    described = describe_pull(parsed)
    query = _parse_query(document["query"])
    step = max_one_frame_step(parsed, frame_ms)
    sample = interpolate_focus(parsed, query["t_ms"])
    judged = judge_tracking(document["tracking"], threshold, limit, frame_ms)
    rejected: list[str] = []
    if document["applyMutant"]:
        _add(rejected, MUTANT)
    if document["labelledSmooth"] and _exceeds(step, limit):
        _add(rejected, "one-frame-jump-exceeds-pull-limiter")
    if query["claimsInterpolationBeyondKeys"]:
        _add(rejected, "claimed-interpolation-beyond-keys")
    if sample["beyond_keys"] and query["reportedState"] != "held":
        _add(rejected, "clamp-without-held")
    if not _close(query["reportedFocus"], sample["focus_distance"]):
        _add(rejected, "reported-focus-mismatch")
    if not sample["beyond_keys"] and query["reportedState"] != sample["state"]:
        _add(rejected, "reported-state-mismatch")
    for token in judged["rejectedClaims"]:
        _add(rejected, token)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        (
            f"pull limiter {PULL_LIMITER}={fmt(limit)} "
            f"max_one_frame_step={fmt(step)} labelled_smooth={document['labelledSmooth']}"
        ),
        (
            f"duration_ms={described['duration_ms']} "
            f"start_distance={fmt(described['start_distance'])} "
            f"end_distance={fmt(described['end_distance'])}"
        ),
        f"query t_ms={query['t_ms']} state={sample['state']} focus_distance={fmt(sample['focus_distance'])}",
    ]
    if document["labelledSmooth"] and _exceeds(step, limit):
        reasons.append("one-frame jump larger than the pull limiter was labelled as a smooth pull")
    elif _exceeds(step, limit):
        reasons.append("step exceeds the pull limiter and was not labelled as a smooth pull")
    elif document["labelledSmooth"]:
        reasons.append("smooth pull stays inside the pull limiter")
    else:
        reasons.append("pull was not labelled smooth; one-frame step stays inside the pull limiter")
    if sample["beyond_keys"]:
        reasons.append("beyond the last key focus is held; it is not extrapolated")
    else:
        reasons.append("focus at the query time is linear interpolation between surrounding keys")
    if any(item["state"] == "held" for item in judged["expected"]):
        reasons.append("tracking loss held the last focus and set state held")
    reasons.append("method: " + METHOD)
    questions = [
        "physical S23 capture was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    decision = "rejected" if rejected else "recorded"
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    frame_samples = [
        interpolate_focus(parsed, t_ms) for t_ms in _frame_times(parsed, frame_ms)
    ]
    preserved = [
        evidence,
        claim,
        f"duration_ms:{described['duration_ms']}",
        f"start_distance:{fmt(described['start_distance'])}",
        f"end_distance:{fmt(described['end_distance'])}",
        "pull_recipe:" + _recipe(frame_samples),
        "tracking_recipe:" + _recipe(judged["expected"]),
    ]
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(f"duration_ms:{described['duration_ms']}" in result["preservedResults"], "pull duration dropped")
    require(f"start_distance:{fmt(described['start_distance'])}" in result["preservedResults"], "start distance dropped")
    require(f"end_distance:{fmt(described['end_distance'])}" in result["preservedResults"], "end distance dropped")
    return result
