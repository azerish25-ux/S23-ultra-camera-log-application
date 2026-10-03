"""TC-P061-08 consumer round-trip discrepancy."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p061_tc08", Path(__file__).resolve().parents[1] / "gates" / "p061_tc08.py"
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
        "consumerVersion": "1.4.2",
        "rangeSetting": "video",
        "expectedRange": "video",
        "sidecar": "present",
        "numericDelta": "0.02",
        "tolerance": "0.001",
        "visualMatch": False,
        "fileOpened": True,
    }
    base.update(overrides)
    return base


class TcP06108(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P061-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("independent consumer", _MODULE.INTERVENTION)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Successful file opening alone must not count as interoperability.",
        )
        self.assertIn("consumer versions", _MODULE.REPEAT)
        self.assertIn("sidecar", _MODULE.REPEAT)

    def test_opening_alone_is_not_interoperability(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("open-is-not-interoperability", result["rejectedClaims"])
        self.assertIn("numeric-discrepancy", result["rejectedClaims"])
        self.assertIn("visual-discrepancy", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("opened:true", result["preservedResults"])
        self.assertIn("consumer:1.4.2", result["preservedResults"])
        self.assertIn("delta:0.02", result["preservedResults"])
        self.assertIn("tolerance:0.001", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_match_inside_tolerance_is_not_qualification(self):
        result = evaluate(payload(numericDelta="0.001", visualMatch=True))
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("consumer:1.4.2", result["preservedResults"])
        self.assertIn("delta:0.001", result["preservedResults"])
        self.assertTrue(any("not a consumer interoperability certificate" in item for item in result["openQuestions"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_consumer_version(self):
        result = evaluate(payload(consumerVersion="2.0.0"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("consumer:2.0.0", result["preservedResults"])
        self.assertIn("opened:true", result["preservedResults"])
        self.assertIn("open-is-not-interoperability", result["rejectedClaims"])

    def test_repeat_range_setting(self):
        result = evaluate(payload(rangeSetting="full", numericDelta="0", visualMatch=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("range-setting", result["rejectedClaims"])
        self.assertIn("range:full", result["preservedResults"])
        self.assertIn("expected-range:video", result["preservedResults"])
        self.assertIn("open-is-not-interoperability", result["rejectedClaims"])

    def test_repeat_sidecar_absent(self):
        result = evaluate(payload(sidecar="absent", numericDelta="0", visualMatch=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sidecar-unavailable", result["rejectedClaims"])
        self.assertIn("sidecar:absent", result["preservedResults"])
        self.assertIn("consumer:1.4.2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "tolerance": "0"},
            {**valid, "numericDelta": "-1"},
            {**valid, "fileOpened": 1},
            {**valid, "expectedRange": "mismatched"},
            {**valid, "consumerVersion": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
