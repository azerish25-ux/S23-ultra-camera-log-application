"""TC-P016-02 advertised but unusable route."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p016_tc02", Path(__file__).resolve().parents[1] / "gates" / "p016_tc02.py"
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
_ORACLE = ["file-retained", "playback:separate", "cadence:separate"]
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


class TcP01602(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P016-02")
        self.assertIn(result["decision"], {"advertised_only", "operational", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["openQuestions"], ["not-endurance-certified"])
        for token in _ORACLE:
            self.assertIn(token, result["preservedResults"])

    def test_contract_text_is_encoded(self):
        self.assertIn("no qualifying samples", _MODULE.INTERVENTION)
        self.assertIn("historical evidence", _MODULE.EXPECTED)
        self.assertIn("recording badge", _MODULE.NEGATIVE)

    def test_configure_request_alone_is_not_a_recording_badge(self):
        item = stream(advertised=True, configured=True, samples=0, format="JPEG", width=8000, height=6000)
        result = evaluate({"stream": item, "failureMode": "none"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "operational"})
        self.assertEqual(result["rejectedClaims"], ["no-samples"])
        self.assertEqual(result["preservedResults"], ["advertised:8000x6000:JPEG", *_ORACLE])
        self.assertTrue(
            any(reason == "configure request alone is not a recording badge" for reason in result["reasons"])
        )
        self.assertNotIn(_identity(item), result["preservedResults"])

    def test_session_rejection_denies_operational_qualification(self):
        item = stream(configured=True, samples=8, format="YUV_420_888", width=1920, height=1080)
        result = evaluate({"stream": item, "failureMode": "session_rejected"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertEqual(result["rejectedClaims"], ["session_rejected"])
        self.assertIn("advertised:1920x1080:YUV_420_888", result["preservedResults"])
        self.assertTrue(any("session rejection" in reason for reason in result["reasons"]))

    def test_startup_timeout_denies_operational_qualification(self):
        item = stream(configured=True, samples=8, format="JPEG", width=8000, height=6000)
        result = evaluate({"stream": item, "failureMode": "startup_timeout"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertIn("startup_timeout", result["rejectedClaims"])
        self.assertTrue(any("startup timeout" in reason for reason in result["reasons"]))
        self.assertIn(_advertised(item), result["preservedResults"])

    def test_emitted_stream_mismatch_denies_operational_qualification(self):
        item = stream(configured=True, samples=2, format="RAW_SENSOR", width=4000, height=3000)
        result = evaluate({"stream": item, "failureMode": "stream_mismatch"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertEqual(result["rejectedClaims"], ["stream_mismatch"])
        self.assertTrue(any("differs from the request" in reason for reason in result["reasons"]))
        self.assertIn(_advertised(item), result["preservedResults"])

    def test_failure_modes_repeat_as_advertised_only(self):
        item = stream(configured=True, samples=8)
        for mode in _FAILURES:
            result = evaluate({"stream": item, "failureMode": mode})
            with self.subTest(mode=mode):
                self.assertEqual(result["decision"], "advertised_only")
                self.assertNotIn(result["decision"], {"qualified", "allowed", "operational"})
                self.assertIn(mode, result["rejectedClaims"])
                self.assertIn(_advertised(item), result["preservedResults"])

    def test_configured_samples_are_operational_evidence_only(self):
        item = stream(
            advertised=True,
            configured=True,
            samples=4,
            format="YUV_420_888",
            width=1920,
            height=1080,
        )
        result = evaluate({"stream": item, "failureMode": "none"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "operational")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["1920x1080:YUV_420_888@rear", *_ORACLE])
        self.assertTrue(any("not a physical S23 qualification" in reason for reason in result["reasons"]))

    def test_zero_samples_with_timeout_records_both_claims(self):
        item = stream(configured=True, samples=0)
        result = evaluate({"stream": item, "failureMode": "startup_timeout"})
        self.assertEqual(result["decision"], "advertised_only")
        self.assertEqual(result["rejectedClaims"], ["startup_timeout", "no-samples"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_unadvertised_stream_is_rejected_but_the_take_remains(self):
        item = stream(advertised=False, configured=True, samples=3, format="YUV_420_888", width=1920, height=1080)
        result = evaluate({"stream": item, "failureMode": "none"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["1920x1080:YUV_420_888@rear"])
        self.assertEqual(result["preservedResults"], _ORACLE)

    def test_invalid_payload_raises(self):
        valid = stream(configured=True, samples=1)
        cases = [
            None,
            {},
            {"stream": valid},
            {"stream": valid, "failureMode": "timeout"},
            {"stream": {**valid, "samples": True}, "failureMode": "none"},
            {"stream": {**valid, "width": 0}, "failureMode": "none"},
            {"stream": valid, "failureMode": "none", "extra": True},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
