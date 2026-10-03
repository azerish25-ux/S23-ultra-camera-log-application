"""TC-P071-08 misleading microbenchmark."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p071_tc08", Path(__file__).resolve().parents[1] / "gates" / "p071_tc08.py"
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
        "run": "cold",
        "kernelMs": "2",
        "endToEndMs": "18",
        "bottleneck": "readback",
        "reportedEndToEnd": True,
        "recordingClaim": False,
    }
    base.update(overrides)
    return base


class TcP07108(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P071-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("recording frame-rate", _MODULE.NEGATIVE)
        self.assertIn("thermally constrained", _MODULE.REPEAT)

    def test_end_to_end_is_reported_with_a_bottleneck(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "end_to_end_reported")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("run:cold", result["preservedResults"])
        self.assertIn("kernel-ms:2", result["preservedResults"])
        self.assertIn("end-to-end-ms:18", result["preservedResults"])
        self.assertIn("bottleneck:readback", result["preservedResults"])

    def test_recording_claim_from_kernel_time_fails(self):
        result = evaluate(payload(recordingClaim=True, reportedEndToEnd=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["recording-frame-rate-claim"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("kernel-ms:2", result["preservedResults"])
        self.assertIn("end-to-end-ms:18", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "end_to_end_reported"})

    def test_kernel_only_extrapolation_keeps_both_timings(self):
        result = evaluate(payload(reportedEndToEnd=False, bottleneck="none"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["kernel-extrapolation"])
        self.assertIn("kernel-ms:2", result["preservedResults"])
        self.assertIn("end-to-end-ms:18", result["preservedResults"])

    def test_repeat_warm_and_sustained(self):
        warm = evaluate(payload(run="warm", bottleneck="upload"))
        sustained = evaluate(payload(run="sustained", bottleneck="encode", endToEndMs="40"))
        self.assertEqual(warm["decision"], "end_to_end_reported")
        self.assertEqual(sustained["decision"], "end_to_end_reported")
        self.assertIn("run:warm", warm["preservedResults"])
        self.assertIn("run:sustained", sustained["preservedResults"])
        self.assertIn("end-to-end-ms:40", sustained["preservedResults"])

    def test_repeat_thermal(self):
        result = evaluate(payload(run="thermal", endToEndMs="90", bottleneck="encode"))
        self.assertEqual(result["decision"], "end_to_end_reported")
        self.assertIn("run:thermal", result["preservedResults"])
        self.assertIn("kernel-ms:2", result["preservedResults"])

    def test_missing_bottleneck_is_rejected(self):
        result = evaluate(payload(bottleneck="none"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["missing-bottleneck"])
        self.assertIn("end-to-end-ms:18", result["preservedResults"])
        self.assertIn("bottleneck:none", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "run": "hot"},
            {**valid, "kernelMs": "0"},
            {**valid, "endToEndMs": "18.0"},
            {**valid, "bottleneck": "gpu"},
            {**valid, "recordingClaim": "yes"},
            {k: v for k, v in valid.items() if k != "run"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
