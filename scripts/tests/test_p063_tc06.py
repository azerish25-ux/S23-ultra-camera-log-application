"""TC-P063-06 source-lineage laundering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p063_tc06", Path(__file__).resolve().parents[1] / "gates" / "p063_tc06.py"
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
        "assetId": "flat-ten",
        "acquisition": "sdr",
        "label": "raw-derived",
        "stage": "export-name",
        "containerDepth": "10",
        "visuallyFlat": True,
        "encodingChanged": True,
    }
    base.update(overrides)
    return base


class TcP06306(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P063-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Changing the encoding cannot upgrade the source acquisition category.",
        )
        self.assertIn("ten-bit", _MODULE.EXPECTED)

    def test_encoding_change_does_not_upgrade_sdr(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["lineage-laundered", "encoding-cannot-upgrade"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertIn("label:raw-derived", result["preservedResults"])
        self.assertIn("depth:10", result["preservedResults"])
        self.assertIn("visually-flat:true", result["preservedResults"])
        self.assertIn("flat-ten", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_import_hlg_native_label(self):
        result = evaluate(
            payload(
                assetId="hlg-take",
                acquisition="hlg",
                label="native-camera-equivalent",
                stage="import",
                encodingChanged=False,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["lineage-laundered"])
        self.assertIn("stage:import", result["preservedResults"])
        self.assertIn("acquisition:hlg", result["preservedResults"])
        self.assertIn("depth:10", result["preservedResults"])

    def test_repeat_recipe_selection(self):
        result = evaluate(payload(stage="recipe", assetId="recipe-sdr"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stage:recipe", result["preservedResults"])
        self.assertIn("encoding-cannot-upgrade", result["rejectedClaims"])

    def test_repeat_shared_metadata(self):
        result = evaluate(payload(stage="shared-metadata", assetId="share"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stage:shared-metadata", result["preservedResults"])
        self.assertIn("label:raw-derived", result["preservedResults"])

    def test_honest_sdr_label_is_withheld(self):
        result = evaluate(payload(label="sdr", encodingChanged=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertIn("label:sdr", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "acquisition": "raw-log"},
            {**valid, "stage": "thumbnail"},
            {**valid, "containerDepth": "12"},
            {**valid, "visuallyFlat": 1},
            {k: v for k, v in valid.items() if k != "label"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
