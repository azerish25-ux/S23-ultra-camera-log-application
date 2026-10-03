"""TC-P024-08 repeated cleanup stays idempotent for one terminal take."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p024_tc08", Path(__file__).resolve().parents[1] / "gates" / "p024_tc08.py"
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
        "context": "empty_startup",
        "events": ["stop", "close"],
        "releaseCount": 1,
        "publicationCount": 1,
        "takeIds": ["take-empty"],
    }
    base.update(overrides)
    return base


class TcP02408(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P024-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("different orders", _MODULE.INTERVENTION)
        self.assertIn("idempotent", _MODULE.EXPECTED)
        self.assertIn("Double release", _MODULE.NEGATIVE)
        self.assertIn("empty_startup", _MODULE.CONTEXTS)
        self.assertIn("recovery_reopening", _MODULE.CONTEXTS)

    def test_empty_startup_stop_then_close_is_idempotent(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["take-empty"])
        self.assertTrue(any("empty_startup" in item for item in result["reasons"]))
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_active_video_cancel_and_detach_keeps_one_take(self):
        result = evaluate(
            payload(
                context="active_video",
                events=["cancel", "detach", "stop"],
                takeIds=["take-video"],
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], ["take-video"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(any("active_video" in item for item in result["reasons"]))

    def test_audiovisual_double_release_is_rejected(self):
        result = evaluate(
            payload(
                context="active_audiovisual",
                events=["stop", "close", "detach"],
                releaseCount=2,
                takeIds=["take-av"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "idempotent"})
        self.assertIn("double-release", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["take-av"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_recovery_reopening_second_take_and_republish_fail(self):
        result = evaluate(
            payload(
                context="recovery_reopening",
                events=["detach", "close"],
                publicationCount=2,
                takeIds=["take-a", "take-b"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-publication", result["rejectedClaims"])
        self.assertIn("second-take", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["take-a", "take-b"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_missing_terminal_identity_keeps_the_context(self):
        result = evaluate(payload(context="active_video", takeIds=[], events=["stop", "cancel"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-terminal-identity", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["active_video"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "context": "background"},
            {**valid, "events": ["stop"]},
            {**valid, "events": ["stop", "halt"]},
            {**valid, "releaseCount": -1},
            {**valid, "takeIds": ["take-empty", "take-empty"]},
            {**valid, "publicationCount": True},
            {key: value for key, value in valid.items() if key != "context"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
