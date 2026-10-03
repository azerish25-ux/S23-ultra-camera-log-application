"""TC-P013-02 advertisement is not a recording badge."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p013_tc02", Path(__file__).resolve().parents[1] / "gates" / "p013_tc02.py"
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
_TUPLE = "c2.android.hevc.encoder:Main10:surface:3840x2160"


def candidate(**overrides):
    base = {
        "candidateId": "hevc-main10-surface",
        "codecName": "c2.android.hevc.encoder",
        "profile": "Main10",
        "interface": "surface",
        "advertised": True,
        "configured": True,
        "samples": 0,
        "exactTuple": _TUPLE,
    }
    base.update(overrides)
    return base


class TcP01302(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P013-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"advertised_only", "sampled", "rejected"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)

    def test_configure_alone_is_not_a_recording_badge(self):
        result = evaluate({"candidate": candidate(), "failureMode": "none"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertIn("recording-badge", result["rejectedClaims"])
        self.assertIn(_TUPLE, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["advertised:hevc-main10-surface:Main10"])
        self.assertTrue(any("configure request alone" in item for item in result["reasons"]))
        self.assertTrue(any("historical" in item for item in result["reasons"]))

    def test_session_rejection_denies_the_exact_tuple(self):
        result = evaluate({"candidate": candidate(samples=0), "failureMode": "session_rejected"})
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertIn("session_rejected", result["rejectedClaims"])
        self.assertIn(_TUPLE, result["rejectedClaims"])
        self.assertIn("advertised:hevc-main10-surface:Main10", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sampled"})

    def test_startup_timeout_keeps_advertisement_only(self):
        result = evaluate(
            {"candidate": candidate(interface="image", exactTuple="image-tuple"), "failureMode": "startup_timeout"}
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertIn("startup_timeout", result["rejectedClaims"])
        self.assertIn("image-tuple", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["advertised:hevc-main10-surface:Main10"])

    def test_stream_mismatch_denies_operational_qualification(self):
        result = evaluate(
            {
                "candidate": candidate(configured=True, samples=4, exactTuple="mismatch-tuple"),
                "failureMode": "stream_mismatch",
            }
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "advertised_only")
        self.assertIn("stream_mismatch", result["rejectedClaims"])
        self.assertIn("mismatch-tuple", result["rejectedClaims"])
        self.assertNotIn("mismatch-tuple", result["preservedResults"])
        self.assertTrue(any("differs from the request" in item for item in result["reasons"]))

    def test_qualifying_samples_are_sampled_not_a_badge_for_other_tuples(self):
        result = evaluate(
            {"candidate": candidate(samples=8, configured=True), "failureMode": "none"}
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "sampled")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [_TUPLE, "advertised:hevc-main10-surface:Main10"])
        self.assertTrue(any("not a supported recording badge" in item for item in result["reasons"]))

    def test_unadvertised_candidate_is_rejected(self):
        result = evaluate(
            {"candidate": candidate(advertised=False, configured=True, samples=3), "failureMode": "none"}
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_TUPLE, result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "sampled"})

    def test_invalid_payload_raises(self):
        valid = {"candidate": candidate(), "failureMode": "none"}
        cases = [
            None,
            {},
            {**valid, "failureMode": "timeout"},
            {**valid, "candidate": candidate(samples=-1)},
            {**valid, "candidate": candidate(configured=1)},
            {**valid, "candidate": candidate(interface="hdmi")},
            {"candidate": candidate()},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
