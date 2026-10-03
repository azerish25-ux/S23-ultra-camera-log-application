"""TC-P063-08 consumer round-trip discrepancy."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p063_tc08", Path(__file__).resolve().parents[1] / "gates" / "p063_tc08.py"
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
        "consumerId": "independent-decoder",
        "version": "1.4.2",
        "rangeSetting": "video",
        "sidecarAvailable": True,
        "opened": True,
        "settingsApplied": False,
        "numericDelta": "0",
        "tolerance": "0.5",
        "visualMatch": True,
    }
    base.update(overrides)
    return base


class TcP06308(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P063-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Successful file opening alone must not count as interoperability.",
        )
        self.assertIn("tolerance", _MODULE.EXPECTED)

    def test_opening_alone_is_not_interoperability(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["open-is-not-interoperability"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("opened:true", result["preservedResults"])
        self.assertIn("version:1.4.2", result["preservedResults"])
        self.assertIn("delta:0", result["preservedResults"])
        self.assertIn("independent-decoder", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_repeat_exact_consumer_version_within_tolerance(self):
        result = evaluate(payload(settingsApplied=True, numericDelta="0.25", tolerance="0.5"))
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("version:1.4.2", result["preservedResults"])
        self.assertIn("delta:0.25", result["preservedResults"])
        self.assertIn("tolerance:0.5", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_range_setting(self):
        result = evaluate(payload(settingsApplied=True, rangeSetting="full"))
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertIn("range:full", result["preservedResults"])
        self.assertIn("version:1.4.2", result["preservedResults"])

    def test_repeat_missing_sidecar_is_withheld(self):
        result = evaluate(payload(settingsApplied=True, sidecarAvailable=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("sidecar:false", result["preservedResults"])
        self.assertIn("version:1.4.2", result["preservedResults"])
        self.assertIn("delta:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_delta_outside_tolerance_keeps_both_numbers(self):
        result = evaluate(payload(settingsApplied=True, numericDelta="2", tolerance="0.5", visualMatch=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["round-trip-discrepancy"])
        self.assertIn("delta:2", result["preservedResults"])
        self.assertIn("tolerance:0.5", result["preservedResults"])

    def test_unmeasured_version_is_withheld(self):
        result = evaluate(payload(settingsApplied=True, version="unmeasured"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("version:unmeasured", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "tolerance": "0"},
            {**valid, "numericDelta": "0.50"},
            {**valid, "rangeSetting": "legal"},
            {**valid, "opened": 1},
            {**valid, "version": ""},
            {k: v for k, v in valid.items() if k != "consumerId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
