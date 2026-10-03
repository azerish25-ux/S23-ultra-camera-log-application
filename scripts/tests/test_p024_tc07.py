"""TC-P024-07 monitoring toggles must not change the clean contract."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p024_tc07", Path(__file__).resolve().parents[1] / "gates" / "p024_tc07.py"
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
_CLEAN = "a" * 64
_OTHER = "b" * 64


def payload(**overrides):
    base = {
        "overlay": "histogram",
        "toggleCount": 3,
        "contract": "clean_master",
        "cleanDigest": _CLEAN,
        "recordedDigest": _CLEAN,
        "overlayRecordedIntoMaster": False,
        "previewGradeRecorded": False,
    }
    base.update(overrides)
    return base


class TcP02407(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P024-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("overlays and viewing transforms", _MODULE.INTERVENTION)
        self.assertIn("deterministic contract", _MODULE.EXPECTED)
        self.assertIn("false-color overlay", _MODULE.NEGATIVE)
        self.assertIn("histogram", _MODULE.OVERLAYS)
        self.assertIn("virtual_depth_display", _MODULE.OVERLAYS)

    def test_histogram_toggle_leaves_the_clean_master(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            [f"clean:{_CLEAN}", f"recorded:{_CLEAN}", "histogram"],
        )
        self.assertTrue(any("histogram" in item for item in result["reasons"]))
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_focus_peaking_on_clean_source_stays_unchanged(self):
        result = evaluate(
            payload(overlay="focus_peaking", contract="clean_source", toggleCount=4)
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertIn("focus_peaking", result["preservedResults"])
        self.assertIn(f"clean:{_CLEAN}", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_false_color_baked_into_the_master_is_rejected(self):
        result = evaluate(
            payload(overlay="film_preview", overlayRecordedIntoMaster=True, toggleCount=2)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unchanged"})
        self.assertIn("overlay-recorded-into-clean-master", result["rejectedClaims"])
        self.assertIn(f"clean:{_CLEAN}", result["preservedResults"])
        self.assertIn(f"recorded:{_CLEAN}", result["preservedResults"])
        self.assertIn("film_preview", result["preservedResults"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_preview_grade_and_digest_drift_keep_both_digests(self):
        result = evaluate(
            payload(
                overlay="virtual_depth_display",
                previewGradeRecorded=True,
                recordedDigest=_OTHER,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("preview-grade-in-clean-master", result["rejectedClaims"])
        self.assertIn("clean-content-changed", result["rejectedClaims"])
        self.assertIn(f"clean:{_CLEAN}", result["preservedResults"])
        self.assertIn(f"recorded:{_OTHER}", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "overlay": "false_color"},
            {**valid, "toggleCount": 1},
            {**valid, "contract": "preview"},
            {**valid, "cleanDigest": "abcd"},
            {**valid, "recordedDigest": "A" * 64},
            {**valid, "overlayRecordedIntoMaster": "yes"},
            {key: value for key, value in valid.items() if key != "overlay"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
