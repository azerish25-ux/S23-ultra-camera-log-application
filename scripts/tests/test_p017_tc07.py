"""TC-P017-07 independent monitoring toggle."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p017_tc07", Path(__file__).resolve().parents[1] / "gates" / "p017_tc07.py"
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
_SOURCE = "seq-controlled-24"
_MASTER = "master-clean-24"


def payload(**overrides):
    base = {
        "monitor": "histogram",
        "sourceSequence": _SOURCE,
        "cleanMaster": _MASTER,
        "toggleCount": 3,
        "recordsOverlay": False,
        "recordsPreviewGrade": False,
    }
    base.update(overrides)
    return base


class TcP01707(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P017-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("viewing transforms", _MODULE.INTERVENTION)
        self.assertIn("deterministic contract", _MODULE.EXPECTED)
        self.assertIn("false-color", _MODULE.NEGATIVE)
        self.assertIn("focus_peaking", _MODULE.MONITORS)
        self.assertIn("virtual_depth_display", _MODULE.MONITORS)

    def test_histogram_toggles_leave_clean_master_unchanged(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["preservedResults"], [_SOURCE, _MASTER])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("histogram toggled 3" in item for item in result["reasons"]))
        self.assertTrue(any("unchanged" in item for item in result["reasons"]))

    def test_focus_peaking_repeat_does_not_alter_source(self):
        result = evaluate(payload(monitor="focus_peaking", toggleCount=8))
        self.assertContract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["preservedResults"], [_SOURCE, _MASTER])
        self.assertTrue(any("focus_peaking toggled 8" in item for item in result["reasons"]))

    def test_film_preview_toggle_keeps_both_identities(self):
        result = evaluate(payload(monitor="film_preview", toggleCount=2))
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["preservedResults"], [_SOURCE, _MASTER])

    def test_virtual_depth_display_is_not_a_qualification(self):
        result = evaluate(payload(monitor="virtual_depth_display", toggleCount=5))
        self.assertEqual(result["decision"], "unchanged")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MASTER, result["preservedResults"])
        self.assertIn(_SOURCE, result["preservedResults"])

    def test_false_color_overlay_in_master_is_rejected(self):
        result = evaluate(payload(monitor="histogram", recordsOverlay=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["false-color-overlay"])
        self.assertEqual(result["preservedResults"], [_SOURCE, _MASTER])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_preview_grade_recorded_into_master_is_rejected(self):
        result = evaluate(payload(monitor="film_preview", recordsPreviewGrade=True, toggleCount=4))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["preview-grade-in-master"])
        self.assertEqual(result["preservedResults"], [_SOURCE, _MASTER])

    def test_both_negatives_still_preserve_the_clean_pair(self):
        result = evaluate(payload(recordsOverlay=True, recordsPreviewGrade=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["false-color-overlay", "preview-grade-in-master"],
        )
        self.assertEqual(result["preservedResults"], [_SOURCE, _MASTER])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "monitor": "zebra"},
            {**valid, "toggleCount": 0},
            {**valid, "toggleCount": True},
            {**valid, "sourceSequence": ""},
            {**valid, "recordsOverlay": "no"},
            {k: v for k, v in valid.items() if k != "cleanMaster"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
