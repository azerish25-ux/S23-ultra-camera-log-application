"""TC-P058-06 source-lineage laundering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p058_tc06", Path(__file__).resolve().parents[1] / "gates" / "p058_tc06.py"
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
        "acquisition": "sdr",
        "exportLabel": "sdr",
        "tenBit": True,
        "visuallyFlat": True,
        "stage": "import",
        "encodingChanged": False,
    }
    base.update(overrides)
    return base


class TcP05806(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P058-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("acquisition:sdr", result["preservedResults"])

    def test_matching_sdr_label_retains_lineage(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "lineage_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("stage:import", result["preservedResults"])
        self.assertIn("ten-bit:true", result["preservedResults"])

    def test_negative_encoding_change_does_not_upgrade_sdr(self):
        result = evaluate(
            payload(
                exportLabel="raw-derived",
                tenBit=True,
                visuallyFlat=True,
                encodingChanged=True,
                stage="export-name",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("laundered-lineage", result["rejectedClaims"])
        self.assertIn("encoding-does-not-upgrade-acquisition", result["rejectedClaims"])
        self.assertIn("ten-bit-file", result["rejectedClaims"])
        self.assertIn("visually-flat", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertIn("label:raw-derived", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_import_and_recipe_stages(self):
        imported = evaluate(payload(acquisition="hlg", exportLabel="native-camera-equivalent", stage="import"))
        self.assertEqual(imported["decision"], "rejected")
        self.assertIn("acquisition:hlg", imported["preservedResults"])
        self.assertIn("stage:import", imported["preservedResults"])
        self.assertIn("laundered-lineage", imported["rejectedClaims"])
        recipe = evaluate(payload(acquisition="hlg", exportLabel="raw-derived", stage="recipe", tenBit=True))
        self.assertEqual(recipe["decision"], "rejected")
        self.assertIn("stage:recipe", recipe["preservedResults"])
        self.assertIn("ten-bit-file", recipe["rejectedClaims"])
        self.assertIn("label:raw-derived", recipe["preservedResults"])

    def test_repeat_shared_metadata(self):
        result = evaluate(
            payload(
                acquisition="sdr",
                exportLabel="native-camera-equivalent",
                stage="shared-metadata",
                visuallyFlat=True,
                tenBit=False,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stage:shared-metadata", result["preservedResults"])
        self.assertIn("visually-flat", result["rejectedClaims"])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertNotIn("ten-bit-file", result["rejectedClaims"])

    def test_raw_native_equivalent_label_is_not_established(self):
        result = evaluate(payload(acquisition="raw", exportLabel="native-camera-equivalent", stage="export-name"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("native-equivalent-unproven", result["rejectedClaims"])
        self.assertIn("acquisition:raw", result["preservedResults"])
        retained = evaluate(payload(acquisition="raw", exportLabel="raw-derived"))
        self.assertEqual(retained["decision"], "lineage_retained")
        self.assertIn("acquisition:raw", retained["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "acquisition"},
            {**valid, "extra": True},
            {**valid, "acquisition": "log"},
            {**valid, "exportLabel": "raw"},
            {**valid, "stage": "preview"},
            {**valid, "tenBit": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
