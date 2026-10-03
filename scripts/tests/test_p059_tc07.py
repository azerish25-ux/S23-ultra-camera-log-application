"""TC-P059-07 double viewing transform."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p059_tc07", Path(__file__).resolve().parents[1] / "gates" / "p059_tc07.py"
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
        "assignment": "none",
        "transformCount": 1,
        "patchId": "grey-18",
        "cleanCode": "0.18",
        "renderedCode": "0.18",
        "thumbnailAgrees": False,
    }
    base.update(overrides)
    return base


class TcP05907(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P059-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("clean:0.18", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("twice", _MODULE.INTERVENTION)
        self.assertIn("clean and rendered", _MODULE.EXPECTED)
        self.assertIn("thumbnail", _MODULE.NEGATIVE)

    def test_single_transform_keeps_both_branches(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("rendered:0.18", result["preservedResults"])
        self.assertIn("transforms:1", result["preservedResults"])
        self.assertIn("patch:grey-18", result["preservedResults"])

    def test_double_transform_preserves_separate_branches(self):
        result = evaluate(payload(transformCount=2, renderedCode="0.46", stage="development"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "mismatch_detected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})
        self.assertIn("double-transform", result["rejectedClaims"])
        self.assertIn("clean:0.18", result["preservedResults"])
        self.assertIn("rendered:0.46", result["preservedResults"])
        self.assertIn("stage:development", result["preservedResults"])
        self.assertNotIn("rendered:0.18", result["preservedResults"])

    def test_negative_thumbnail_does_not_certify(self):
        result = evaluate(payload(transformCount=2, renderedCode="0.46", thumbnailAgrees=True))
        self.assertEqual(result["decision"], "mismatch_detected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("thumbnail-not-certification", result["rejectedClaims"])
        self.assertIn("double-transform", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("clean:0.18", result["preservedResults"])
        self.assertIn("rendered:0.46", result["preservedResults"])

    def test_thumbnail_alone_is_rejected(self):
        result = evaluate(payload(thumbnailAgrees=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["thumbnail-not-certification"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("clean:0.18", result["preservedResults"])
        self.assertIn("rendered:0.18", result["preservedResults"])

    def test_repeat_manual_editor_assignment(self):
        result = evaluate(
            payload(stage="editor", assignment="manual", transformCount=2, renderedCode="0.7")
        )
        self.assertEqual(result["decision"], "mismatch_detected")
        self.assertIn("assignment:manual", result["preservedResults"])
        self.assertIn("stage:editor", result["preservedResults"])
        self.assertIn("rendered:0.7", result["preservedResults"])
        self.assertIn("clean:0.18", result["preservedResults"])

    def test_repeat_automatic_source_tag(self):
        result = evaluate(
            payload(assignment="automatic", transformCount=2, renderedCode="0.33", stage="preview")
        )
        self.assertEqual(result["decision"], "mismatch_detected")
        self.assertIn("assignment:automatic", result["preservedResults"])
        self.assertIn("rendered:0.33", result["preservedResults"])
        self.assertIn("clean:0.18", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "patchId"},
            {**valid, "extra": 1},
            {**valid, "transformCount": 3},
            {**valid, "assignment": "auto"},
            {**valid, "cleanCode": "0.180"},
            {**valid, "thumbnailAgrees": "yes"},
            {**valid, "stage": "player"},
            {**valid, "patchId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
