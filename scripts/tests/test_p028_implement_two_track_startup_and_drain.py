"""Host checks for the P028 two-track mux. Not a physical S23 probe.

TC-P028-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p028_implement_two_track_startup_and_drain import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    assess_mux,
    ignores_later_selected_tracks,
    trace_mux,
    validate_fixture,
)


PARTIAL = "private-stage/take-p028.mp4"
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
HANDOFF_KEYS = (
    "phase",
    "caseIds",
    "changedFiles",
    "commit",
    "testsRun",
    "failures",
    "unverified",
    "nextPhase",
)


def load_fixture() -> dict:
    path = ROOT / "docs" / "P028_IMPLEMENT_TWO_TRACK_STARTUP_AND_DRAIN.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P028-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _event(index: int, kind: str, track: str, at_ms: int, fabricated: bool = False) -> dict:
    return {
        "index": index,
        "kind": kind,
        "track": track,
        "atMs": at_ms,
        "fabricated": fabricated,
    }


class P028TwoTrackStartupDrainTests(unittest.TestCase):
    def test_fixture_encodes_method_oracle_and_late_audio(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_fixture(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P028")
        self.assertEqual(raw["contractId"], "s23-two-track-startup-drain-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["muxPolicy"], "wait-for-all-formats")
        self.assertEqual(raw["drainPolicy"], "bounded")
        self.assertEqual(raw["selectedTracks"], ["video", "audio"])
        self.assertEqual(raw["maxPreStartSamples"], 3)
        self.assertEqual(raw["maxDrainDurationMs"], 1500)
        formats = [item for item in raw["events"] if item["kind"] == "format"]
        self.assertEqual([item["track"] for item in formats], ["video", "audio"])
        self.assertLess(formats[0]["atMs"], formats[1]["atMs"])
        stop = [item for item in raw["events"] if item["kind"] == "stop"]
        self.assertEqual(len(stop), 1)
        self.assertGreater(stop[0]["atMs"], formats[1]["atMs"])
        self.assertEqual(
            [item for item in raw["events"] if item["kind"] == "eos" and item["track"] == "audio"],
            [],
        )
        self.assertTrue(any(item["kind"] == "eos" and item["track"] == "video" for item in raw["events"]))
        pre = []
        for item in raw["events"]:
            if item["kind"] == "format" and item["track"] == "audio":
                break
            if item["kind"] == "sample":
                pre.append(item)
        self.assertEqual(len(pre), 2)
        self.assertLessEqual(len(pre), raw["maxPreStartSamples"])
        self.assertTrue(all(item["fabricated"] is False for item in raw["events"]))

    def test_stop_before_audio_eos_is_unverified_partial(self) -> None:
        raw = load_fixture()
        trace = trace_mux(raw)
        self.assertFalse(trace["earlyMux"])
        self.assertFalse(ignores_later_selected_tracks(raw))
        self.assertEqual(trace["muxStartMs"], 90)
        self.assertEqual(trace["formatsAtMux"], ["video", "audio"])
        self.assertEqual(trace["ignoredTracks"], [])
        self.assertEqual(trace["preStartSamples"], 2)
        self.assertEqual(trace["failedTracks"], ["audio"])
        self.assertFalse(trace["fabricatedAudio"])
        self.assertFalse(trace["deadlock"])
        result = assess_mux(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P028")
        self.assertEqual(result["decision"], "unverified_partial")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "protocol_complete"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][0], PARTIAL)
        self.assertIn("synthetic-two-track-p028", result["preservedResults"])
        self.assertIn("video", result["preservedResults"])
        self.assertIn("audio", result["preservedResults"])
        self.assertIn("failed:audio", result["preservedResults"])
        self.assertIn("video-samples:3", result["preservedResults"])
        self.assertIn("audio-samples:1", result["preservedResults"])
        self.assertTrue(any("unverified" in item for item in result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_mutant_start_on_first_track_is_rejected(self) -> None:
        raw = load_fixture()
        mutant = copy.deepcopy(raw)
        mutant["muxPolicy"] = "start-on-first-track"
        self.assertTrue(ignores_later_selected_tracks(mutant))
        trace = trace_mux(mutant)
        self.assertEqual(trace["muxStartMs"], 0)
        self.assertEqual(trace["formatsAtMux"], ["video"])
        self.assertEqual(trace["ignoredTracks"], ["audio"])
        result = assess_mux(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(
            result["decision"],
            {"qualified", "allowed", "protocol_complete", "unverified_partial"},
        )
        self.assertIn("mux-started-on-first-track", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], PARTIAL)
        self.assertIn("audio", result["preservedResults"])
        self.assertIn("failed:audio", result["preservedResults"])
        honest = assess_mux(raw)
        self.assertEqual(honest["decision"], "unverified_partial")
        self.assertNotEqual(result["decision"], honest["decision"])

    def test_ignoring_audio_eos_does_not_complete_the_take(self) -> None:
        raw = load_fixture()
        video_only = copy.deepcopy(raw)
        video_only["events"] = [
            item for item in video_only["events"] if item["track"] != "audio"
        ]
        for index, item in enumerate(video_only["events"]):
            item["index"] = index
        video_only["muxPolicy"] = "start-on-first-track"
        result = assess_mux(video_only)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "protocol_complete")
        self.assertIn("audio", result["preservedResults"])
        self.assertIn(PARTIAL, result["preservedResults"])

    def test_fabricated_audio_is_rejected_and_the_sample_is_kept(self) -> None:
        raw = load_fixture()
        mutant = copy.deepcopy(raw)
        mutant["events"][4]["fabricated"] = True
        result = assess_mux(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("fabricated-audio", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "protocol_complete"})
        self.assertIn("audio-samples:1", result["preservedResults"])
        self.assertIn(PARTIAL, result["preservedResults"])

    def test_both_eos_inside_the_bound_is_protocol_complete(self) -> None:
        raw = load_fixture()
        done = copy.deepcopy(raw)
        done["events"].append(_event(8, "eos", "audio", 400))
        result = assess_mux(done)
        self.assertEqual(result["decision"], "protocol_complete")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("failed:audio", result["preservedResults"])
        self.assertIn(PARTIAL, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_wait_forever_without_audio_eos_is_deadlock(self) -> None:
        raw = load_fixture()
        hung = copy.deepcopy(raw)
        hung["drainPolicy"] = "wait-forever"
        result = assess_mux(hung)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("deadlock", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "protocol_complete"})
        self.assertIn(PARTIAL, result["preservedResults"])
        self.assertIn("audio", result["preservedResults"])

    def test_pre_start_overflow_is_rejected_without_wiping_samples(self) -> None:
        raw = load_fixture()
        burst = copy.deepcopy(raw)
        extra = [
            _event(1, "sample", "video", 20),
            _event(2, "sample", "video", 40),
            _event(3, "sample", "video", 50),
            _event(4, "sample", "video", 60),
        ]
        tail = []
        for item in burst["events"]:
            if item["index"] == 0:
                tail.append(item)
            elif item["atMs"] >= 90:
                tail.append(item)
        burst["events"] = [tail[0], *extra, *tail[1:]]
        for index, item in enumerate(burst["events"]):
            item["index"] = index
        result = assess_mux(burst)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("pre-start-bound-exceeded", result["rejectedClaims"])
        self.assertIn("video-samples:5", result["preservedResults"])
        self.assertIn(PARTIAL, result["preservedResults"])

    def test_audio_eos_after_the_drain_bound_stays_partial(self) -> None:
        raw = load_fixture()
        late = copy.deepcopy(raw)
        late["events"].append(_event(8, "eos", "audio", 200 + 1500 + 1))
        result = assess_mux(late)
        self.assertEqual(result["decision"], "unverified_partial")
        self.assertIn("failed:audio", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "protocol_complete"})

    def test_invalid_fixtures_raise(self) -> None:
        valid = load_fixture()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P027"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "fffd5c9a63cb732e103052acae29ae0c251585cc"
        wrong_method = copy.deepcopy(valid)
        wrong_method["method"] = "start the muxer after the first track"
        empty = copy.deepcopy(valid)
        empty["events"] = []
        video_only = copy.deepcopy(valid)
        video_only["selectedTracks"] = ["video"]
        backwards = copy.deepcopy(valid)
        backwards["events"][2]["atMs"] = 10
        early_eos = copy.deepcopy(valid)
        early_eos["events"] = [
            _event(0, "eos", "video", 0),
        ]
        bad_policy = copy.deepcopy(valid)
        bad_policy["muxPolicy"] = "start-immediately"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            wrong_method,
            empty,
            video_only,
            backwards,
            early_eos,
            bad_policy,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(sample)

    def test_handoff_lists_cases_and_does_not_invent_a_commit(self) -> None:
        handoff = load_handoff()
        self.assertEqual(tuple(handoff), HANDOFF_KEYS)
        self.assertEqual(handoff["phase"], "P028")
        self.assertEqual(handoff["caseIds"], [f"TC-P028-0{index}" for index in range(1, 9)])
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(handoff["nextPhase"], "P029")
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p028*.py' -v",
            handoff["testsRun"],
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertIn("cinema-camera equivalence", handoff["unverified"])
        for relative in handoff["changedFiles"]:
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
