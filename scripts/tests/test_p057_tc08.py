"""TC-P057-08 opening a file is not consumer interoperability."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p057_tc08", Path(__file__).resolve().parents[1] / "gates" / "p057_tc08.py"
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
        "consumer": "ReferencePlayer",
        "version": "1.2.3",
        "rangeSetting": "full",
        "sidecar": "present",
        "numericDelta": "0.5",
        "tolerance": "0.02",
        "opened": True,
    }
    base.update(overrides)
    return base


class TcP05708(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P057-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_opening_with_a_large_delta_is_not_interoperability(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("file-open-is-not-interoperability", result["rejectedClaims"])
        self.assertIn("numeric-delta", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("consumer:ReferencePlayer", result["preservedResults"])
        self.assertIn("version:1.2.3", result["preservedResults"])
        self.assertIn("numeric-delta:0.5", result["preservedResults"])
        self.assertIn("opened:true", result["preservedResults"])

    def test_repeat_exact_consumer_version(self):
        result = evaluate(payload(consumer="OtherConsumer", version="2.0.0"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("version:2.0.0", result["preservedResults"])
        self.assertIn("consumer:OtherConsumer", result["preservedResults"])
        self.assertIn("numeric-delta:0.5", result["preservedResults"])

    def test_repeat_range_and_sidecar_settings(self):
        video = evaluate(payload(rangeSetting="video", numericDelta="0.01", tolerance="0.02"))
        self.assertEqual(video["decision"], "within_tolerance")
        self.assertIn("range:video", video["preservedResults"])
        self.assertEqual(video["rejectedClaims"], [])
        missing = evaluate(payload(sidecar="absent", numericDelta="0.01"))
        self.assertEqual(missing["decision"], "rejected")
        self.assertIn("sidecar-absent", missing["rejectedClaims"])
        self.assertIn("file-open-is-not-interoperability", missing["rejectedClaims"])
        self.assertIn("sidecar:absent", missing["preservedResults"])
        unspecified = evaluate(payload(rangeSetting="unspecified", numericDelta="0.01"))
        self.assertEqual(unspecified["decision"], "rejected")
        self.assertIn("range-unspecified", unspecified["rejectedClaims"])
        self.assertIn("range:unspecified", unspecified["preservedResults"])

    def test_closed_file_is_withheld(self):
        result = evaluate(payload(opened=False, numericDelta="0"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("opened:false", result["preservedResults"])
        self.assertIn("numeric-delta:0", result["preservedResults"])

    def test_match_within_tolerance_is_not_qualified(self):
        result = evaluate(payload(numericDelta="0.02", tolerance="0.02"))
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("tolerance:0.02", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "tolerance": "0"},
            {**valid, "numericDelta": "0.020"},
            {**valid, "rangeSetting": "legal"},
            {**valid, "opened": "yes"},
            {**valid, "version": ""},
            {k: v for k, v in valid.items() if k != "consumer"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
