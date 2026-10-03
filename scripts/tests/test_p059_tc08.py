"""TC-P059-08 consumer round-trip discrepancy."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p059_tc08", Path(__file__).resolve().parents[1] / "gates" / "p059_tc08.py"
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
        "consumer": "host-consumer",
        "consumerVersion": "1.2.3",
        "opened": True,
        "openOnly": False,
        "numericError": "0.001",
        "visualError": "0.002",
        "tolerance": "0.01",
        "rangeSetting": "full",
        "sidecar": "present",
        "repeat": "none",
    }
    base.update(overrides)
    return base


class TcP05908(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P059-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("consumer:host-consumer", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("independent consumer", _MODULE.INTERVENTION)
        self.assertIn("tolerance", _MODULE.EXPECTED)
        self.assertIn("file opening", _MODULE.NEGATIVE)

    def test_within_tolerance_is_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("version:1.2.3", result["preservedResults"])
        self.assertIn("numeric-error:0.001", result["preservedResults"])
        self.assertIn("visual-error:0.002", result["preservedResults"])
        self.assertIn("tolerance:0.01", result["preservedResults"])
        self.assertIn("range:full", result["preservedResults"])
        self.assertIn("sidecar:present", result["preservedResults"])

    def test_negative_open_alone_is_not_interoperability(self):
        result = evaluate(payload(openOnly=True, opened=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})
        self.assertEqual(result["rejectedClaims"], ["open-is-not-interoperable"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("opened:true", result["preservedResults"])
        self.assertIn("numeric-error:0.001", result["preservedResults"])

    def test_error_above_tolerance_keeps_both_errors(self):
        result = evaluate(payload(numericError="0.2", visualError="0.05"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["round-trip-mismatch"])
        self.assertIn("numeric-error:0.2", result["preservedResults"])
        self.assertIn("visual-error:0.05", result["preservedResults"])
        self.assertIn("tolerance:0.01", result["preservedResults"])

    def test_repeat_consumer_version(self):
        result = evaluate(payload(consumerVersion="9.9.9", repeat="consumer-version"))
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertIn("version:9.9.9", result["preservedResults"])
        self.assertNotIn("version:1.2.3", result["preservedResults"])
        self.assertIn("repeat:consumer-version", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_range_setting(self):
        result = evaluate(payload(rangeSetting="video", repeat="range-setting"))
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertIn("range:video", result["preservedResults"])
        self.assertIn("repeat:range-setting", result["preservedResults"])
        self.assertIn("sidecar:present", result["preservedResults"])

    def test_repeat_missing_sidecar_is_not_interoperability(self):
        result = evaluate(payload(sidecar="absent", repeat="sidecar"))
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})
        self.assertEqual(result["rejectedClaims"], ["incomplete-consumer-settings"])
        self.assertIn("sidecar:absent", result["preservedResults"])
        self.assertIn("numeric-error:0.001", result["preservedResults"])
        self.assertIn("repeat:sidecar", result["preservedResults"])

    def test_missing_range_is_withheld(self):
        result = evaluate(payload(rangeSetting="missing"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("range:missing", result["preservedResults"])
        self.assertIn("incomplete-consumer-settings", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "tolerance"},
            {**valid, "extra": True},
            {**valid, "numericError": "0.0010"},
            {**valid, "opened": 1},
            {**valid, "rangeSetting": "legal"},
            {**valid, "sidecar": "maybe"},
            {**valid, "repeat": "player"},
            {**valid, "consumer": ""},
            {**valid, "tolerance": "-1"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
