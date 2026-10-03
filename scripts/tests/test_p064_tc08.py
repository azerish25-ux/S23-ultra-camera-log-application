"""TC-P064-08 consumer round-trip discrepancy."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p064_tc08", Path(__file__).resolve().parents[1] / "gates" / "p064_tc08.py"
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
        "consumer": "independent-decoder",
        "consumerVersion": "1.2.3",
        "rangeSetting": "video",
        "sidecarAvailable": True,
        "fileOpened": True,
        "numericDelta": "0.001",
        "visualDelta": "0.002",
        "numericTolerance": "0.01",
        "visualTolerance": "0.01",
        "documentedSettings": True,
    }
    base.update(overrides)
    return base


class TcP06408(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P064-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Successful file opening alone must not count as interoperability.",
        )
        self.assertIn("consumer versions", _MODULE.REPEAT)
        self.assertIn("sidecar", _MODULE.REPEAT)

    def test_within_tolerance_is_not_qualification(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("consumer:independent-decoder", result["preservedResults"])
        self.assertIn("version:1.2.3", result["preservedResults"])
        self.assertIn("numeric-delta:0.001", result["preservedResults"])
        self.assertIn("visual-delta:0.002", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_opening_alone_is_not_interoperability(self):
        result = evaluate(payload(documentedSettings=False, numericDelta="0", visualDelta="0"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("open-is-not-interoperable", result["rejectedClaims"])
        self.assertIn("settings-not-documented", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("opened:true", result["preservedResults"])
        self.assertIn("version:1.2.3", result["preservedResults"])
        self.assertIn("numeric-delta:0", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_outside_tolerance_keeps_the_deltas(self):
        result = evaluate(payload(numericDelta="0.2", visualDelta="0.3"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("outside-tolerance", result["rejectedClaims"])
        self.assertIn("open-is-not-interoperable", result["rejectedClaims"])
        self.assertIn("numeric-delta:0.2", result["preservedResults"])
        self.assertIn("visual-delta:0.3", result["preservedResults"])
        self.assertIn("numeric-tolerance:0.01", result["preservedResults"])

    def test_repeat_exact_consumer_version(self):
        result = evaluate(payload(consumerVersion="2.0.1", rangeSetting="full"))
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertIn("version:2.0.1", result["preservedResults"])
        self.assertIn("range:full", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_range_setting(self):
        video = evaluate(payload(rangeSetting="video"))
        full = evaluate(payload(rangeSetting="full"))
        unspecified = evaluate(payload(rangeSetting="unspecified"))
        self.assertEqual(video["decision"], "within_tolerance")
        self.assertEqual(full["decision"], "within_tolerance")
        self.assertIn("range:video", video["preservedResults"])
        self.assertIn("range:full", full["preservedResults"])
        self.assertEqual(unspecified["decision"], "rejected")
        self.assertIn("range-unspecified", unspecified["rejectedClaims"])
        self.assertIn("range:unspecified", unspecified["preservedResults"])
        self.assertNotIn(unspecified["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_repeat_sidecar_availability(self):
        present = evaluate(payload(sidecarAvailable=True))
        absent = evaluate(payload(sidecarAvailable=False))
        self.assertEqual(present["decision"], "within_tolerance")
        self.assertEqual(absent["decision"], "within_tolerance")
        self.assertIn("sidecar:true", present["preservedResults"])
        self.assertIn("sidecar:false", absent["preservedResults"])
        self.assertTrue(any("sidecar unavailable" in item for item in absent["openQuestions"]))
        self.assertIn("version:1.2.3", absent["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "numericDelta": "0.010"},
            {**valid, "numericDelta": "-1"},
            {**valid, "rangeSetting": "legal"},
            {**valid, "fileOpened": "yes"},
            {**valid, "consumerVersion": "1.2.3 "},
            {k: v for k, v in valid.items() if k != "visualTolerance"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
