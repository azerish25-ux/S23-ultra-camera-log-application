"""Host checks for the P018 capture-state reducer. Not a physical S23 probe.

TC-P018-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p018_implement_the_capture_state_reducer import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    LOG_KEYS,
    METHOD,
    MUTANT,
    ORACLE,
    RESULT_KEYS,
    STATES,
    assess,
    initial_state,
    reduce_event,
    replay,
    validate_fixture,
)


def load_fixture() -> dict:
    path = ROOT / "docs" / "P018_IMPLEMENT_THE_CAPTURE_STATE_REDUCER.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ev(etype: str, **overrides) -> dict:
    event = {
        "type": etype,
        "generation": 1,
        "owner": "session-a",
        "delayed": False,
    }
    event.update(overrides)
    return event


def startup() -> list[dict]:
    return [
        ev("camera_opened"),
        ev("configure"),
        ev("configured"),
    ]


class P018CaptureReducerTests(unittest.TestCase):
    def test_fixture_identity_matches_the_phase_contract(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_fixture(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P018")
        self.assertEqual(raw["logId"], "s23-capture-reducer-record-stop-race")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["states"], list(STATES))
        self.assertEqual(raw["takeId"], "take-1")
        self.assertEqual(
            [item["type"] for item in raw["events"]],
            [
                "camera_opened",
                "configure",
                "configured",
                "record",
                "stop",
                "first_video_sample",
                "audio_format",
                "finalize",
                "finalized",
            ],
        )
        self.assertTrue(raw["events"][5]["delayed"])
        self.assertTrue(raw["events"][6]["delayed"])
        self.assertTrue(all(item["generation"] == 1 for item in raw["events"]))

    def test_record_then_stop_never_returns_to_recording(self) -> None:
        raw = load_fixture()
        before = copy.deepcopy(raw)
        state = initial_state(raw["takeId"])
        seen_recording = False
        for event in raw["events"]:
            state = reduce_event(state, event)
            if state["recording"]:
                seen_recording = True
            if event["type"] == "first_video_sample":
                self.assertEqual(state["state"], "stopping")
                self.assertFalse(state["recording"])
                self.assertFalse(state["timerRunning"])
                self.assertFalse(state["indicatorActive"])
                self.assertTrue(state["lateFirstVideoSample"])
                self.assertNotIn("stopping->recording", state["transitions"])
            if event["type"] == "audio_format":
                self.assertEqual(state["state"], "stopping")
                self.assertFalse(state["recording"])
                self.assertTrue(state["lateAudioFormat"])
        self.assertFalse(seen_recording)
        self.assertFalse(state["returnedFromStoppingToRecording"])
        self.assertEqual(
            state["transitions"],
            [
                "opening->preview",
                "preview->configuring",
                "configuring->preview",
                "preview->starting",
                "starting->stopping",
                "stopping->finalizing",
            ],
        )
        self.assertEqual(state["state"], "finalizing")
        retained = state["retainedOutput"]
        self.assertEqual(
            retained,
            {
                "takeId": "take-1",
                "status": "stopped_before_first_sample",
                "recordingEntered": False,
                "lateFirstVideoSample": True,
                "lateAudioFormat": True,
                "returnedToRecording": False,
            },
        )
        self.assertEqual(tuple(state["eventLog"][0]), LOG_KEYS)
        self.assertEqual([item["type"] for item in state["eventLog"]], [item["type"] for item in raw["events"]])
        result = assess(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P018")
        self.assertEqual(result["decision"], "terminal_accurate")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("take-1", result["preservedResults"])
        self.assertIn("5:stop", result["preservedResults"])
        self.assertIn("6:first_video_sample", result["preservedResults"])
        self.assertIn("7:audio_format", result["preservedResults"])
        self.assertIn("status:stopped_before_first_sample", result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertEqual(raw, before)

    def test_mutant_first_frame_callback_is_rejected(self) -> None:
        """This fails if the production reducer lets any first frame set recording=true."""
        raw = load_fixture()
        state = initial_state("take-1")
        for event in raw["events"]:
            state = reduce_event(state, event)
            if event["type"] in {"first_video_sample", "first_sample_ack"}:
                self.assertFalse(state["recording"])
                self.assertNotEqual(state["state"], "recording")
        mutated = replay(raw["events"], mutant=True, take_id="take-1")
        self.assertTrue(mutated["recording"])
        self.assertTrue(mutated["returnedFromStoppingToRecording"])
        self.assertIn("stopping->recording", mutated["transitions"])
        assessed = assess(raw, mutant=True)
        self.assertEqual(assessed["decision"], "rejected")
        self.assertNotIn(assessed["decision"], {"qualified", "allowed"})
        self.assertIn("first-frame-sets-recording", assessed["rejectedClaims"])
        self.assertIn("stopping-returned-to-recording", assessed["rejectedClaims"])
        self.assertIn("take-1", assessed["preservedResults"])
        self.assertIn("6:first_video_sample", assessed["preservedResults"])
        self.assertIn("7:audio_format", assessed["preservedResults"])
        correct = assess(raw, mutant=False)
        self.assertEqual(correct["decision"], "terminal_accurate")
        self.assertFalse(replay(raw["events"], take_id="take-1")["recording"])

    def test_first_sample_ack_is_required_before_timer_and_indicator(self) -> None:
        events = startup() + [ev("record"), ev("first_video_sample", delayed=True)]
        state = replay(events)
        self.assertEqual(state["state"], "starting")
        self.assertFalse(state["recording"])
        self.assertFalse(state["timerRunning"])
        self.assertFalse(state["indicatorActive"])
        self.assertFalse(state["firstSampleAcknowledged"])
        state = reduce_event(state, ev("first_sample_ack"))
        self.assertEqual(state["state"], "recording")
        self.assertTrue(state["recording"])
        self.assertTrue(state["timerRunning"])
        self.assertTrue(state["indicatorActive"])
        self.assertTrue(state["firstSampleAcknowledged"])

    def test_late_ack_during_stopping_does_not_resume(self) -> None:
        events = startup() + [
            ev("record"),
            ev("stop"),
            ev("first_sample_ack", delayed=True),
            ev("audio_format", delayed=True),
        ]
        state = replay(events)
        self.assertEqual(state["state"], "stopping")
        self.assertFalse(state["recording"])
        self.assertFalse(state["timerRunning"])
        self.assertFalse(state["indicatorActive"])
        self.assertNotIn("stopping->recording", state["transitions"])

    def test_acknowledged_recording_stops_without_returning(self) -> None:
        events = startup() + [
            ev("record"),
            ev("first_sample_ack"),
            ev("stop"),
            ev("first_video_sample", delayed=True),
            ev("audio_format", delayed=True),
            ev("finalize"),
            ev("finalized"),
        ]
        state = replay(events, take_id="take-acked")
        self.assertEqual(state["state"], "finalizing")
        self.assertFalse(state["recording"])
        self.assertFalse(state["returnedFromStoppingToRecording"])
        self.assertEqual(state["retainedOutput"]["takeId"], "take-acked")
        self.assertEqual(state["retainedOutput"]["status"], "stopped")
        self.assertTrue(state["retainedOutput"]["recordingEntered"])
        self.assertFalse(state["retainedOutput"]["returnedToRecording"])
        self.assertTrue(state["retainedOutput"]["lateFirstVideoSample"])
        self.assertTrue(state["retainedOutput"]["lateAudioFormat"])

    def test_stale_generation_releases_only_its_own_resources(self) -> None:
        events = [
            ev(
                "camera_opened",
                generation=1,
                owner="session-a",
                hold=["surface-old"],
                surface="surface-old",
            ),
            ev(
                "generation_advanced",
                generation=2,
                owner="session-b",
                surface="surface-new",
            ),
            ev(
                "first_video_sample",
                generation=1,
                owner="session-a",
                delayed=True,
                release=["surface-old", "surface-new"],
                surface="surface-old",
            ),
        ]
        state = replay(events)
        self.assertEqual(state["state"], "preview")
        self.assertEqual(state["generation"], 2)
        self.assertEqual(state["owner"], "session-b")
        self.assertFalse(state["recording"])
        self.assertEqual(state["attachedSurface"], "surface-new")
        self.assertIn("surface-old", state["released"])
        self.assertNotIn("surface-old", state["resources"])
        self.assertEqual(state["resources"].get("surface-new"), 2)
        self.assertTrue(state["eventLog"][-1]["stale"])
        self.assertFalse(state["eventLog"][-1]["applied"])
        self.assertEqual(state["eventLog"][-1]["generation"], 1)

    def test_failure_releases_current_resources_and_keeps_a_terminal_status(self) -> None:
        events = startup() + [ev("record"), ev("fail", hold=[])]
        state = replay([ev("camera_opened", hold=["camera-a"]), ev("fail")])
        self.assertEqual(state["state"], "failure")
        self.assertFalse(state["recording"])
        self.assertIn("camera-a", state["released"])
        self.assertEqual(state["retainedOutput"]["status"], "failed")
        self.assertFalse(state["retainedOutput"]["recordingEntered"])
        self.assertNotIn(events[0]["type"], {"qualified", "allowed"})

    def test_invalid_fixture_and_events_raise(self) -> None:
        valid = load_fixture()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["oracle"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P017"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        schema = copy.deepcopy(valid)
        schema["schemaVersion"] = True
        reordered = copy.deepcopy(valid)
        reordered["events"][4], reordered["events"][5] = reordered["events"][5], reordered["events"][4]
        for sample in (None, [], {}, extra, missing, wrong_phase, bad_revision, schema, reordered):
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(sample)
        state = initial_state()
        with self.assertRaises(ValueError):
            reduce_event(state, {"type": "record", "generation": 1})
        with self.assertRaises(ValueError):
            reduce_event(state, ev("record", generation=True))
        with self.assertRaises(ValueError):
            reduce_event(state, ev("nope"))
        with self.assertRaises(ValueError):
            assess(valid, mutant="true")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
