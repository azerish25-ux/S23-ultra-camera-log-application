"""TC-P058-08 consumer round-trip discrepancy."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p058_tc08", Path(__file__).resolve().parents[1] / "gates" / "p058_tc08.py"
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
        "consumerVersion": "consumer-1.2",
        "documentedRange": "video",
        "consumerRange": "video",
        "sidecarAvailable": True,
        "fileOpened": True,
        "openedOnly": False,
        "numericDelta": "0.01",
        "visualDelta": "0.02",
        "numericTolerance": "0.03",
        "visualTolerance": "0.03",
    }
    base.update(overrides)
    return base


class TcP05808(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P058-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("consumer:consumer-1.2", result["preservedResults"])

    def test_within_tolerance_is_not_qualification(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "within_tolerance")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("numeric:0.01/0.03", result["preservedResults"])
        self.assertIn("visual:0.02/0.03", result["preservedResults"])
        self.assertTrue(any("not the interoperability certificate" in item for item in result["reasons"]))

    def test_negative_opening_alone_is_not_interoperability(self):
        result = evaluate(payload(openedOnly=True, fileOpened=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("open-is-not-interop", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("opened:true", result["preservedResults"])
        self.assertIn("numeric:0.01/0.03", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "within_tolerance"})

    def test_repeat_exact_consumer_version(self):
        result = evaluate(payload(consumerVersion="consumer-2.0", numericDelta="0.05"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("out-of-tolerance", result["rejectedClaims"])
        self.assertIn("consumer:consumer-2.0", result["preservedResults"])
        self.assertIn("numeric:0.05/0.03", result["preservedResults"])
        self.assertIn("sidecar:present", result["preservedResults"])

    def test_repeat_range_setting_and_missing_sidecar(self):
        ranged = evaluate(payload(consumerRange="full"))
        self.assertEqual(ranged["decision"], "rejected")
        self.assertIn("range-setting", ranged["rejectedClaims"])
        self.assertIn("documented-range:video", ranged["preservedResults"])
        self.assertIn("consumer-range:full", ranged["preservedResults"])
        missing = evaluate(payload(sidecarAvailable=False, consumerVersion="consumer-2.0"))
        self.assertEqual(missing["decision"], "rejected")
        self.assertIn("sidecar-unavailable", missing["rejectedClaims"])
        self.assertIn("sidecar:absent", missing["preservedResults"])
        self.assertIn("consumer:consumer-2.0", missing["preservedResults"])

    def test_closed_file_is_rejected_and_deltas_remain(self):
        result = evaluate(payload(fileOpened=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("file-not-opened", result["rejectedClaims"])
        self.assertIn("visual:0.02/0.03", result["preservedResults"])
        self.assertIn("opened:false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "consumerVersion"},
            {**valid, "extra": True},
            {**valid, "consumerVersion": ""},
            {**valid, "documentedRange": "legal"},
            {**valid, "numericDelta": "0.010"},
            {**valid, "openedOnly": "false"},
            {**valid, "fileOpened": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
