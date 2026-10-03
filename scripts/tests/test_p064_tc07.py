"""TC-P064-07 double viewing transform."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p064_tc07", Path(__file__).resolve().parents[1] / "gates" / "p064_tc07.py"
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
        "transformCount": 1,
        "transformKind": "display",
        "referencePatchMismatch": False,
        "cleanBranch": "clean-a",
        "renderedBranch": "rendered-b",
        "thumbnailCertifies": False,
    }
    base.update(overrides)
    return base


class TcP06407(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P064-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A generic player thumbnail must not certify correct color interpretation.",
        )
        self.assertIn("manual editor", _MODULE.REPEAT)
        self.assertIn("automatically detected", _MODULE.REPEAT)

    def test_single_transform_keeps_both_branches(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("clean:clean-a", result["preservedResults"])
        self.assertIn("rendered:rendered-b", result["preservedResults"])
        self.assertIn("assignment:manual", result["preservedResults"])

    def test_double_transform_is_detected_and_keeps_branches(self):
        result = evaluate(payload(transformCount=2, referencePatchMismatch=True, transformKind="log"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["double-viewing-transform"])
        self.assertIn("clean:clean-a", result["preservedResults"])
        self.assertIn("rendered:rendered-b", result["preservedResults"])
        self.assertIn("transform-count:2", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_thumbnail_does_not_certify_interpretation(self):
        result = evaluate(payload(thumbnailCertifies=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["thumbnail-not-interpretation"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("clean:clean-a", result["preservedResults"])
        self.assertIn("rendered:rendered-b", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_manual_editor_assignment(self):
        result = evaluate(
            payload(path="editor", assignment="manual", transformCount=2, referencePatchMismatch=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("double-viewing-transform", result["rejectedClaims"])
        self.assertIn("assignment:manual", result["preservedResults"])
        self.assertIn("path:editor", result["preservedResults"])
        self.assertIn("clean:clean-a", result["preservedResults"])

    def test_repeat_automatic_source_tag(self):
        result = evaluate(
            payload(
                path="development",
                assignment="automatic",
                transformCount=2,
                referencePatchMismatch=True,
                transformKind="log",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("assignment:automatic", result["preservedResults"])
        self.assertIn("rendered:rendered-b", result["preservedResults"])
        self.assertIn("clean:clean-a", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "cleanBranch": "same", "renderedBranch": "same"},
            {**valid, "transformCount": 3},
            {**valid, "assignment": "guessed"},
            {**valid, "thumbnailCertifies": "yes"},
            {**valid, "path": "file"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
