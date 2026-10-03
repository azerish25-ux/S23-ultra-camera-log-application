"""TC-P022-08 repeated cleanup stays one terminal take."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p022_tc08", Path(__file__).resolve().parents[1] / "gates" / "p022_tc08.py"
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
_HASH = "cm-cleanup"


def payload(**overrides):
    base = {
        "context": "empty_startup",
        "events": ["stop", "close", "stop"],
        "takeId": "take-1",
        "doubleRelease": False,
        "duplicatePublication": False,
        "secondTakeCreated": False,
        "cleanMasterHash": _HASH,
    }
    base.update(overrides)
    return base


class TcP02208(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P022-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("different orders", _MODULE.INTERVENTION)
        self.assertIn("idempotent", _MODULE.EXPECTED)
        self.assertIn("second take", _MODULE.NEGATIVE)

    def test_empty_startup_repeat_stop_is_idempotent(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], ["take-1", _HASH])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("events stop,close,stop" in item for item in result["reasons"]))
        self.assertTrue(any("empty_startup" in item for item in result["reasons"]))

    def test_active_audiovisual_detach_order_keeps_the_same_take(self):
        result = evaluate(
            payload(
                context="active_audiovisual",
                events=["detach", "cancel", "stop", "close"],
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "idempotent")
        self.assertEqual(result["preservedResults"], ["take-1", _HASH])
        self.assertTrue(any("events detach,cancel,stop,close" in item for item in result["reasons"]))
        self.assertTrue(any("active_audiovisual" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_double_release_on_active_video_is_rejected(self):
        result = evaluate(payload(context="active_video", doubleRelease=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "idempotent"})
        self.assertEqual(result["rejectedClaims"], ["double-release"])
        self.assertEqual(result["preservedResults"], ["take-1", _HASH])

    def test_duplicate_publication_and_second_take_keep_the_original(self):
        result = evaluate(
            payload(
                context="recovery_reopening",
                duplicatePublication=True,
                secondTakeCreated=True,
                events=["close", "detach"],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(
            result["rejectedClaims"],
            ["duplicate-publication", "second-take-from-cleanup"],
        )
        self.assertEqual(result["preservedResults"], ["take-1", _HASH])
        joined = " ".join(result["preservedResults"])
        self.assertNotIn("take-2", joined)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "context": "idle"},
            {**valid, "events": []},
            {**valid, "events": ["pause"]},
            {**valid, "doubleRelease": "no"},
            {**valid, "takeId": ""},
            {k: v for k, v in valid.items() if k != "events"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
