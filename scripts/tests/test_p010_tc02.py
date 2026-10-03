"""TC-P010-02 advertised but unusable ordinary stream."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p010_tc02", Path(__file__).resolve().parents[1] / "gates" / "p010_tc02.py"
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
_FAILURES = ("session_rejected", "startup_timeout", "stream_mismatch")


def stream(**overrides):
    base = {
        "logicalId": "rear",
        "format": "RAW_SENSOR",
        "width": 4000,
        "height": 3000,
        "advertised": True,
        "configured": False,
        "samples": 0,
        "queryError": None,
    }
    base.update(overrides)
    return base


def _identity(item):
    return f"{item['width']}x{item['height']}:{item['format']}@{item['logicalId']}"


def _advertised(item):
    return f"advertised:{item['width']}x{item['height']}:{item['format']}"


class TcP01002(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P010-02")
        self.assertIn(result["decision"], {"advertised_only", "qualified", "rejected"})
        self.assertNotEqual(result["decision"], "allowed")
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_advertised_unconfigured_is_not_qualified(self):
        item = stream(advertised=True, configured=False, samples=0)
        result = evaluate({"stream": item, "failureMode": "none"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["no-samples"])
        self.assertIn("no-samples", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["advertised:4000x3000:RAW_SENSOR"])
        self.assertIn(_advertised(item), result["preservedResults"])
        self.assertEqual(result["openQuestions"], [])
        self.assertTrue(any("not operational qualification" in item for item in result["reasons"]))

    def test_configure_request_alone_is_not_a_recording_badge(self):
        item = stream(advertised=True, configured=True, samples=0, format="JPEG", width=8000, height=6000)
        result = evaluate({"stream": item, "failureMode": "none"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["no-samples"])
        self.assertEqual(result["preservedResults"], ["advertised:8000x6000:JPEG"])
        self.assertTrue(
            any(item == "configure request alone is not a recording badge" for item in result["reasons"])
        )
        self.assertNotIn(_identity(item), result["preservedResults"])

    def test_not_configured_with_samples_stays_advertised_only(self):
        item = stream(
            advertised=True,
            configured=False,
            samples=5,
            format="YUV_420_888",
            width=1920,
            height=1080,
        )
        result = evaluate({"stream": item, "failureMode": "none"})
        self.assertEqual(result["decision"], "advertised_only")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["no-samples"])
        self.assertEqual(result["preservedResults"], ["advertised:1920x1080:YUV_420_888"])

    def test_measured_stream_is_qualified_with_full_identity(self):
        item = stream(
            advertised=True,
            configured=True,
            samples=4,
            format="YUV_420_888",
            width=1920,
            height=1080,
            logicalId="rear",
        )
        result = evaluate({"stream": item, "failureMode": "none"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "qualified")
        identity = "1920x1080:YUV_420_888@rear"
        self.assertEqual(result["preservedResults"], [identity])
        self.assertIn("1920", identity)
        self.assertIn("1080", identity)
        self.assertIn("YUV_420_888", identity)
        self.assertIn("rear", identity)
        self.assertIn(str(item["width"]), result["preservedResults"][0])
        self.assertIn(str(item["height"]), result["preservedResults"][0])
        self.assertIn(item["format"], result["preservedResults"][0])
        self.assertIn(item["logicalId"], result["preservedResults"][0])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("advertised:1920x1080:YUV_420_888", result["preservedResults"])
        self.assertNotEqual(result["decision"], "allowed")

    def test_failure_modes_repeat_as_advertised_only(self):
        item = stream(
            advertised=True,
            configured=True,
            samples=8,
            format="RAW_SENSOR",
            width=4000,
            height=3000,
            logicalId="rear",
        )
        for mode in _FAILURES:
            result = evaluate({"stream": item, "failureMode": mode})
            with self.subTest(mode=mode):
                self.assertContract(result)
                self.assertEqual(result["decision"], "advertised_only")
                self.assertNotIn(result["decision"], {"qualified", "allowed"})
                self.assertEqual(result["rejectedClaims"], [mode])
                self.assertIn(mode, result["rejectedClaims"])
                self.assertEqual(result["preservedResults"], ["advertised:4000x3000:RAW_SENSOR"])
                self.assertIn(_advertised(item), result["preservedResults"])
                self.assertNotEqual(result["decision"], "qualified")

    def test_session_rejection_startup_timeout_and_stream_mismatch(self):
        expectations = {
            "session_rejected": "session rejection denies operational qualification",
            "startup_timeout": "startup timeout denies operational qualification",
            "stream_mismatch": "emitted stream differs from the request",
        }
        item = stream(advertised=True, configured=True, samples=2, format="JPEG", width=8000, height=6000)
        for mode, phrase in expectations.items():
            result = evaluate({"stream": item, "failureMode": mode})
            with self.subTest(mode=mode):
                self.assertEqual(result["decision"], "advertised_only")
                self.assertIn(mode, result["rejectedClaims"])
                self.assertTrue(any(phrase == reason for reason in result["reasons"]))
                self.assertIn("advertised:8000x6000:JPEG", result["preservedResults"])

    def test_samples_zero_with_failure_records_both_claims(self):
        item = stream(advertised=True, configured=True, samples=0)
        result = evaluate({"stream": item, "failureMode": "startup_timeout"})
        self.assertEqual(result["decision"], "advertised_only")
        self.assertEqual(result["rejectedClaims"], ["startup_timeout", "no-samples"])
        self.assertIn("startup_timeout", result["rejectedClaims"])
        self.assertIn("no-samples", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_unadvertised_configured_stream_is_rejected(self):
        item = stream(
            advertised=False,
            configured=True,
            samples=3,
            format="YUV_420_888",
            width=1920,
            height=1080,
            logicalId="front",
        )
        result = evaluate({"stream": item, "failureMode": "none"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "advertised_only"})
        self.assertEqual(result["rejectedClaims"], ["1920x1080:YUV_420_888@front"])
        self.assertEqual(result["preservedResults"], [])
        self.assertEqual(result["openQuestions"], [])

    def test_unadvertised_failure_is_not_qualified(self):
        item = stream(advertised=False, configured=True, samples=0, logicalId="wide")
        result = evaluate({"stream": item, "failureMode": "stream_mismatch"})
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["4000x3000:RAW_SENSOR@wide", "stream_mismatch", "no-samples"],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], [])

    def test_invalid_payload_raises(self):
        valid = stream(advertised=True, configured=True, samples=1)
        cases = [
            None,
            [],
            {},
            {"stream": valid},
            {"failureMode": "none"},
            {"stream": valid, "failureMode": "none", "extra": True},
            {"stream": valid, "failureMode": "timeout"},
            {"stream": valid, "failureMode": "NONE"},
            {"stream": valid, "failureMode": None},
            {"stream": valid, "failureMode": ""},
            {"stream": [valid], "failureMode": "none"},
            {"stream": {**valid, "lens": 50}, "failureMode": "none"},
            {"stream": {k: v for k, v in valid.items() if k != "samples"}, "failureMode": "none"},
            {"stream": {**valid, "logicalId": ""}, "failureMode": "none"},
            {"stream": {**valid, "logicalId": None}, "failureMode": "session_rejected"},
            {"stream": {**valid, "format": ""}, "failureMode": "none"},
            {"stream": {**valid, "width": 0}, "failureMode": "none"},
            {"stream": {**valid, "width": True}, "failureMode": "none"},
            {"stream": {**valid, "height": -1080}, "failureMode": "startup_timeout"},
            {"stream": {**valid, "height": 1080.0}, "failureMode": "none"},
            {"stream": {**valid, "advertised": "true"}, "failureMode": "none"},
            {"stream": {**valid, "configured": 0}, "failureMode": "none"},
            {"stream": {**valid, "samples": True}, "failureMode": "none"},
            {"stream": {**valid, "samples": -1}, "failureMode": "stream_mismatch"},
            {"stream": {**valid, "samples": 1.5}, "failureMode": "none"},
            {"stream": {**valid, "queryError": ""}, "failureMode": "none"},
            {"stream": {**valid, "queryError": 1}, "failureMode": "none"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
