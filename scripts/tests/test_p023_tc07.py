"""TC-P023-07 monitoring toggles must not alter the clean contract."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p023_tc07", Path(__file__).resolve().parents[1] / "gates" / "p023_tc07.py"
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
_DIGEST = "a" * 64
_OTHER = "b" * 64


def payload(**overrides):
    base = {
        "overlay": "histogram",
        "toggleCount": 3,
        "contract": "clean_master",
        "cleanDigest": _DIGEST,
        "recordedDigest": _DIGEST,
        "overlayRecordedIntoMaster": False,
        "previewGradeRecorded": False,
    }
    base.update(overrides)
    return base


class TcP02307(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P023-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("same controlled source sequence", _MODULE.INTERVENTION)
        self.assertIn("deterministic contract", _MODULE.EXPECTED)
        self.assertIn("false-color overlay or preview grade", _MODULE.NEGATIVE)
        self.assertIn("histogram", _MODULE.OVERLAYS)
        self.assertIn("virtual_depth_display", _MODULE.OVERLAYS)

    def test_histogram_toggles_leave_clean_master_unchanged(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            [f"clean:{_DIGEST}", f"recorded:{_DIGEST}", "histogram"],
        )
        self.assertTrue(any(_MODULE.EXPECTED in item for item in result["reasons"]))

    def test_focus_peaking_leaves_clean_source_unchanged(self):
        result = evaluate(
            payload(overlay="focus_peaking", contract="clean_source", toggleCount=4)
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertIn("focus_peaking", result["preservedResults"])
        self.assertIn(f"clean:{_DIGEST}", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_film_preview_recorded_into_master_is_rejected(self):
        result = evaluate(payload(overlay="film_preview", overlayRecordedIntoMaster=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unchanged"})
        self.assertIn("overlay-recorded-into-clean-master", result["rejectedClaims"])
        self.assertIn(f"clean:{_DIGEST}", result["preservedResults"])
        self.assertIn(f"recorded:{_DIGEST}", result["preservedResults"])
        self.assertIn("film_preview", result["preservedResults"])
        self.assertTrue(any(_MODULE.NEGATIVE in item for item in result["reasons"]))

    def test_virtual_depth_preview_grade_is_rejected(self):
        result = evaluate(
            payload(
                overlay="virtual_depth_display",
                contract="clean_source",
                previewGradeRecorded=True,
                recordedDigest=_OTHER,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("preview-grade-in-clean-master", result["rejectedClaims"])
        self.assertIn("clean-content-changed", result["rejectedClaims"])
        self.assertIn(f"clean:{_DIGEST}", result["preservedResults"])
        self.assertIn(f"recorded:{_OTHER}", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_digest_mismatch_alone_is_rejected(self):
        result = evaluate(payload(recordedDigest=_OTHER))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["clean-content-changed"])
        self.assertIn(f"recorded:{_OTHER}", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "overlay": "zebra"},
            {**valid, "toggleCount": 1},
            {**valid, "toggleCount": True},
            {**valid, "contract": "graded"},
            {**valid, "cleanDigest": "A" * 64},
            {**valid, "cleanDigest": "abc"},
            {**valid, "overlayRecordedIntoMaster": 0},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
