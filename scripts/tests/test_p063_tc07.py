"""TC-P063-07 double viewing transform."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p063_tc07", Path(__file__).resolve().parents[1] / "gates" / "p063_tc07.py"
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
        "clipId": "take-7",
        "stage": "preview",
        "transformCount": "1",
        "referencePatch": "grey-18",
        "cleanBranch": "clean-log",
        "renderedBranch": "display-render",
        "thumbnailOnly": True,
        "playerOpened": True,
    }
    base.update(overrides)
    return base


class TcP06307(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P063-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A generic player thumbnail must not certify correct color interpretation.",
        )
        self.assertIn("reference patches", _MODULE.EXPECTED)

    def test_thumbnail_does_not_certify_interpretation(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["generic-player-thumbnail"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:display-render", result["preservedResults"])
        self.assertIn("patch:grey-18", result["preservedResults"])
        self.assertIn("take-7", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "branches_separated"})

    def test_double_transform_detects_mismatch_and_keeps_branches(self):
        result = evaluate(payload(transformCount="2", thumbnailOnly=False, stage="development"))
        self.assertEqual(result["decision"], "mismatch_detected")
        self.assertEqual(result["rejectedClaims"], ["double-viewing-transform"])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:display-render", result["preservedResults"])
        self.assertIn("stage:development", result["preservedResults"])

    def test_repeat_manual_editor_assignment(self):
        result = evaluate(
            payload(transformCount="2", thumbnailOnly=False, stage="manual-assignment", playerOpened=False)
        )
        self.assertEqual(result["decision"], "mismatch_detected")
        self.assertIn("stage:manual-assignment", result["preservedResults"])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:display-render", result["preservedResults"])

    def test_repeat_automatic_source_tag(self):
        result = evaluate(payload(transformCount="2", thumbnailOnly=False, stage="auto-tag"))
        self.assertEqual(result["decision"], "mismatch_detected")
        self.assertIn("stage:auto-tag", result["preservedResults"])
        self.assertIn("transforms:2", result["preservedResults"])

    def test_thumbnail_plus_double_transform_still_rejects(self):
        result = evaluate(payload(transformCount="2", stage="editor"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("double-viewing-transform", result["rejectedClaims"])
        self.assertIn("generic-player-thumbnail", result["rejectedClaims"])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "mismatch_detected"})

    def test_single_transform_separates_branches(self):
        result = evaluate(payload(thumbnailOnly=False, playerOpened=False, stage="editor"))
        self.assertEqual(result["decision"], "branches_separated")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:display-render", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "transformCount": "3"},
            {**valid, "cleanBranch": "display-render"},
            {**valid, "stage": "grade"},
            {**valid, "thumbnailOnly": "yes"},
            {k: v for k, v in valid.items() if k != "clipId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
