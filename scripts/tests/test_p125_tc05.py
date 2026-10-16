"""Tests for TC-P125-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p125_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SOURCE = 8_000_000_000
INTERMEDIATE = 4_000_000_000
SAFETY = 250_000_000
RESERVE = SOURCE + INTERMEDIATE + SAFETY
FINAL = 1_500_000_000


def payload(**overrides):
    base = {
        "evidenceId": "p125-disk",
        "repeat": "before-rendering",
        "stage": "before-rendering",
        "source_bytes": SOURCE,
        "intermediate_estimate_bytes": INTERMEDIATE,
        "safety_bytes": SAFETY,
        "free_bytes": 20_000_000_000,
        "start_allowed": True,
        "delete_source": False,
        "frame_count": 100,
        "bytes_per_frame": 40_000_000,
        "final_output_bytes": FINAL,
        "budgeted_bytes": RESERVE,
    }
    base.update(overrides)
    return base


class TCP12505(unittest.TestCase):
    def assert_contract(self, result, evidence="p125-disk"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P125-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Temporary storage exhaustion")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Make remaining space insufficient for intermediate work or duplicate publication storage.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Budgeting only final output bytes must fail.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat before rendering, during chunk assembly, and during gallery publication.",
        )

    def test_full_reserve_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        kept = result["preservedResults"][1]
        self.assertEqual(kept["reserveBytes"], RESERVE)
        self.assertEqual(kept["headroomBytes"], 20_000_000_000 - RESERVE)
        self.assertEqual(kept["safety_bytes"], SAFETY)
        self.assertTrue(kept["recoverable"])
        self.assertIn("source-originals", kept["protected"])

    def test_short_space_pauses_without_deleting_the_source(self):
        result = evaluate(
            payload(
                evidenceId="p125-pause",
                repeat="chunk-assembly",
                stage="chunk-assembly",
                free_bytes=RESERVE - 10,
                start_allowed=False,
            )
        )
        self.assert_contract(result, "p125-pause")
        self.assertEqual(result["decision"], "recorded")
        self.assertLess(result["preservedResults"][1]["headroomBytes"], 0)
        self.assertTrue(result["preservedResults"][1]["startRefused"])
        self.assertTrue(result["preservedResults"][1]["recoverable"])

    def test_final_output_only_budget_is_rejected(self):
        result = evaluate(
            payload(
                repeat="gallery-publication",
                stage="gallery-publication",
                budgeted_bytes=FINAL,
                intermediate_estimate_bytes=0,
                start_allowed=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FINAL_ONLY, result["rejectedClaims"])
        self.assertIn("ignored-intermediates", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p125-disk", result["preservedResults"])
        self.assertNotEqual(result["preservedResults"][1]["reserveBytes"], FINAL)

    def test_delete_source_is_rejected(self):
        result = evaluate(payload(delete_source=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("delete-source", result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][1]["recoverable"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(safety_bytes=-5))
        with self.assertRaises(ValueError):
            evaluate(payload(stage="before-rendering", repeat="chunk-assembly"))
