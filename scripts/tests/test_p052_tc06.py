"""TC-P052-06 defect versus real highlight."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p052_tc06", Path(__file__).resolve().parents[1] / "gates" / "p052_tc06.py"
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
        "frameId": "frame-1",
        "site": "frame",
        "defectId": "hot-1",
        "highlightId": "spec-1",
        "defectCorrected": True,
        "highlightPreserved": True,
        "removeAllIsolated": False,
    }
    base.update(overrides)
    return base


class TcP05206(unittest.TestCase):
    def test_supported_defect_keeps_highlight(self):
        result = evaluate(payload())
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P052-06")
        self.assertEqual(result["decision"], "kept-highlight")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("defect:hot-1:corrected=true", result["preservedResults"])
        self.assertIn("highlight:spec-1:preserved=true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_negative_remove_all_keeps_both_identities(self):
        result = evaluate(payload(highlightPreserved=False, removeAllIsolated=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("remove-all-isolated-bright", result["rejectedClaims"])
        self.assertIn("highlight-removed", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("defect:hot-1:corrected=true", result["preservedResults"])
        self.assertIn("highlight:spec-1:preserved=false", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "kept-highlight"})

    def test_repeat_frame_2(self):
        result = evaluate(payload(frameId="frame-2"))
        self.assertEqual(result["decision"], "kept-highlight")
        self.assertIn("frame:frame-2", result["preservedResults"])
        self.assertIn("highlight:spec-1:preserved=true", result["preservedResults"])

    def test_repeat_saturated_boundary(self):
        result = evaluate(payload(frameId="frame-3", site="saturated-boundary"))
        self.assertEqual(result["decision"], "kept-highlight")
        self.assertIn("site:saturated-boundary", result["preservedResults"])
        self.assertIn("frame:frame-3", result["preservedResults"])

    def test_highlight_removed_without_blanket_policy(self):
        result = evaluate(payload(highlightPreserved=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["highlight-removed"])
        self.assertIn("highlight:spec-1:preserved=false", result["preservedResults"])
        self.assertNotIn("remove-all-isolated-bright", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "frameId"},
            {**valid, "extra": True},
            {**valid, "site": "corner"},
            {**valid, "defectCorrected": "true"},
            {**valid, "highlightId": "hot-1"},
            {**valid, "frameId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
