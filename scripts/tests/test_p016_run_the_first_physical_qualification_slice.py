"""Host checks for the P016 first-slice report. Not a physical S23 probe.

TC-P016-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p016_run_the_first_physical_qualification_slice import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    assess_slice,
    validate_report,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
THERMAL = "single missing sample near thermal escalation"
STORAGE = "output file retained; storage headroom recorded"


def load_report() -> dict:
    path = ROOT / "docs" / "P016_RUN_THE_FIRST_PHYSICAL_QUALIFICATION_SLICE.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P016SliceTests(unittest.TestCase):
    def test_module_encodes_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(
            METHOD,
            "Choose one actually available rear route and conservative advertised configuration. "
            "Capture a controlled sixty-second take with a visible timing event and audio when supported. "
            "Decode it fully, inspect source and output metadata, and preserve thermal and storage observations.",
        )
        self.assertEqual(
            FIXTURE,
            "A real phone take with a single missing sample near thermal escalation "
            "and an otherwise playable output.",
        )
        self.assertEqual(
            ORACLE,
            "The file is retained, playback integrity and cadence receive separate statuses, "
            "and the mode is not endurance-certified.",
        )
        self.assertEqual(MUTANT, "Accept a mode after checking only the first decoded frame.")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")

    def test_fixture_is_a_host_report_not_a_device_probe(self) -> None:
        raw = load_report()
        self.assertIsNone(validate_report(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P016")
        self.assertEqual(raw["reportId"], "s23-first-physical-slice-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertIs(raw["hostFixture"], True)
        self.assertEqual(raw["route"], "rear")
        self.assertEqual(raw["configuration"], "conservative-advertised")
        self.assertEqual(raw["durationSec"], 60)
        self.assertIs(raw["timingEventVisible"], True)
        self.assertIs(raw["audioSupported"], True)
        self.assertIs(raw["audioPresent"], True)
        self.assertIs(raw["decodedFully"], True)
        self.assertIs(raw["fileRetained"], True)
        self.assertIs(raw["playable"], True)
        self.assertEqual(raw["missingSampleCount"], 1)
        self.assertIs(raw["missingSampleNearThermalEscalation"], True)
        self.assertEqual(raw["framesChecked"], "all")
        self.assertEqual(raw["playbackIntegrity"], "playable-with-gap")
        self.assertEqual(raw["cadenceStatus"], "withheld")
        self.assertNotEqual(raw["playbackIntegrity"], raw["cadenceStatus"])
        self.assertIs(raw["enduranceCertified"], False)
        self.assertIs(raw["firstFrameOnly"], False)
        self.assertEqual(raw["thermalObservation"], THERMAL)
        self.assertEqual(raw["storageObservation"], STORAGE)

    def test_authored_slice_is_reported_without_endurance_or_qualification(self) -> None:
        raw = load_report()
        before = copy.deepcopy(raw)
        result = assess_slice(raw)
        self.assertEqual(raw, before)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P016")
        self.assertEqual(result["decision"], "slice_reported")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "endurance-certified"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            [
                THERMAL,
                STORAGE,
                "playback:playable-with-gap",
                "cadence:withheld",
                "file-retained",
                "route:rear",
            ],
        )
        self.assertNotEqual(
            result["preservedResults"][2],
            result["preservedResults"][3],
        )
        self.assertIn(ORACLE, result["reasons"])
        self.assertTrue(any("single missing sample near thermal escalation" in item for item in result["reasons"]))
        self.assertEqual(
            result["openQuestions"],
            [
                "mode is not endurance-certified",
                "cadence withheld pending measured results",
                "endurance unqualified",
            ],
        )
        self.assertTrue(result["reasons"])

    def test_first_frame_only_mutant_is_rejected(self) -> None:
        mutant = load_report()
        mutant["firstFrameOnly"] = True
        mutant["framesChecked"] = "first"
        mutant["decodedFully"] = False
        result = assess_slice(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "slice_reported"})
        self.assertIn("first-frame-only", result["rejectedClaims"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertTrue(any("first decoded frame" in item for item in result["reasons"]))
        self.assertIn(THERMAL, result["preservedResults"])
        self.assertIn(STORAGE, result["preservedResults"])
        self.assertIn("playback:playable-with-gap", result["preservedResults"])
        self.assertIn("cadence:withheld", result["preservedResults"])
        self.assertIn("file-retained", result["preservedResults"])
        self.assertNotIn(ORACLE, result["reasons"])
        self.assertIn("mode is not endurance-certified", result["openQuestions"])

    def test_mutant_stays_rejected_when_the_first_frame_looks_perfect(self) -> None:
        mutant = load_report()
        mutant["firstFrameOnly"] = True
        mutant["framesChecked"] = "first"
        mutant["decodedFully"] = False
        mutant["missingSampleCount"] = 0
        mutant["missingSampleNearThermalEscalation"] = False
        mutant["playable"] = True
        mutant["playbackIntegrity"] = "playable"
        mutant["cadenceStatus"] = "measured"
        mutant["enduranceCertified"] = False
        result = assess_slice(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "slice_reported"})
        self.assertEqual(result["rejectedClaims"], ["first-frame-only"])
        self.assertIn("playback:playable", result["preservedResults"])
        self.assertIn("cadence:measured", result["preservedResults"])
        self.assertIn("measured cadence is not a fixed-cadence certificate", result["openQuestions"])

    def test_endurance_flag_is_rejected_and_observations_remain(self) -> None:
        claimed = load_report()
        claimed["enduranceCertified"] = True
        result = assess_slice(claimed)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "slice_reported"})
        self.assertIn("endurance-certified", result["rejectedClaims"])
        self.assertIn(THERMAL, result["preservedResults"])
        self.assertIn(STORAGE, result["preservedResults"])
        self.assertIn("file-retained", result["preservedResults"])
        self.assertTrue(any("endurance certification is rejected" in item for item in result["reasons"]))

    def test_dropped_file_is_rejected_without_wiping_observations(self) -> None:
        dropped = load_report()
        dropped["fileRetained"] = False
        result = assess_slice(dropped)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("file-not-retained", result["rejectedClaims"])
        self.assertIn("file-not-retained", result["preservedResults"])
        self.assertIn(THERMAL, result["preservedResults"])
        self.assertIn(STORAGE, result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_short_take_is_withheld_rather_than_reported(self) -> None:
        short = load_report()
        short["durationSec"] = 10
        result = assess_slice(short)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "slice_reported"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("sixty-second" in item for item in result["reasons"]))
        self.assertIn(THERMAL, result["preservedResults"])
        self.assertIn("take is not the controlled sixty-second slice", result["openQuestions"])

    def test_non_rear_route_is_withheld(self) -> None:
        front = load_report()
        front["route"] = "front"
        result = assess_slice(front)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("route:front", result["preservedResults"])
        self.assertIn(THERMAL, result["preservedResults"])
        self.assertTrue(any("rear route" in item for item in result["reasons"]))

    def test_audio_supported_but_missing_is_withheld(self) -> None:
        quiet = load_report()
        quiet["audioPresent"] = False
        result = assess_slice(quiet)
        self.assertEqual(result["decision"], "withheld")
        self.assertTrue(any("audio was supported but not captured" in item for item in result["reasons"]))
        self.assertIn(STORAGE, result["preservedResults"])

    def test_measured_cadence_stays_separate_and_is_not_a_certificate(self) -> None:
        measured = load_report()
        measured["cadenceStatus"] = "measured"
        result = assess_slice(measured)
        self.assertEqual(result["decision"], "slice_reported")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("playback:playable-with-gap", result["preservedResults"])
        self.assertIn("cadence:measured", result["preservedResults"])
        self.assertNotEqual(
            result["preservedResults"][result["preservedResults"].index("playback:playable-with-gap")],
            "cadence:measured",
        )
        self.assertIn("measured cadence is not a fixed-cadence certificate", result["openQuestions"])
        self.assertIn("endurance unqualified", result["openQuestions"])

    def test_unplayable_output_is_rejected_while_the_file_record_remains(self) -> None:
        bad = load_report()
        bad["playable"] = False
        bad["playbackIntegrity"] = "unplayable"
        result = assess_slice(bad)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("playback-failed", result["rejectedClaims"])
        self.assertIn("file-retained", result["preservedResults"])
        self.assertIn("playback:unplayable", result["preservedResults"])
        self.assertIn(THERMAL, result["preservedResults"])

    def test_invalid_reports_raise(self) -> None:
        valid = load_report()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["thermalObservation"]
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        not_host = copy.deepcopy(valid)
        not_host["hostFixture"] = False
        collapsed = copy.deepcopy(valid)
        collapsed["playbackIntegrity"] = "withheld"
        first_inconsistent = copy.deepcopy(valid)
        first_inconsistent["firstFrameOnly"] = True
        audio = copy.deepcopy(valid)
        audio["audioSupported"] = False
        float_duration = copy.deepcopy(valid)
        float_duration["durationSec"] = 60.0
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_revision,
            not_host,
            collapsed,
            first_inconsistent,
            audio,
            float_duration,
            {**valid, "phase": "P015"},
            {**valid, "schemaVersion": True},
            {**valid, "framesChecked": "some"},
            {**valid, "cadenceStatus": "playable"},
            {**valid, "missingSampleCount": 0},
            {**valid, "route": ""},
            {**valid, "enduranceCertified": 1},
            {**valid, "fileRetained": "true"},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_report(sample)


if __name__ == "__main__":
    unittest.main()
