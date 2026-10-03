"""TC-P073-05 overfit reference image."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p073_tc05", Path(__file__).resolve().parents[1] / "gates" / "p073_tc05.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def payload(**overrides):
    base = {
        "subject": "skin",
        "tunedFrame": "frame-01",
        "withheldExposure": True,
        "withheldScene": True,
        "favorableOnly": False,
        "generalizationFailed": True,
    }
    base.update(overrides)
    return base


class TcP07305(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P073-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("attractive frame", _MODULE.INTERVENTION)
        self.assertIn("single successful still", _MODULE.NEGATIVE)
        self.assertIn("foliage", _MODULE.REPEAT)
        self.assertIn("broad highlights", _MODULE.REPEAT)

    def test_skin_generalization_failure_is_reported(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "generalization_reported")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("subject:skin", result["preservedResults"])
        self.assertIn("frame-01", result["preservedResults"])
        self.assertIn("failed:true", result["preservedResults"])

    def test_foliage_repeat_reports_the_failure(self):
        result = evaluate(payload(subject="foliage", tunedFrame="frame-02"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "generalization_reported")
        self.assertIn("subject:foliage", result["preservedResults"])
        self.assertIn("frame-02", result["preservedResults"])

    def test_single_still_must_not_qualify_the_library(self):
        result = evaluate(
            payload(
                subject="night",
                generalizationFailed=False,
                withheldExposure=False,
                withheldScene=False,
                favorableOnly=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["favorable-only", "single-still"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("subject:night", result["preservedResults"])
        self.assertIn("frame-01", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "generalization_reported"})

    def test_highlights_held_out_success_is_withheld(self):
        result = evaluate(payload(subject="highlights", generalizationFailed=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("subject:highlights", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_fabric_favorable_selection_hides_a_reported_failure(self):
        result = evaluate(payload(subject="fabric", favorableOnly=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["favorable-only"])
        self.assertIn("subject:fabric", result["preservedResults"])
        self.assertIn("failed:true", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "subject"},
            {**valid, "extra": True},
            {**valid, "subject": "portrait"},
            {**valid, "tunedFrame": "frame 01"},
            {**valid, "favorableOnly": "true"},
            {**valid, "generalizationFailed": 0},
            {**valid, "withheldExposure": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
