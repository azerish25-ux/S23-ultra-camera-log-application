"""TC-P011-02 advertisement is not a recording badge."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p011_tc02", Path(__file__).resolve().parents[1] / "gates" / "p011_tc02.py"
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


def rate(numerator=15, denominator=1):
    return {"numerator": numerator, "denominator": denominator}


def payload(**overrides):
    base = {
        "candidateId": "rear-24",
        "advertised": True,
        "configured": True,
        "samples": 0,
        "failureMode": "none",
        "aeMin": rate(15),
        "aeMax": rate(30),
        "requestedFps": rate(24),
        "containerTimestampsAssigned": True,
    }
    base.update(overrides)
    return base


class TcP01102(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P011-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertTrue(result["reasons"])
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_encodes_intervention_expected_and_negative(self):
        self.assertIn("no qualifying samples", _MODULE.INTERVENTION)
        self.assertIn("historical evidence", _MODULE.EXPECTED)
        self.assertIn("recording badge", _MODULE.NEGATIVE)

    def test_configure_alone_is_not_a_recording_badge(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertIn("recording-badge", result["rejectedClaims"])
        self.assertIn("native-fixed-24", result["rejectedClaims"])
        self.assertIn("advertised:rear-24", result["preservedResults"])
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertTrue(any("not a recording badge" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_session_rejection_startup_timeout_and_stream_mismatch(self):
        expectations = {
            "session_rejected": "session rejection denies operational qualification",
            "startup_timeout": "startup timeout denies operational qualification",
            "stream_mismatch": "emitted stream differs from the request",
        }
        for mode, phrase in expectations.items():
            result = evaluate(payload(failureMode=mode, samples=0, configured=True))
            with self.subTest(mode=mode):
                self.assert_contract(result)
                self.assertEqual(result["decision"], "advertised_only")
                self.assertIn(mode, result["rejectedClaims"])
                self.assertIn("advertised:rear-24", result["preservedResults"])
                self.assertIn("ae:15/1-30/1", result["preservedResults"])
                self.assertTrue(any(phrase in item for item in result["reasons"]))
                self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_samples_do_not_become_native_fixed_24(self):
        result = evaluate(payload(samples=8, failureMode="none", containerTimestampsAssigned=True))
        self.assertEqual(result["decision"], "sampled")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "native_fixed_24"})
        self.assertEqual(result["rejectedClaims"], ["native-fixed-24"])
        self.assertIn("rear-24", result["preservedResults"])
        self.assertIn("requested:24/1", result["preservedResults"])

    def test_unadvertised_candidate_is_rejected_and_inventory_remains(self):
        result = evaluate(payload(advertised=False, configured=False, samples=0))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("rear-24", result["rejectedClaims"])
        self.assertIn("ae:15/1-30/1", result["preservedResults"])
        self.assertNotIn("advertised:rear-24", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "failureMode": "badge"},
            {**valid, "samples": -1},
            {**valid, "samples": True},
            {**valid, "candidateId": ""},
            {**valid, "aeMax": {"numerator": 2, "denominator": 2}},
            {**valid, "configured": "true"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
