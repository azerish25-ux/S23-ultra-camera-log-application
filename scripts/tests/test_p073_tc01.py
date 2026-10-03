"""TC-P073-01 stock identity without measurements."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p073_tc01", Path(__file__).resolve().parents[1] / "gates" / "p073_tc01.py"
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
        "stockName": "Vision 400",
        "modelKind": "generic",
        "measuredSamples": False,
        "label": "reconstructed",
        "interpretation": "daylight",
    }
    base.update(overrides)
    return base


class TcP07301(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P073-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("famous stock name", _MODULE.INTERVENTION)
        self.assertIn("marketing label", _MODULE.NEGATIVE)
        self.assertIn("daylight", _MODULE.REPEAT)
        self.assertIn("historical-stock", _MODULE.REPEAT)

    def test_daylight_name_stays_reconstructed(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "reconstructed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("Vision 400", result["preservedResults"])
        self.assertIn("interpretation:daylight", result["preservedResults"])
        self.assertIn("model:generic", result["preservedResults"])
        self.assertTrue(any("not a calibrated fidelity claim" in item for item in result["reasons"]))

    def test_tungsten_synthetic_label_is_kept(self):
        result = evaluate(payload(interpretation="tungsten", label="synthetic", modelKind="density"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "synthetic")
        self.assertIn("interpretation:tungsten", result["preservedResults"])
        self.assertIn("label:synthetic", result["preservedResults"])
        self.assertIn("Vision 400", result["preservedResults"])

    def test_marketing_label_does_not_establish_measured_behavior(self):
        result = evaluate(payload(interpretation="monochrome", label="measured"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["marketing-label"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("Vision 400", result["preservedResults"])
        self.assertIn("interpretation:monochrome", result["preservedResults"])
        self.assertIn("label:measured", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "measured_record", "reconstructed"})

    def test_historical_stock_repeat_stays_reconstructed(self):
        result = evaluate(payload(interpretation="historical-stock"))
        self.assertEqual(result["decision"], "reconstructed")
        self.assertIn("interpretation:historical-stock", result["preservedResults"])
        self.assertIn("samples:false", result["preservedResults"])

    def test_measured_samples_are_a_record_not_a_qualification(self):
        result = evaluate(payload(measuredSamples=True, label="measured", interpretation="daylight"))
        self.assertEqual(result["decision"], "measured_record")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("Vision 400", result["preservedResults"])
        self.assertIn("samples:true", result["preservedResults"])

    def test_label_sample_mismatch_is_rejected(self):
        result = evaluate(payload(measuredSamples=True, label="reconstructed"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["label-sample-mismatch"])
        self.assertIn("Vision 400", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "stockName"},
            {**valid, "extra": True},
            {**valid, "measuredSamples": "false"},
            {**valid, "label": "calibrated"},
            {**valid, "interpretation": "daylight-balance"},
            {**valid, "modelKind": "kodak"},
            {**valid, "stockName": " vision"},
            {**valid, "stockName": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
