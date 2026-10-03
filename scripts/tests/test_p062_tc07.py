"""TC-P062-07 double viewing transform."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p062_tc07", Path(__file__).resolve().parents[1] / "gates" / "p062_tc07.py"
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
        "sampleId": "patch-grey",
        "route": "preview",
        "transformKind": "display",
        "transformCount": 2,
        "referencePatch": "0.18",
        "observedPatch": "0.04",
        "thumbnailCertifies": False,
        "cleanBranch": "clean-log",
        "renderedBranch": "rendered-delivery",
    }
    base.update(overrides)
    return base


class TcP06207(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P062-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A generic player thumbnail must not certify correct color interpretation.",
        )

    def test_double_display_transform_keeps_both_branches(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["double-viewing-transform"])
        self.assertIn("reference:0.18", result["preservedResults"])
        self.assertIn("observed:0.04", result["preservedResults"])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:rendered-delivery", result["preservedResults"])
        self.assertIn("patch-grey", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "branches_preserved"})

    def test_thumbnail_does_not_certify_a_match(self):
        result = evaluate(
            payload(transformCount=1, observedPatch="0.18", thumbnailCertifies=True, route="editor")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["thumbnail-not-certificate"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:rendered-delivery", result["preservedResults"])
        self.assertIn("reference:0.18", result["preservedResults"])

    def test_repeat_manual_assignment(self):
        result = evaluate(
            payload(
                sampleId="manual",
                route="manual-assignment",
                transformKind="log",
                transformCount=2,
                thumbnailCertifies=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["double-viewing-transform", "thumbnail-not-certificate"],
        )
        self.assertIn("route:manual-assignment", result["preservedResults"])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:rendered-delivery", result["preservedResults"])

    def test_repeat_auto_tag(self):
        result = evaluate(payload(sampleId="auto", route="auto-tag", transformKind="log"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("route:auto-tag", result["preservedResults"])
        self.assertIn("kind:log", result["preservedResults"])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:rendered-delivery", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_single_matching_transform_preserves_branches(self):
        result = evaluate(
            payload(transformCount=1, observedPatch="0.18", route="development", sampleId="once")
        )
        self.assertEqual(result["decision"], "branches_preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("clean:clean-log", result["preservedResults"])
        self.assertIn("rendered:rendered-delivery", result["preservedResults"])
        self.assertIn("count:1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "route"},
            {**valid, "extra": True},
            {**valid, "transformCount": True},
            {**valid, "transformCount": 0},
            {**valid, "cleanBranch": "rendered-delivery"},
            {**valid, "referencePatch": "0.180"},
            {**valid, "thumbnailCertifies": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
