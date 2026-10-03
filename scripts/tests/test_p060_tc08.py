"""TC-P060-08 consumer round-trip discrepancy."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p060_tc08", Path(__file__).resolve().parents[1] / "gates" / "p060_tc08.py"
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
        "fileOpened": True,
        "rangeSetting": "limited",
        "expectedRange": "limited",
        "sidecar": "present",
        "numericDelta": "0.001",
        "tolerance": "0.01",
        "visualDelta": "0",
        "visualTolerance": "0.02",
    }
    base.update(overrides)
    return base


class TcP06008(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P060-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("file opening", _MODULE.NEGATIVE)
        self.assertIn("sidecar", _MODULE.REPEAT)

    def test_within_tolerance_matches_without_qualifying(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "matched")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("numeric:0.001/0.01", result["preservedResults"])
        self.assertIn("visual:0/0.02", result["preservedResults"])
        self.assertIn("version:1.2.3", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_open_file_outside_tolerance_is_not_interoperability(self):
        result = evaluate(payload(numericDelta="1.5"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("file-open-is-not-interoperability", result["rejectedClaims"])
        self.assertIn("outside-tolerance", result["rejectedClaims"])
        self.assertIn("numeric:1.5/0.01", result["preservedResults"])
        self.assertIn("opened:yes", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_repeat_consumer_version(self):
        result = evaluate(payload(consumerVersion="2.0.1"))
        self.assertEqual(result["decision"], "matched")
        self.assertIn("version:2.0.1", result["preservedResults"])
        self.assertIn("consumer:host-consumer", result["preservedResults"])

    def test_repeat_range_setting(self):
        result = evaluate(payload(rangeSetting="full"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("range-setting", result["rejectedClaims"])
        self.assertIn("range:full|limited", result["preservedResults"])
        self.assertIn("file-open-is-not-interoperability", result["rejectedClaims"])

    def test_repeat_missing_sidecar(self):
        result = evaluate(payload(sidecar="absent", numericDelta="0", visualDelta="0"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sidecar-unavailable", result["rejectedClaims"])
        self.assertIn("sidecar:absent", result["preservedResults"])
        self.assertIn("opened:yes", result["preservedResults"])

    def test_unopened_file_is_withheld(self):
        result = evaluate(payload(fileOpened=False, numericDelta="4"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("opened:no", result["preservedResults"])
        self.assertIn("numeric:4/0.01", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "numericDelta": "-1"},
            {**valid, "numericDelta": "0.010"},
            {**valid, "fileOpened": "yes"},
            {**valid, "sidecar": "maybe"},
            {**valid, "consumerVersion": "1 2"},
            {k: v for k, v in valid.items() if k != "tolerance"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
