"""TC-P059-06 source-lineage laundering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p059_tc06", Path(__file__).resolve().parents[1] / "gates" / "p059_tc06.py"
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
        "exportLabel": "raw-derived",
        "bitDepth": 10,
        "visuallyFlat": True,
        "stage": "import",
    }
    base.update(overrides)
    return base


class TcP05906(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P059-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn("acquisition:sdr", result["preservedResults"])

    def test_constants_encode_the_case(self):
        self.assertIn("RAW-derived", _MODULE.INTERVENTION)
        self.assertIn("ten-bit and visually flat", _MODULE.EXPECTED)
        self.assertIn("cannot upgrade", _MODULE.NEGATIVE)

    def test_negative_ten_bit_flat_sdr_is_not_raw(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["lineage-laundering"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("bit-depth:10", result["preservedResults"])
        self.assertIn("flat:true", result["preservedResults"])
        self.assertIn("label:raw-derived", result["preservedResults"])
        self.assertIn("stage:import", result["preservedResults"])

    def test_repeat_import_keeps_hlg_lineage(self):
        result = evaluate(
            payload(acquisition="hlg", exportLabel="native-camera-equivalent", stage="import", visuallyFlat=False)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("acquisition:hlg", result["preservedResults"])
        self.assertIn("label:native-camera-equivalent", result["preservedResults"])
        self.assertIn("stage:import", result["preservedResults"])
        self.assertIn("flat:false", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_recipe_selection(self):
        result = evaluate(payload(stage="recipe", bitDepth=8, visuallyFlat=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stage:recipe", result["preservedResults"])
        self.assertIn("bit-depth:8", result["preservedResults"])
        self.assertIn("lineage-laundering", result["rejectedClaims"])

    def test_repeat_export_name_and_shared_metadata(self):
        for stage in ("export-name", "shared-metadata"):
            result = evaluate(payload(stage=stage))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn("stage:" + stage, result["preservedResults"])
            self.assertIn("bit-depth:10", result["preservedResults"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_matching_sdr_label_is_withheld(self):
        result = evaluate(payload(exportLabel="sdr", visuallyFlat=False, bitDepth=8))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("label:sdr", result["preservedResults"])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_raw_source_is_not_upgraded_by_a_flat_grade(self):
        result = evaluate(payload(acquisition="raw", exportLabel="raw-derived"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("acquisition:raw", result["preservedResults"])
        self.assertNotIn("lineage-laundering", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "stage"},
            {**valid, "extra": True},
            {**valid, "acquisition": "raw-video"},
            {**valid, "exportLabel": "logc3"},
            {**valid, "bitDepth": 12},
            {**valid, "visuallyFlat": "true"},
            {**valid, "stage": "grade"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
