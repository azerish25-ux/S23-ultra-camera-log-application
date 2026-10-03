"""TC-P064-06 source-lineage laundering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p064_tc06", Path(__file__).resolve().parents[1] / "gates" / "p064_tc06.py"
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
        "stage": "export-name",
        "acquisition": "SDR-derived",
        "exportLabel": "processed-look",
        "containerBitDepth": 10,
        "visuallyFlat": True,
        "encodingChanged": False,
    }
    base.update(overrides)
    return base


class TcP06406(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P064-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Changing the encoding cannot upgrade the source acquisition category.",
        )
        self.assertIn("import", _MODULE.REPEAT)
        self.assertIn("shared metadata", _MODULE.REPEAT)

    def test_processed_look_on_sdr_is_withheld(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:SDR-derived", result["preservedResults"])
        self.assertIn("export-label:processed-look", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])
        self.assertIn("visually-flat:true", result["preservedResults"])

    def test_sdr_under_raw_label_is_rejected_when_flat_and_ten_bit(self):
        result = evaluate(payload(exportLabel="RAW-derived"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["lineage-laundering"])
        self.assertIn("acquisition:SDR-derived", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])
        self.assertIn("visually-flat:true", result["preservedResults"])
        self.assertIn("stage:export-name", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_encoding_change_does_not_upgrade_acquisition(self):
        result = evaluate(payload(exportLabel="HLG-derived", encodingChanged=True, visuallyFlat=False, containerBitDepth=8))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("encoding-does-not-upgrade-acquisition", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:SDR-derived", result["preservedResults"])
        self.assertIn("export-label:HLG-derived", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_import_stage(self):
        result = evaluate(payload(stage="import", exportLabel="native-camera-equivalent"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("lineage-laundering", result["rejectedClaims"])
        self.assertIn("native-camera-equivalent-unproven", result["rejectedClaims"])
        self.assertIn("stage:import", result["preservedResults"])
        self.assertIn("acquisition:SDR-derived", result["preservedResults"])

    def test_repeat_recipe_selection(self):
        result = evaluate(payload(stage="recipe", acquisition="HLG-derived", exportLabel="RAW-derived"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["lineage-laundering"])
        self.assertIn("stage:recipe", result["preservedResults"])
        self.assertIn("acquisition:HLG-derived", result["preservedResults"])
        self.assertIn("visually-flat:true", result["preservedResults"])

    def test_repeat_shared_metadata(self):
        result = evaluate(
            payload(
                stage="shared-metadata",
                exportLabel="RAW-derived",
                encodingChanged=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["lineage-laundering", "encoding-does-not-upgrade-acquisition"],
        )
        self.assertIn("stage:shared-metadata", result["preservedResults"])
        self.assertIn("acquisition:SDR-derived", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "stage": "preview"},
            {**valid, "acquisition": "native-camera-equivalent"},
            {**valid, "containerBitDepth": True},
            {**valid, "visuallyFlat": "yes"},
            {k: v for k, v in valid.items() if k != "exportLabel"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
