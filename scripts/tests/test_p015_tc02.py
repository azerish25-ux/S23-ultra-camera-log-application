"""TC-P015-02 advertisement is not a supported recording badge."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p015_tc02", Path(__file__).resolve().parents[1] / "gates" / "p015_tc02.py"
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
_TUPLE = "logical:0|3840x2160|hevc"
_HIST = "adv-hevc-main10"


def payload(**overrides):
    base = {
        "tupleId": _TUPLE,
        "advertised": True,
        "configured": True,
        "qualifyingSamples": 0,
        "failureMode": "none",
        "historicalAdvertisementId": _HIST,
    }
    base.update(overrides)
    return base


class TcP01502(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P015-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_contract_text(self):
        self.assertIn("no qualifying samples", _MODULE.INTERVENTION)
        self.assertIn("historical evidence", _MODULE.EXPECTED)
        self.assertIn("supported recording badge", _MODULE.NEGATIVE)
        self.assertIn("session rejection", _MODULE.REPEAT)

    def test_configure_request_alone_is_not_a_badge(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "historical_only")
        self.assertEqual(result["preservedResults"], [f"historical:{_HIST}"])
        self.assertIn(_TUPLE, result["rejectedClaims"])
        self.assertIn("supported-recording-badge", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "candidate"})
        self.assertTrue(any("configure request alone" in item for item in result["reasons"]))

    def test_session_rejection_denies_the_tuple(self):
        result = evaluate(payload(failureMode="session_rejection", qualifyingSamples=3))
        self.assertContract(result)
        self.assertEqual(result["decision"], "historical_only")
        self.assertIn("session_rejection", result["rejectedClaims"])
        self.assertIn(f"historical:{_HIST}", result["preservedResults"])
        self.assertTrue(any("session rejection" in item for item in result["reasons"]))

    def test_startup_timeout_and_stream_mismatch_repeat(self):
        for mode, needle in (
            ("startup_timeout", "startup timeout"),
            ("stream_differs", "emitted stream differs"),
        ):
            result = evaluate(payload(failureMode=mode, qualifyingSamples=4, configured=True))
            self.assertEqual(result["decision"], "historical_only")
            self.assertNotIn(result["decision"], {"qualified", "allowed"})
            self.assertIn(mode, result["rejectedClaims"])
            self.assertIn(f"historical:{_HIST}", result["preservedResults"])
            self.assertTrue(any(needle in item for item in result["reasons"]))

    def test_qualifying_samples_are_a_candidate_not_a_badge(self):
        result = evaluate(payload(qualifyingSamples=8, failureMode="none"))
        self.assertEqual(result["decision"], "candidate")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [f"historical:{_HIST}", _TUPLE])

    def test_unadvertised_tuple_is_rejected_but_not_deleted(self):
        result = evaluate(payload(advertised=False, configured=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["preservedResults"], [_TUPLE])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "failureMode": "thermal"},
            {**valid, "qualifyingSamples": -1},
            {**valid, "qualifyingSamples": True},
            {**valid, "configured": "yes"},
            {k: v for k, v in valid.items() if k != "tupleId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
