"""TC-P061-07 double viewing transform."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p061_tc07", Path(__file__).resolve().parents[1] / "gates" / "p061_tc07.py"
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
        "assignment": "manual",
        "applications": 2,
        "cleanPatch": "0.18",
        "renderedPatch": "0.04",
        "expectedRendered": "0.4",
        "thumbnailAgrees": True,
    }
    base.update(overrides)
    return base


class TcP06107(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P061-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("twice", _MODULE.INTERVENTION)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A generic player thumbnail must not certify correct color interpretation.",
        )
        self.assertIn("manual editor", _MODULE.REPEAT)
        self.assertIn("automatically detected", _MODULE.REPEAT)

    def test_thumbnail_does_not_certify_a_double_transform(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["double-viewing-transform", "patch-mismatch", "thumbnail-not-certification"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("clean:0.18", result["preservedResults"])
        self.assertIn("rendered:0.04", result["preservedResults"])
        self.assertIn("expected:0.4", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "branches_separated"})

    def test_single_matching_transform_keeps_both_branches(self):
        result = evaluate(
            payload(
                applications=1,
                renderedPatch="0.4",
                thumbnailAgrees=False,
            )
        )
        self.assertEqual(result["decision"], "branches_separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("clean:0.18", result["preservedResults"])
        self.assertIn("rendered:0.4", result["preservedResults"])

    def test_repeat_manual_assignment(self):
        result = evaluate(payload(stage="editor", assignment="manual"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("assignment:manual", result["preservedResults"])
        self.assertIn("stage:editor", result["preservedResults"])
        self.assertIn("double-viewing-transform", result["rejectedClaims"])
        self.assertIn("clean:0.18", result["preservedResults"])

    def test_repeat_auto_tag(self):
        result = evaluate(
            payload(
                stage="development",
                assignment="auto-tag",
                applications=1,
                renderedPatch="0.2",
                thumbnailAgrees=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("assignment:auto-tag", result["preservedResults"])
        self.assertIn("patch-mismatch", result["rejectedClaims"])
        self.assertIn("thumbnail-not-certification", result["rejectedClaims"])
        self.assertIn("clean:0.18", result["preservedResults"])
        self.assertIn("rendered:0.2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "applications": 3},
            {**valid, "thumbnailAgrees": "yes"},
            {**valid, "assignment": "guess"},
            {**valid, "cleanPatch": "0.180"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
