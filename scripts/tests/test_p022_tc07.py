"""TC-P022-07 monitoring toggles do not change the clean master."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p022_tc07", Path(__file__).resolve().parents[1] / "gates" / "p022_tc07.py"
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
_SOURCE = "src-stable"
_PREVIEW = "preview-branch"


def payload(**overrides):
    base = {
        "aid": "histogram",
        "enabled": True,
        "sourceHash": _SOURCE,
        "cleanMasterHash": _SOURCE,
        "previewHash": _PREVIEW,
        "overlayInMaster": False,
        "previewGradeInMaster": False,
    }
    base.update(overrides)
    return base


class TcP02207(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P022-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_module_encodes_the_case_text(self):
        self.assertIn("viewing transforms", _MODULE.INTERVENTION)
        self.assertIn("clean-master", _MODULE.EXPECTED)
        self.assertIn("false-color overlay", _MODULE.NEGATIVE)

    def test_histogram_leaves_the_clean_master_unchanged(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["preservedResults"], [_SOURCE, _SOURCE])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("histogram" in item for item in result["reasons"]))
        self.assertTrue(any("monitoring" in item for item in result["reasons"]))

    def test_focus_peaking_also_leaves_the_source_hash(self):
        result = evaluate(payload(aid="focus_peaking", previewHash="peaking-preview"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "unchanged")
        self.assertEqual(result["preservedResults"], [_SOURCE, _SOURCE])
        self.assertTrue(any("focus_peaking" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_film_preview_grade_in_the_master_is_rejected(self):
        result = evaluate(payload(aid="film_preview", previewGradeInMaster=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "unchanged"})
        self.assertIn("preview-grade-in-clean-master", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], [_SOURCE, _SOURCE])

    def test_false_color_overlay_in_the_master_is_rejected(self):
        result = evaluate(
            payload(aid="false_color", overlayInMaster=True, cleanMasterHash="burned-overlay")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("overlay-in-clean-master", result["rejectedClaims"])
        self.assertIn("clean-master-drift", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], [_SOURCE, "burned-overlay"])

    def test_virtual_depth_without_a_preview_branch_is_rejected(self):
        result = evaluate(payload(aid="virtual_depth", previewHash=_SOURCE))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("monitoring-branch-missing", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], [_SOURCE, _SOURCE])

    def test_disabled_histogram_can_match_when_the_master_matches(self):
        result = evaluate(payload(enabled=False, previewHash=_SOURCE))
        self.assertEqual(result["decision"], "unchanged")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_SOURCE, result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "aid": "zebra"},
            {**valid, "enabled": "yes"},
            {**valid, "sourceHash": ""},
            {**valid, "overlayInMaster": 0},
            {k: v for k, v in valid.items() if k != "aid"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
