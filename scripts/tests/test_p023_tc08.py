"""TC-P023-08 redundant cleanup stays idempotent."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p023_tc08", Path(__file__).resolve().parents[1] / "gates" / "p023_tc08.py"
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
        "releaseCount": 0,
        "publicationCount": 0,
        "takeIds": ["take-empty"],
    }
    base.update(overrides)
    return base


class TcP02308(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P023-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("different orders", _MODULE.INTERVENTION)
        self.assertIn("single coherent terminal take identity", _MODULE.EXPECTED)
        self.assertIn("Double release", _MODULE.NEGATIVE)
        self.assertIn("empty_startup", _MODULE.CONTEXTS)
        self.assertIn("recovery_reopening", _MODULE.CONTEXTS)

    def test_empty_startup_cleanup_is_idempotent(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["take-empty"])
        self.assertTrue(any("stop,close" in item for item in result["reasons"]))
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_active_video_order_does_not_mint_a_second_take(self):
        forward = evaluate(
            payload(
                context="active_video",
                events=["stop", "detach", "close", "cancel"],
                releaseCount=1,
                publicationCount=1,
                takeIds=["take-video"],
            )
        )
        reverse = evaluate(
            payload(
                context="active_video",
                events=["detach", "cancel", "close", "stop"],
                releaseCount=1,
                publicationCount=1,
                takeIds=["take-video"],
            )
        )
        self.assert_contract(forward)
        self.assertEqual(forward["decision"], "idempotent")
        self.assertEqual(reverse["decision"], "idempotent")
        self.assertEqual(forward["preservedResults"], ["take-video"])
        self.assertEqual(reverse["preservedResults"], ["take-video"])
        self.assertNotEqual(
            next(item for item in forward["reasons"] if item.startswith("context")),
            next(item for item in reverse["reasons"] if item.startswith("context")),
        )
        self.assertNotIn(forward["decision"], {"qualified", "allowed"})

    def test_active_audiovisual_double_release_is_rejected(self):
        result = evaluate(
            payload(
                context="active_audiovisual",
                events=["stop", "stop", "close"],
                releaseCount=2,
                publicationCount=1,
                takeIds=["take-av"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "idempotent"})
        self.assertIn("double-release", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["take-av"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_duplicate_publication_and_second_take_are_rejected(self):
        result = evaluate(
            payload(
                context="recovery_reopening",
                events=["cancel", "detach", "close"],
                releaseCount=1,
                publicationCount=2,
                takeIds=["take-recovery", "take-cleanup"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-publication", result["rejectedClaims"])
        self.assertIn("second-take", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["take-recovery", "take-cleanup"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_missing_terminal_identity_is_rejected_without_inventing_a_take(self):
        result = evaluate(payload(context="empty_startup", takeIds=[]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-terminal-identity", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], ["empty_startup"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "context": "idle"},
            {**valid, "events": ["stop"]},
            {**valid, "events": ["stop", "publish"]},
            {**valid, "releaseCount": -1},
            {**valid, "releaseCount": True},
            {**valid, "takeIds": ["take-a", "take-a"]},
            {**valid, "publicationCount": 1.0},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
