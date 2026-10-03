"""TC-P058-07 double viewing transform."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p058_tc07", Path(__file__).resolve().parents[1] / "gates" / "p058_tc07.py"
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
        "stage": "preview",
        "transformCount": 1,
        "assignment": "manual",
        "patchId": "grey18",
        "patchDelta": "0",
        "cleanBranch": "clean",
        "renderedBranch": "rendered",
        "thumbnailCertifies": False,
    }
    base.update(overrides)
    return base


class TcP05807(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P058-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("clean:clean", result["preservedResults"])
        self.assertIn("rendered:rendered", result["preservedResults"])

    def test_single_transform_keeps_separate_branches(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "branches_separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("patch:grey18", result["preservedResults"])
        self.assertIn("delta:0", result["preservedResults"])

    def test_negative_thumbnail_does_not_certify_interpretation(self):
        result = evaluate(payload(thumbnailCertifies=True, patchDelta="0"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("thumbnail-not-certificate", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("clean:clean", result["preservedResults"])
        self.assertIn("rendered:rendered", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_manual_editor_assignment(self):
        result = evaluate(payload(stage="editor", assignment="manual", transformCount=2, patchDelta="0.2"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("double-viewing-transform", result["rejectedClaims"])
        self.assertIn("assignment:manual", result["preservedResults"])
        self.assertIn("stage:editor", result["preservedResults"])
        self.assertIn("clean:clean", result["preservedResults"])
        self.assertIn("rendered:rendered", result["preservedResults"])
        self.assertIn("delta:0.2", result["preservedResults"])

    def test_repeat_automatically_detected_source_tag(self):
        result = evaluate(
            payload(stage="development", assignment="auto-detected", transformCount=2, patchId="skin", patchDelta="0.4")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("double-viewing-transform", result["rejectedClaims"])
        self.assertIn("assignment:auto-detected", result["preservedResults"])
        self.assertIn("patch:skin", result["preservedResults"])
        self.assertIn("clean:clean", result["preservedResults"])
        self.assertTrue(any("skin" in item for item in result["reasons"]))

    def test_collapsed_branches_are_rejected_but_both_names_remain(self):
        result = evaluate(payload(renderedBranch="clean"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("branches-collapsed", result["rejectedClaims"])
        self.assertIn("clean:clean", result["preservedResults"])
        self.assertIn("rendered:clean", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "stage"},
            {**valid, "extra": True},
            {**valid, "transformCount": 3},
            {**valid, "assignment": "auto"},
            {**valid, "patchDelta": "-1"},
            {**valid, "thumbnailCertifies": "false"},
            {**valid, "cleanBranch": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
