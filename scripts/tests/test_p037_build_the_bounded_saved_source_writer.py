"""Host checks for the P037 bounded saved-source writer. Not a physical S23 probe.

TC-P037-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p037_build_the_bounded_saved_source_writer import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    WRITER_ID,
    assess,
    mutant_overwrite,
    record_token,
    simulate,
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
    path = ROOT / "docs" / "P037_BUILD_THE_BOUNDED_SAVED_SOURCE_WRITER.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P037BoundedWriterTests(unittest.TestCase):
    def assert_result(self, result: dict) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P037")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P037")
        self.assertEqual(WRITER_ID, "s23-bounded-raw-writer-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("fixed-capacity pool", METHOD)
        self.assertIn("replacement timestamps", METHOD)
        self.assertEqual(
            FIXTURE,
            "A source writer paused until the copy pool fills, then resumed after the capture "
            "controller has stopped.",
        )
        self.assertEqual(
            ORACLE,
            "All retained records remain ordered and intact, overflow is visible, and late "
            "completion cannot resume the failed take.",
        )
        self.assertEqual(
            MUTANT,
            "Overwrite the oldest queued source frame to keep a green recording indicator.",
        )

    def test_fixture_stops_with_ordered_records_and_visible_overflow(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P037")
        self.assertEqual(raw["writerId"], WRITER_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["policy"], "stop_on_full_pool")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "overflow_visible")
        self.assertEqual(
            result["preservedResults"][:5],
            [
                "r0@1000000000:aa00",
                "r1@1333333333:aa01",
                "r2@1666666666:aa02",
                "r3@2000000000:aa03",
                "r4@2333333333:aa04",
            ],
        )
        self.assertIn("sourceCount:3", result["preservedResults"])
        self.assertIn("flush:flush_on_stop", result["preservedResults"])
        self.assertIn("shortWrite:128", result["preservedResults"])
        self.assertIn("indicator:stopped", result["preservedResults"])
        self.assertEqual(
            result["rejectedClaims"],
            ["overflow:r3@2000000000:aa03", "late:r4@2333333333:aa04"],
        )
        self.assertIn("source count 3", result["reasons"])
        self.assertIn("flush policy flush_on_stop", result["reasons"])
        self.assertIn("short write 128", result["reasons"])
        self.assertIn("late completion cannot resume the failed take", result["reasons"])
        self.assertIn(ORACLE, result["reasons"])
        observed = simulate(raw)
        self.assertEqual([item["id"] for item in observed["written"]], ["r0", "r1", "r2"])
        self.assertEqual([item["timestampNs"] for item in observed["written"]],
                         ["1000000000", "1333333333", "1666666666"])
        self.assertEqual([item["digest"] for item in observed["written"]], ["aa00", "aa01", "aa02"])
        self.assertEqual(observed["sourceCount"], 3)
        self.assertTrue(observed["takeFailed"])
        self.assertEqual(observed["indicator"], "stopped")
        self.assertEqual(observed["shortWrites"], [{"bytes": 128, "policy": "flush_on_stop"}])
        self.assertNotIn("r4", [item["id"] for item in observed["written"]])
        self.assertNotIn("r3", [item["id"] for item in observed["written"]])

    def test_mutant_overwrite_oldest_is_rejected(self) -> None:
        raw = load_document()
        mutant = copy.deepcopy(raw)
        mutant["policy"] = "overwrite_oldest_keep_green"
        result = assess(mutant)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "overflow_visible"})
        self.assertEqual(
            result["rejectedClaims"],
            ["overwrite-oldest-keep-green", "green-recording-indicator"],
        )
        self.assertIn("r0@1000000000:aa00", result["preservedResults"])
        self.assertIn("r3@2000000000:aa03", result["preservedResults"])
        self.assertIn(MUTANT, result["reasons"])
        overwritten = mutant_overwrite(raw["records"], raw["poolCapacity"])
        self.assertEqual(overwritten["indicator"], "green")
        self.assertFalse(overwritten["acquisitionStopped"])
        self.assertEqual(overwritten["overflow"], [])
        self.assertEqual(overwritten["overwritten"][0]["id"], "r0")
        self.assertNotIn("r0", [item["id"] for item in overwritten["retained"]])
        self.assertIn("r0@1000000000:aa00", result["preservedResults"])
        joined = " ".join(result["preservedResults"])
        self.assertIn(record_token(raw["records"][0]), joined)

    def test_pool_that_does_not_overflow_is_withheld(self) -> None:
        raw = load_document()
        raw["records"] = [item for item in raw["records"] if item["id"] != "r3"]
        raw["script"] = [step for step in raw["script"] if step.get("recordId") != "r3"]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "overflow_visible"})
        self.assertIn("r0@1000000000:aa00", result["preservedResults"])
        self.assertIn("r4@2333333333:aa04", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_missing_flush_policy_keeps_the_inventory(self) -> None:
        raw = load_document()
        raw["flushPolicy"] = "none"
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-flush-policy", result["rejectedClaims"])
        self.assertIn("r0@1000000000:aa00", result["preservedResults"])
        self.assertIn("r3@2000000000:aa03", result["preservedResults"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["script"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P036"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        inverted = copy.deepcopy(valid)
        inverted["records"][0]["timestampNs"] = "3000000000"
        duplicate = copy.deepcopy(valid)
        duplicate["records"][1]["id"] = "r0"
        early = copy.deepcopy(valid)
        early["script"] = [
            {"op": "pause_writer"},
            {"op": "resume_writer"},
            {"op": "offer", "recordId": "r0"},
            {"op": "stop_controller"},
            {"op": "late_offer", "recordId": "r4"},
        ]
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            inverted,
            duplicate,
            early,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            simulate(copy.deepcopy(valid) | {"policy": "overwrite_oldest_keep_green"})


if __name__ == "__main__":
    unittest.main()
