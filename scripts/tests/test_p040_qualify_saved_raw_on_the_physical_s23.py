"""Host checks for the P040 saved-RAW duration fixture. Not a physical S23 probe.

TC-P040-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p040_qualify_saved_raw_on_the_physical_s23 import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    still_token,
    take_token,
    validate_document,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
SHORT = (
    "take:raw-five-second:kind=raw_sequence:requested=5000:measured=5000:frames=150:"
    "complete=true:stop=requested_bound:integrity=intact:source=true:metadata=true:"
    "bandwidth=sufficient:thermal=nominal:lens=stable:retained=true"
)
LONG = (
    "take:raw-sixty-second:kind=raw_sequence:requested=60000:measured=17250:frames=410:"
    "complete=false:stop=severe_thermal:integrity=intact:source=false:metadata=true:"
    "bandwidth=sufficient:thermal=severe:lens=stable:retained=true"
)
STILL = "still:frames=5:kind=still_sequence"
LONGER = "retained-longer:raw-sixty-second:measured=17250"
INVENTORY = [
    "gates:acquisition=true:writer=true",
    SHORT,
    LONG,
    STILL,
    "maximum-resolution:attempted=false:conditional=true",
    LONGER,
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P040_QUALIFY_SAVED_RAW_ON_THE_PHYSICAL_S23.json").read_text(
            encoding="utf-8"
        )
    )


class P040SavedRawQualificationTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P040")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sustained_raw"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        self.assertTrue(result["preservedResults"])

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P040")
        self.assertEqual(MAP_ID, "s23-saved-raw-qualification-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("acquisition and writer gates", METHOD)
        self.assertIn("lens behaviour", METHOD)
        self.assertIn("maximum-resolution experiments conditional", METHOD)
        self.assertEqual(
            FIXTURE,
            "A five-second successful RAW sequence followed by a sixty-second run that stops "
            "under severe thermal pressure.",
        )
        self.assertEqual(
            ORACLE,
            "The app reports the measured duration boundaries and retains the longer partial "
            "take rather than extrapolating endurance.",
        )
        self.assertEqual(
            MUTANT,
            "Treat a five-frame still sequence as proof of sustained RAW video.",
        )

    def test_fixture_reports_measured_boundaries_and_keeps_the_partial(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P040")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "boundaries_reported")
        self.assertEqual(result["rejectedClaims"], ["endurance-extrapolation"])
        self.assertEqual(result["preservedResults"], INVENTORY)
        self.assertEqual(result["preservedResults"][1], take_token(raw["shortTake"]))
        self.assertEqual(result["preservedResults"][2], take_token(raw["longTake"]))
        self.assertEqual(result["preservedResults"][3], still_token(raw["stillSequence"]))
        self.assertIn(LONGER, result["preservedResults"])
        self.assertNotIn("measured=60000", result["preservedResults"][2])
        self.assertNotIn("sustained-raw-video", " ".join(result["preservedResults"]))
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("measured boundary raw-five-second 5000ms of 5000ms", result["reasons"])
        self.assertIn("measured boundary raw-sixty-second 17250ms of 60000ms", result["reasons"])
        self.assertIn("endurance was not extrapolated to 60000ms", result["reasons"])
        self.assertIn(
            "longer partial take raw-sixty-second retained at measured 17250ms",
            result["reasons"],
        )
        self.assertIn("boundaries_reported is not physical S23 qualification", result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertIn(
            "severe thermal stop is a measured bound, not an endurance certificate",
            result["openQuestions"],
        )
        self.assertNotIn(MUTANT, result["reasons"])
        note = (ROOT / "docs" / "P040_QUALIFY_SAVED_RAW_ON_THE_PHYSICAL_S23.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("host fixture", note)
        self.assertIn("python3 -m unittest discover -s scripts/tests -p 'test_p040*.py' -v", note)
        self.assertIn("Non-claims", note)
        self.assertIn("not a physical S23", note)

    def test_mutant_five_frame_still_is_rejected(self) -> None:
        raw = load_document()
        self.assertEqual(raw["stillSequence"]["frameCount"], "5")
        self.assertEqual(raw["stillSequence"]["kind"], "still_sequence")
        result = assess(raw, basis="five_frame_still")
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(
            result["decision"],
            {"qualified", "allowed", "boundaries_reported", "sustained_raw"},
        )
        self.assertEqual(
            result["rejectedClaims"],
            ["five-frame-still-as-sustained-raw-video", "endurance-extrapolation"],
        )
        self.assertEqual(result["preservedResults"], INVENTORY)
        self.assertIn(LONG, result["preservedResults"])
        self.assertIn(LONGER, result["preservedResults"])
        self.assertIn(STILL, result["preservedResults"])
        self.assertNotIn("sustained-raw-video", " ".join(result["preservedResults"]))
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn(
            "five still frames are not a sustained RAW video duration boundary",
            result["reasons"],
        )
        self.assertIn("endurance was not extrapolated to 60000ms", result["reasons"])
        self.assertIn(
            "five-frame still was not accepted as sustained RAW video",
            result["openQuestions"],
        )

    def test_mutant_still_rejects_when_the_short_take_succeeded(self) -> None:
        raw = load_document()
        self.assertTrue(raw["shortTake"]["complete"])
        self.assertEqual(raw["shortTake"]["measuredDurationMs"], "5000")
        result = assess(raw, basis="five_frame_still")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("five-frame-still-as-sustained-raw-video", result["rejectedClaims"])
        self.assertIn(SHORT, result["preservedResults"])
        self.assertNotEqual(result["decision"], "boundaries_reported")

    def test_failed_writer_gate_withholds_without_erasing_takes(self) -> None:
        raw = load_document()
        raw["gates"]["writerPassed"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "boundaries_reported"})
        self.assertIn("endurance-extrapolation", result["rejectedClaims"])
        self.assertIn("gates:acquisition=true:writer=false", result["preservedResults"])
        self.assertIn(LONG, result["preservedResults"])
        self.assertIn(LONGER, result["preservedResults"])
        self.assertIn("longer experiments require acquisition and writer gates", result["reasons"])
        self.assertIn("acquisition and writer gates have not both passed", result["openQuestions"])

    def test_discarded_partial_is_rejected_and_still_inventoried(self) -> None:
        raw = load_document()
        raw["longTake"]["retained"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("discarded-partial-take", result["rejectedClaims"])
        self.assertIn("endurance-extrapolation", result["rejectedClaims"])
        self.assertIn("retained=false", result["preservedResults"][2])
        self.assertIn("retained-longer:absent", result["preservedResults"])
        self.assertIn("the longer partial take was not retained", result["reasons"])
        self.assertIn("measured=17250", result["preservedResults"][2])

    def test_maximum_resolution_before_lower_cost_is_rejected(self) -> None:
        raw = load_document()
        raw["maximumResolution"]["attempted"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("maximum-resolution-before-lower-cost", result["rejectedClaims"])
        self.assertIn(LONGER, result["preservedResults"])
        self.assertIn("maximum-resolution:attempted=true:conditional=true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "boundaries_reported"})

    def test_corrupt_samples_withhold_the_boundary_report(self) -> None:
        raw = load_document()
        raw["longTake"]["sampleIntegrity"] = "corrupt"
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("sample-integrity", result["rejectedClaims"])
        self.assertIn("integrity=corrupt", result["preservedResults"][2])
        self.assertIn(LONGER, result["preservedResults"])
        self.assertIn("sample integrity is not intact", result["openQuestions"])

    def test_completed_sixty_seconds_is_not_this_thermal_boundary(self) -> None:
        raw = load_document()
        raw["longTake"].update(
            {
                "measuredDurationMs": "60000",
                "frameCount": "1800",
                "complete": True,
                "stoppedReason": "requested_bound",
                "sourceComplete": True,
                "thermalState": "warm",
            }
        )
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "boundaries_reported"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("measured=60000", result["preservedResults"][2])
        self.assertIn("retained-longer:absent", result["preservedResults"])
        self.assertIn(
            "measured records do not form the five-second then thermal-stop boundary",
            result["reasons"],
        )
        self.assertIn("a completed requested bound is not an endurance extrapolation", result["reasons"])

    def test_missing_metadata_keeps_durations_and_withholds(self) -> None:
        raw = load_document()
        raw["shortTake"]["metadataAvailable"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("metadata=false", result["preservedResults"][1])
        self.assertIn(LONG, result["preservedResults"])
        self.assertIn("metadata unavailable", result["openQuestions"])
        self.assertIn("endurance-extrapolation", result["rejectedClaims"])

    def test_invalid_documents_and_basis_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        short = copy.deepcopy(valid)
        short["shortTake"]["requestedDurationMs"] = "4000"
        still = copy.deepcopy(valid)
        still["stillSequence"]["frameCount"] = "6"
        kind = copy.deepcopy(valid)
        kind["stillSequence"]["kind"] = "raw_video"
        phase = copy.deepcopy(valid)
        phase["phase"] = "P039"
        unconditional = copy.deepcopy(valid)
        unconditional["maximumResolution"]["conditionalOnLowerCost"] = False
        same = copy.deepcopy(valid)
        same["longTake"]["id"] = same["shortTake"]["id"]
        thermal_complete = copy.deepcopy(valid)
        thermal_complete["longTake"]["complete"] = True
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            short,
            still,
            kind,
            phase,
            unconditional,
            same,
            thermal_complete,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, basis="five-frames")
        with self.assertRaises(ValueError):
            assess(valid, basis="qualified")


if __name__ == "__main__":
    unittest.main()
