#!/usr/bin/env python3
"""P018 pure capture-state reducer and race replay.

States are opening, preview, configuring, starting, recording, stopping,
finalizing, and failure. Every asynchronous event carries a generation token.
The recording timer and the active indicator change only after a first-sample
acknowledgement for the current generation. A Record followed immediately by
Stop does not return to recording when the first video sample or the audio
format callback arrives late.

The deliberate mutation — any first-frame callback sets recording=true — is
rejected. This module does not probe a device and does not qualify a physical
S23. It does not execute TC-P018-01 through TC-P018-08.
"""

from __future__ import annotations

import copy
import re
from typing import Any


PHASE = "P018"
CASE_ID = "P018"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
LOG_ID = "s23-capture-reducer-record-stop-race"
METHOD = (
    "Use distinct opening, preview, configuring, starting, recording, stopping, "
    "finalizing, and failure states. Every asynchronous event carries a generation "
    "token. First-sample acknowledgement is required before the recording timer "
    "and active indicator change."
)
FIXTURE = (
    "Record followed immediately by Stop, with a delayed first video sample and "
    "a delayed audio format callback."
)
ORACLE = (
    "The state never returns from stopping to recording and the retained output "
    "receives an accurate terminal status."
)
MUTANT = "Allow any first-frame callback to set recording=true."
MUTANT_CLAIM = "first-frame-sets-recording"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
STATES = (
    "opening",
    "preview",
    "configuring",
    "starting",
    "recording",
    "stopping",
    "finalizing",
    "failure",
)
EVENT_TYPES = (
    "camera_opened",
    "configure",
    "configured",
    "record",
    "stop",
    "first_video_sample",
    "audio_format",
    "first_sample_ack",
    "finalize",
    "finalized",
    "fail",
    "generation_advanced",
    "surface_attach",
)
FIRST_FRAME = frozenset({"first_video_sample", "first_sample_ack"})
FIXTURE_KEYS = {
    "schemaVersion",
    "phase",
    "logId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "states",
    "takeId",
    "events",
}
EVENT_KEYS = {"seq", "type", "generation", "owner", "delayed"}
OPTIONAL_EVENT_KEYS = {"seq", "delayed", "hold", "release", "surface", "takeId"}
REQUIRED_EVENT_KEYS = {"type", "generation", "owner"}
LOG_KEYS = ("seq", "type", "generation", "owner", "delayed", "stale", "applied")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
TERMINAL_KEYS = (
    "takeId",
    "status",
    "recordingEntered",
    "lateFirstVideoSample",
    "lateAudioFormat",
    "returnedToRecording",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _string_list(value: object, label: str) -> list[str]:
    require(isinstance(value, list), label + " must be a list")
    for item in value:
        require(_text(item), label + " must contain non-empty strings")
    return list(value)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def initial_state(take_id: str = "take-1") -> dict[str, Any]:
    """Opening state. Generation 0 means no owner has been adopted yet."""
    require(_text(take_id), "takeId must be a non-empty string")
    return {
        "state": "opening",
        "generation": 0,
        "owner": "",
        "recording": False,
        "indicatorActive": False,
        "timerRunning": False,
        "firstSampleAcknowledged": False,
        "stopRequested": False,
        "stoppedBeforeFirstSample": False,
        "lateFirstVideoSample": False,
        "lateAudioFormat": False,
        "returnedFromStoppingToRecording": False,
        "takeId": take_id,
        "attachedSurface": None,
        "resources": {},
        "released": [],
        "transitions": [],
        "eventLog": [],
        "terminalStatus": None,
        "retainedOutput": None,
    }


def _goto(state: dict, new_state: str) -> None:
    require(new_state in STATES, "unknown state")
    previous = state["state"]
    if previous == "stopping" and new_state == "recording":
        state["returnedFromStoppingToRecording"] = True
    if previous != new_state:
        state["transitions"].append(previous + "->" + new_state)
    state["state"] = new_state


def _validate_event(event: object) -> dict:
    require(isinstance(event, dict), "event must be an object")
    missing = REQUIRED_EVENT_KEYS - set(event)
    extra = set(event) - REQUIRED_EVENT_KEYS - OPTIONAL_EVENT_KEYS
    require(not missing, "event missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "event has unexpected fields: " + ", ".join(sorted(extra)))
    require(event["type"] in EVENT_TYPES, "unknown event type")
    generation = event["generation"]
    require(type(generation) is int and generation > 0, "generation must be a positive int")
    require(_text(event["owner"]), "owner must be a non-empty string")
    if "seq" in event:
        require(type(event["seq"]) is int and event["seq"] > 0, "seq must be a positive int")
    if "delayed" in event:
        require(type(event["delayed"]) is bool, "delayed must be a bool")
    for key in ("hold", "release"):
        if key in event:
            _string_list(event[key], key)
    if "surface" in event:
        require(_text(event["surface"]), "surface must be a non-empty string")
    if "takeId" in event:
        require(_text(event["takeId"]), "takeId must be a non-empty string")
    if event["type"] == "surface_attach":
        require("surface" in event, "surface_attach needs surface")
    return event


def _append_log(state: dict, event: dict) -> None:
    entry = {
        "seq": event["seq"] if "seq" in event else len(state["eventLog"]) + 1,
        "type": event["type"],
        "generation": event["generation"],
        "owner": event["owner"],
        "delayed": event["delayed"] if "delayed" in event else False,
        "stale": False,
        "applied": True,
    }
    require(tuple(entry) == LOG_KEYS, "event log keys drifted")
    state["eventLog"].append(entry)


def _mark(state: dict, *, stale: bool = False, applied: bool = True) -> None:
    state["eventLog"][-1]["stale"] = stale
    state["eventLog"][-1]["applied"] = applied


def _is_stale(state: dict, event: dict) -> bool:
    if event["type"] == "generation_advanced":
        return False
    if event["type"] == "camera_opened" and state["state"] == "opening" and state["generation"] == 0:
        return False
    if state["generation"] == 0:
        return False
    if event["generation"] != state["generation"]:
        return True
    if state["owner"] and event["owner"] != state["owner"]:
        return True
    return False


def _release_listed(state: dict, resource_ids: list[str], generation: int) -> None:
    """Release a resource only when that generation still owns it."""
    for resource_id in resource_ids:
        if state["resources"].get(resource_id) == generation:
            del state["resources"][resource_id]
            state["released"].append(resource_id)


def _release_stale(state: dict, event: dict) -> None:
    _release_listed(state, list(event.get("release") or []), event["generation"])


def _hold(state: dict, event: dict) -> None:
    generation = state["generation"]
    for resource_id in event.get("hold") or []:
        state["resources"][resource_id] = generation
    surface = event.get("surface")
    if surface:
        state["attachedSurface"] = surface
        state["resources"][surface] = generation


def _terminal(state: dict, *, failed: bool = False) -> dict[str, Any]:
    if failed:
        status = "failed"
    elif state["stoppedBeforeFirstSample"] or not state["firstSampleAcknowledged"]:
        status = "stopped_before_first_sample"
    else:
        status = "stopped"
    terminal = {
        "takeId": state["takeId"],
        "status": status,
        "recordingEntered": state["firstSampleAcknowledged"] is True and not failed,
        "lateFirstVideoSample": state["lateFirstVideoSample"] is True,
        "lateAudioFormat": state["lateAudioFormat"] is True,
        "returnedToRecording": state["returnedFromStoppingToRecording"] is True,
    }
    if failed:
        terminal["recordingEntered"] = False
    require(tuple(terminal) == TERMINAL_KEYS, "terminal status keys drifted")
    return terminal


def _seal(state: dict, *, failed: bool = False) -> None:
    terminal = _terminal(state, failed=failed)
    state["terminalStatus"] = terminal
    state["retainedOutput"] = dict(terminal)


def _apply_mutant(state: dict) -> None:
    """Rejected behavior: a first-frame callback forces recording on."""
    if state["state"] == "stopping":
        state["returnedFromStoppingToRecording"] = True
    _goto(state, "recording")
    state["recording"] = True
    state["indicatorActive"] = True
    state["timerRunning"] = True


def _apply(state: dict, event: dict) -> None:
    etype = event["type"]
    current = state["state"]
    applied = True

    if etype == "camera_opened" and current == "opening":
        state["generation"] = event["generation"]
        state["owner"] = event["owner"]
        _goto(state, "preview")
        _hold(state, event)
    elif etype == "configure" and current == "preview":
        _goto(state, "configuring")
    elif etype == "configured" and current == "configuring":
        _goto(state, "preview")
    elif etype == "record" and current == "preview":
        if "takeId" in event:
            state["takeId"] = event["takeId"]
        state["recording"] = False
        state["indicatorActive"] = False
        state["timerRunning"] = False
        state["firstSampleAcknowledged"] = False
        state["stopRequested"] = False
        state["stoppedBeforeFirstSample"] = False
        _goto(state, "starting")
    elif etype == "first_video_sample":
        # A sample is not an acknowledgement. It must not start the timer,
        # the indicator, or recording, and it must not leave stopping.
        if state["stopRequested"] or current in ("stopping", "finalizing", "failure"):
            state["lateFirstVideoSample"] = True
    elif etype == "audio_format":
        if state["stopRequested"] or current in ("stopping", "finalizing", "failure"):
            state["lateAudioFormat"] = True
    elif etype == "first_sample_ack" and current == "starting" and not state["stopRequested"]:
        state["firstSampleAcknowledged"] = True
        state["recording"] = True
        state["indicatorActive"] = True
        state["timerRunning"] = True
        _goto(state, "recording")
    elif etype == "first_sample_ack":
        if state["stopRequested"] or current in ("stopping", "finalizing", "failure"):
            state["lateFirstVideoSample"] = True
    elif etype == "stop" and current in ("starting", "recording"):
        if current == "starting" and not state["firstSampleAcknowledged"]:
            state["stoppedBeforeFirstSample"] = True
        state["stopRequested"] = True
        state["recording"] = False
        state["indicatorActive"] = False
        state["timerRunning"] = False
        _goto(state, "stopping")
    elif etype == "stop" and current == "stopping":
        applied = True
    elif etype == "finalize" and current == "stopping":
        _goto(state, "finalizing")
    elif etype == "finalized" and current == "finalizing":
        _seal(state)
    elif etype == "fail":
        state["recording"] = False
        state["indicatorActive"] = False
        state["timerRunning"] = False
        state["stopRequested"] = True
        _goto(state, "failure")
        owned = [rid for rid, gen in list(state["resources"].items()) if gen == state["generation"]]
        _release_listed(state, owned, state["generation"])
        _seal(state, failed=True)
    elif etype == "generation_advanced":
        require(event["generation"] != state["generation"], "generation_advanced needs a new generation")
        state["generation"] = event["generation"]
        state["owner"] = event["owner"]
        state["recording"] = False
        state["indicatorActive"] = False
        state["timerRunning"] = False
        state["firstSampleAcknowledged"] = False
        state["stopRequested"] = False
        _hold(state, event)
        if state["state"] != "preview":
            _goto(state, "preview")
    elif etype == "surface_attach" and current not in ("stopping", "finalizing", "failure"):
        state["attachedSurface"] = event["surface"]
        state["resources"][event["surface"]] = state["generation"]
    else:
        applied = False

    _mark(state, applied=applied)


def _guard_correct(state: dict) -> None:
    if state["returnedFromStoppingToRecording"]:
        raise ValueError("stopping returned to recording")
    if "stopping->recording" in state["transitions"]:
        raise ValueError("stopping returned to recording")
    if state["recording"] and not (
        state["state"] == "recording" and state["firstSampleAcknowledged"] is True
    ):
        raise ValueError("recording set without first-sample acknowledgement")
    if (state["timerRunning"] or state["indicatorActive"]) and not state["firstSampleAcknowledged"]:
        raise ValueError("timer or indicator changed before first-sample acknowledgement")


def reduce_event(state: dict, event: dict, *, mutant: bool = False) -> dict:
    """Return the next state. The input state is not mutated.

    ``mutant=True`` implements the rejected control: any first-frame callback
    sets ``recording=True``, including a callback that arrives during stopping.
    The default path never does that.
    """
    require(isinstance(state, dict) and state.get("state") in STATES, "state must be a reducer state")
    require(type(mutant) is bool, "mutant must be a bool")
    event = _validate_event(event)
    state = copy.deepcopy(state)
    _append_log(state, event)
    if mutant and event["type"] in FIRST_FRAME:
        _apply_mutant(state)
        _mark(state, stale=False, applied=True)
    elif _is_stale(state, event):
        _release_stale(state, event)
        _mark(state, stale=True, applied=False)
    else:
        _apply(state, event)
    if not mutant:
        _guard_correct(state)
    return state


def replay(events: list, *, mutant: bool = False, take_id: str = "take-1") -> dict:
    """Fold events from the opening state."""
    require(isinstance(events, list), "events must be a list")
    state = initial_state(take_id)
    for event in events:
        state = reduce_event(state, event, mutant=mutant)
    return state


def _canonical_events(events: object) -> None:
    require(isinstance(events, list) and len(events) == 9, "fixture needs the nine-event record/stop race")
    expected = (
        ("camera_opened", False),
        ("configure", False),
        ("configured", False),
        ("record", False),
        ("stop", False),
        ("first_video_sample", True),
        ("audio_format", True),
        ("finalize", False),
        ("finalized", False),
    )
    for index, event in enumerate(events, start=1):
        exact_keys(event, EVENT_KEYS, f"event {index}")
        etype, delayed = expected[index - 1]
        require(event["seq"] == index, "event seq must be contiguous from 1")
        require(event["type"] == etype, "fixture event order drifted at " + etype)
        require(type(event["generation"]) is int and event["generation"] == 1,
                "fixture generation must be 1")
        require(event["owner"] == "session-a", "fixture owner must be session-a")
        require(event["delayed"] is delayed, "fixture delayed flag drifted at " + etype)


def validate_fixture(document: dict) -> None:
    """Raise ValueError unless document is the P018 record/stop race fixture."""
    exact_keys(document, FIXTURE_KEYS, "fixture")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P018")
    require(document["logId"] == LOG_ID, "unexpected logId")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "fixture needs the P018 implementation base revision")
    require(document["method"] == METHOD, "method drifted")
    require(document["fixture"] == FIXTURE, "fixture description drifted")
    require(document["oracle"] == ORACLE, "oracle drifted")
    require(document["mutant"] == MUTANT, "mutant drifted")
    require(document["states"] == list(STATES), "states must be the eight capture states in order")
    require(_text(document["takeId"]), "takeId must be a non-empty string")
    _canonical_events(document["events"])


def _oracle_holds(state: dict) -> bool:
    if state["returnedFromStoppingToRecording"]:
        return False
    if "stopping->recording" in state["transitions"]:
        return False
    if state["state"] == "recording" and state["stopRequested"]:
        return False
    retained = state["retainedOutput"]
    if not isinstance(retained, dict) or tuple(retained) != TERMINAL_KEYS:
        return False
    if retained["returnedToRecording"] is not False:
        return False
    if retained["takeId"] != state["takeId"]:
        return False
    if state["stoppedBeforeFirstSample"]:
        if retained["status"] != "stopped_before_first_sample":
            return False
        if retained["recordingEntered"] is not False:
            return False
        if state["recording"] is not False:
            return False
    if state["lateFirstVideoSample"] and retained["lateFirstVideoSample"] is not True:
        return False
    if state["lateAudioFormat"] and retained["lateAudioFormat"] is not True:
        return False
    if state["firstSampleAcknowledged"] and not state["stoppedBeforeFirstSample"]:
        if retained["recordingEntered"] is not True:
            return False
        if retained["status"] != "stopped":
            return False
    return True


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons), "reasons must be non-empty")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess(document: dict, *, mutant: bool = False) -> dict[str, Any]:
    """Replay the fixture. The mutant decision is rejected and the log is kept.

    A correct replay decides ``terminal_accurate``. That label is a host-fixture
    result only. It is never ``qualified`` and never ``allowed``.
    """
    require(type(mutant) is bool, "mutant must be a bool")
    validate_fixture(document)
    state = replay(document["events"], mutant=mutant, take_id=document["takeId"])
    preserved = [document["takeId"]]
    preserved.extend(f"{event['seq']}:{event['type']}" for event in document["events"])
    retained = state["retainedOutput"]
    if isinstance(retained, dict) and _text(retained.get("status")):
        preserved.append("status:" + retained["status"])
    preserved.append("state:" + state["state"])

    reasons: list[str] = []
    rejected: list[str] = []
    questions = [
        "host fixture only; physical S23 capture was not measured",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, "
        "and cinema-camera equivalence are not claimed",
    ]
    if mutant:
        rejected.append(MUTANT_CLAIM)
        reasons.append("mutant allows any first-frame callback to set recording=true")
    oracle_ok = _oracle_holds(state)
    if not oracle_ok:
        if state["returnedFromStoppingToRecording"] or "stopping->recording" in state["transitions"]:
            rejected.append("stopping-returned-to-recording")
        rejected.append("inaccurate-terminal-status")
        reasons.append(
            "oracle failed: stopping must not return to recording and the retained "
            "output must keep an accurate terminal status"
        )
        decision = "rejected"
    elif mutant:
        decision = "rejected"
        reasons.append("mutant rejected before it can be treated as a successful recording")
    else:
        decision = "terminal_accurate"
        reasons.append("state never returned from stopping to recording")
        reasons.append("retained output has an accurate terminal status")
    return _result(decision, reasons, rejected, preserved, questions)
