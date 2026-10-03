"""Host checks for the P036 acquisition-only throughput fixture.

Not a physical S23 probe. TC-P036-01..08 are separate modules and are not
executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p036_build_the_acquisition_only_throughput_probe import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    recording_rate,
    sustained_rate,
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


def load_document() -> dict:
    return json.loads(
        (
            ROOT / "docs" / "P036_BUILD_THE_ACQUISITION_ONLY_THROUGHPUT_PROBE.json"
        ).read_text(encoding="utf-8")
    )


class P036AcquisitionThroughputTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P036")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P036")
        self.assertEqual(MAP_ID, "s23-acquisition-throughput-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("preallocated buffers", METHOD)
        self.assertIn("frames are not retained", METHOD)
        self.assertIn("saved-source throughput", METHOD)
        self.assertIn("final encoded", METHOD)
        self.assertEqual(
            FIXTURE,
            "A route delivering frames regularly when discarded but losing cadence when written "
            "to storage.",
        )
        self.assertEqual(
            ORACLE,
            "The report preserves the distinction and cannot claim the faster acquisition-only "
            "rate as reliable recorded RAW video.",
        )
        self.assertEqual(
            MUTANT,
            "Publish the best acquisition-only rate as the recording capability.",
        )

    def test_fixture_keeps_stages_separate_and_withholds_recording(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P036")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["publication"], "separated")
        self.assertIs(raw["stages"][0]["framesRetained"], False)
        self.assertEqual(raw["stages"][0]["cadence"], "regular")
        self.assertEqual(raw["stages"][1]["cadence"], "lost")
        self.assertIs(raw["stages"][1]["framesRetained"], True)
        self.assertEqual(raw["stages"][2]["cadence"], "absent")
        acq = sustained_rate(raw["stages"][0]["intervalsNs"])
        saved = sustained_rate(raw["stages"][1]["intervalsNs"])
        encoded = sustained_rate(raw["stages"][2]["intervalsNs"])
        self.assertEqual(acq, "100/1")
        self.assertEqual(saved, "40/3")
        self.assertEqual(encoded, "absent")
        self.assertEqual(recording_rate(raw), "withheld")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["acquisition-rate-as-recorded-raw"])
        self.assertEqual(result["caseId"], "P036")
        self.assertTrue(any(item.startswith("route:") for item in result["preservedResults"]))
        self.assertTrue(
            any(item.startswith("acquisition_only:") and "rate=100/1" in item
                and "retained=false" in item for item in result["preservedResults"])
        )
        self.assertTrue(
            any(item.startswith("saved_source:") and "rate=40/3" in item and "cadence=lost" in item
                for item in result["preservedResults"])
        )
        self.assertTrue(
            any(item.startswith("encoded:") and "rate=absent" in item
                for item in result["preservedResults"])
        )
        self.assertIn("recordingCapability:withheld", result["preservedResults"])
        self.assertNotIn("recordingCapability:100/1", result["preservedResults"])
        self.assertNotIn("recordingCapability:acquisition_only:100/1", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("acquisition_only frames are not retained", result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertEqual(
            result["openQuestions"],
            [
                "acquisition_only frames are not retained",
                "saved_source cadence lost when written to storage",
                "encoded performance absent",
                "not a physical S23 qualification",
            ],
        )

    def test_mutant_does_not_publish_acquisition_rate_as_recording(self) -> None:
        raw = load_document()
        raw["publication"] = "acquisition_as_recording"
        acq = sustained_rate(raw["stages"][0]["intervalsNs"])
        self.assertEqual(acq, "100/1")
        self.assertEqual(recording_rate(raw), "withheld")
        self.assertNotEqual(recording_rate(raw), acq)
        self.assertFalse(recording_rate(raw).startswith("acquisition_only"))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "stage_separated"})
        self.assertEqual(
            result["rejectedClaims"],
            ["acquisition-as-recording", "acquisition-rate-as-recorded-raw"],
        )
        self.assertIn("recordingCapability:withheld", result["preservedResults"])
        self.assertNotIn("recordingCapability:100/1", result["preservedResults"])
        self.assertTrue(any("rate=100/1" in item and item.startswith("acquisition_only:")
                            for item in result["preservedResults"]))
        self.assertTrue(any(item.startswith("saved_source:") for item in result["preservedResults"]))
        self.assertTrue(any(item.startswith("encoded:") for item in result["preservedResults"]))
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn(ORACLE, result["reasons"])

    def test_regular_saved_source_stays_distinct_from_acquisition(self) -> None:
        raw = load_document()
        saved = raw["stages"][1]
        saved["intervalsNs"] = ["50000000", "50000000", "50000000", "50000000"]
        saved["occupancy"] = ["1", "1", "1", "1"]
        saved["copyTimeNs"] = ["2000000", "2000000", "2000000", "2000000"]
        saved["cadence"] = "regular"
        saved["framesRetained"] = True
        self.assertEqual(sustained_rate(saved["intervalsNs"]), "20/1")
        self.assertEqual(recording_rate(raw), "saved_source:20/1")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "stage_separated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["acquisition-rate-as-recorded-raw"])
        self.assertIn("recordingCapability:saved_source:20/1", result["preservedResults"])
        self.assertNotIn("recordingCapability:100/1", result["preservedResults"])
        self.assertNotIn("recordingCapability:acquisition_only:100/1", result["preservedResults"])
        self.assertTrue(any("rate=100/1" in item and "retained=false" in item
                            for item in result["preservedResults"]))
        self.assertTrue(any("stage_separated is not physical qualification" in item
                            for item in result["reasons"]))

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["publication"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P035"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "abc"
        retained = copy.deepcopy(valid)
        retained["stages"][0]["framesRetained"] = True
        numeric = copy.deepcopy(valid)
        numeric["stages"][0]["intervalsNs"] = [10000000, 10000000, 10000000, 10000000]
        swapped = copy.deepcopy(valid)
        swapped["stages"][0]["cadence"] = "lost"
        empty = copy.deepcopy(valid)
        empty["stages"] = []
        encoded_retained = copy.deepcopy(valid)
        encoded_retained["stages"][2]["framesRetained"] = True
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            retained,
            numeric,
            swapped,
            empty,
            encoded_retained,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)


if __name__ == "__main__":
    unittest.main()
