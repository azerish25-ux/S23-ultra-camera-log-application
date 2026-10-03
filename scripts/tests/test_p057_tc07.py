"""TC-P057-07 a second viewing transform is not certified by a thumbnail."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p057_tc07", Path(__file__).resolve().parents[1] / "gates" / "p057_tc07.py"
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
        "path": "preview",
        "assignment": "manual",
        "transformCount": 2,
        "patchDelta": "0.25",
        "thumbnailAgrees": True,
    }
    base.update(overrides)
    return base


class TcP05707(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P057-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_manual_double_transform_rejects_the_thumbnail(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["double-viewing-transform", "thumbnail-certifies-color"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("branch:clean", result["preservedResults"])
        self.assertIn("branch:rendered:double-transform", result["preservedResults"])
        self.assertIn("patch-delta:0.25", result["preservedResults"])
        self.assertIn("assignment:manual", result["preservedResults"])

    def test_repeat_auto_tag_without_using_the_thumbnail(self):
        result = evaluate(
            payload(path="editor", assignment="auto-tag", thumbnailAgrees=False, patchDelta="0.4")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["double-viewing-transform"])
        self.assertIn("assignment:auto-tag", result["preservedResults"])
        self.assertIn("branch:clean", result["preservedResults"])
        self.assertIn("branch:rendered:double-transform", result["preservedResults"])
        self.assertNotIn("thumbnail-certifies-color", result["rejectedClaims"])

    def test_repeat_development_path(self):
        result = evaluate(payload(path="development", assignment="manual"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("path:development", result["preservedResults"])
        self.assertIn("branch:rendered:double-transform", result["preservedResults"])

    def test_thumbnail_alone_does_not_certify_a_single_transform(self):
        result = evaluate(payload(transformCount=1, thumbnailAgrees=True, patchDelta="0"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["thumbnail-certifies-color"])
        self.assertIn("branch:rendered:single-transform", result["preservedResults"])
        self.assertIn("branch:clean", result["preservedResults"])

    def test_single_transform_without_thumbnail_is_withheld(self):
        result = evaluate(payload(transformCount=1, thumbnailAgrees=False, assignment="auto-tag"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("branch:clean", result["preservedResults"])
        self.assertIn("branch:rendered:single-transform", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "path": "player"},
            {**valid, "transformCount": 5},
            {**valid, "patchDelta": "0.250"},
            {**valid, "thumbnailAgrees": 1},
            {**valid, "assignment": "detected"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
