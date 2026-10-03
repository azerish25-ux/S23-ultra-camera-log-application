"""TC-P073-07 unversioned profile change."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p073_tc07", Path(__file__).resolve().parents[1] / "gates" / "p073_tc07.py"
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
        "parameter": "curve",
        "recipeId": "vision-400-a",
        "bytesChanged": True,
        "versionCreated": False,
        "priorRenderReproducible": True,
        "overwriteInPlace": True,
    }
    base.update(overrides)
    return base


class TcP07307(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P073-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("immutable recipe", _MODULE.INTERVENTION)
        self.assertIn("Overwriting", _MODULE.NEGATIVE)
        self.assertIn("halation", _MODULE.REPEAT)
        self.assertIn("print-response", _MODULE.REPEAT)

    def test_curve_overwrite_fails_and_keeps_the_prior_recipe(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["overwrite-in-place"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("vision-400-a", result["preservedResults"])
        self.assertIn("prior:vision-400-a", result["preservedResults"])
        self.assertIn("parameter:curve", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "version_created"})

    def test_grain_change_creates_a_new_version(self):
        result = evaluate(
            payload(parameter="grain", versionCreated=True, overwriteInPlace=False, priorRenderReproducible=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "version_created")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("parameter:grain", result["preservedResults"])
        self.assertIn("prior:vision-400-a", result["preservedResults"])
        self.assertIn("version-created:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_halation_overwrite_is_rejected(self):
        result = evaluate(payload(parameter="halation", versionCreated=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["overwrite-in-place"])
        self.assertIn("parameter:halation", result["preservedResults"])
        self.assertIn("prior:vision-400-a", result["preservedResults"])

    def test_print_response_without_prior_reproducibility_fails(self):
        result = evaluate(
            payload(
                parameter="print-response",
                versionCreated=True,
                overwriteInPlace=False,
                priorRenderReproducible=False,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["prior-render-lost"])
        self.assertIn("parameter:print-response", result["preservedResults"])
        self.assertIn("prior:vision-400-a", result["preservedResults"])

    def test_unchanged_recipe_is_not_qualified(self):
        result = evaluate(
            payload(bytesChanged=False, versionCreated=False, overwriteInPlace=False, parameter="curve")
        )
        self.assertEqual(result["decision"], "recipe_unchanged")
        self.assertIn("bytes-changed:false", result["preservedResults"])
        self.assertIn("vision-400-a", result["preservedResults"])

    def test_bytes_changed_without_a_version_is_an_overwrite(self):
        result = evaluate(payload(overwriteInPlace=False, versionCreated=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["overwrite-in-place"])
        self.assertIn("prior:vision-400-a", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "parameter"},
            {**valid, "extra": True},
            {**valid, "parameter": "contrast"},
            {**valid, "recipeId": "Vision 400"},
            {**valid, "bytesChanged": "true"},
            {**valid, "versionCreated": 1},
            {**valid, "overwriteInPlace": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
