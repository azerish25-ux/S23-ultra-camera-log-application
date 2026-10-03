"""TC-P044-08 profile replacement and rollback."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p044_tc08", Path(__file__).resolve().parents[1] / "gates" / "p044_tc08.py"
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
        "archivedRecipeId": "recipe-a",
        "revisedRecipeId": "recipe-b",
        "sameIdentifier": False,
        "overwriteBytes": False,
        "action": "install",
        "renderedId": "render-1",
        "historicalProvenance": "prov-1",
    }
    base.update(overrides)
    return base


class TcP04408(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P044-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants_encode_intervention_expected_and_negative(self):
        self.assertIn("rendered and archived", _MODULE.INTERVENTION)
        self.assertIn("historical provenance", _MODULE.EXPECTED)
        self.assertIn("same identifier", _MODULE.NEGATIVE)

    def test_explicit_install_keeps_the_archived_recipe(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "explicit_new_render")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"][:4],
            [
                "archived:recipe-a",
                "revised:recipe-b",
                "rendered:render-1",
                "provenance:prov-1",
            ],
        )
        self.assertIn("new rendering is explicit and historical provenance stands", result["openQuestions"])

    def test_firmware_repeat_does_not_rewrite_provenance(self):
        result = evaluate(payload(action="firmware", revisedRecipeId="recipe-fw"))
        self.assertEqual(result["decision"], "firmware_noted")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("archived:recipe-a", result["preservedResults"])
        self.assertIn("revised:recipe-fw", result["preservedResults"])
        self.assertIn("provenance:prov-1", result["preservedResults"])
        self.assertIn("action:firmware", result["preservedResults"])

    def test_rename_repeat_keeps_the_historical_id(self):
        result = evaluate(payload(action="rename", revisedRecipeId="recipe-display"))
        self.assertEqual(result["decision"], "renamed_explicit")
        self.assertIn("archived:recipe-a", result["preservedResults"])
        self.assertIn("revised:recipe-display", result["preservedResults"])
        self.assertIn("provenance:prov-1", result["preservedResults"])
        self.assertNotIn("provenance:recipe-display", result["preservedResults"])

    def test_rollback_repeat_returns_the_earlier_recipe(self):
        result = evaluate(
            payload(action="rollback", revisedRecipeId="recipe-a", sameIdentifier=True)
        )
        self.assertEqual(result["decision"], "rolled_back")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("archived:recipe-a", result["preservedResults"])
        self.assertIn("provenance:prov-1", result["preservedResults"])
        self.assertIn("rendered:render-1", result["preservedResults"])
        self.assertIn("explicit rollback kept the earlier recipe identity", result["openQuestions"])

    def test_negative_same_identifier_overwrite_cannot_qualify(self):
        result = evaluate(
            payload(
                archivedRecipeId="recipe-a",
                revisedRecipeId="recipe-a",
                sameIdentifier=True,
                overwriteBytes=True,
                action="install",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "explicit_new_render"})
        self.assertEqual(result["rejectedClaims"], ["identifier-overwrite"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("archived:recipe-a", result["preservedResults"])
        self.assertIn("rendered:render-1", result["preservedResults"])
        self.assertIn("provenance:prov-1", result["preservedResults"])
        self.assertNotIn("provenance:recipe-a", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "action"},
            {**valid, "extra": True},
            {**valid, "action": "delete"},
            {**valid, "sameIdentifier": True},
            {**valid, "archivedRecipeId": "recipe-b"},
            {**valid, "overwriteBytes": "false"},
            {**valid, "renderedId": ""},
            {**valid, "historicalProvenance": " prov-1"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
