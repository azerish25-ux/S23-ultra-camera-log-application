"""TC-P060-06 source-lineage laundering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p060_tc06", Path(__file__).resolve().parents[1] / "gates" / "p060_tc06.py"
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
        "acquisition": "sdr",
        "exportLabel": "raw-derived",
        "containerBitDepth": "10",
        "visuallyFlat": True,
    }
    base.update(overrides)
    return base


class TcP06006(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P060-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("RAW-derived", _MODULE.INTERVENTION)
        self.assertIn("cannot upgrade", _MODULE.NEGATIVE)

    def test_ten_bit_flat_sdr_raw_label_is_rejected(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["laundered-source-lineage"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertIn("label:raw-derived", result["preservedResults"])
        self.assertIn("depth:10", result["preservedResults"])
        self.assertIn("visually-flat:yes", result["preservedResults"])

    def test_hlg_native_camera_label_is_rejected(self):
        result = evaluate(
            payload(acquisition="hlg", exportLabel="native-camera-equivalent", visuallyFlat=False)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("acquisition:hlg", result["preservedResults"])
        self.assertIn("label:native-camera-equivalent", result["preservedResults"])

    def test_repeat_import_stage(self):
        result = evaluate(payload(stage="import"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stage:import", result["preservedResults"])
        self.assertIn("acquisition:sdr", result["preservedResults"])

    def test_repeat_recipe_and_shared_metadata(self):
        for stage in ("recipe", "shared-metadata"):
            result = evaluate(payload(stage=stage, containerBitDepth="8", visuallyFlat=False))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"stage:{stage}", result["preservedResults"])
            self.assertIn("depth:8", result["preservedResults"])

    def test_honest_label_does_not_upgrade_or_qualify(self):
        result = evaluate(payload(exportLabel="sdr", visuallyFlat=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertIn("label:sdr", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "stage": "grade"},
            {**valid, "visuallyFlat": "yes"},
            {**valid, "containerBitDepth": "12"},
            {k: v for k, v in valid.items() if k != "acquisition"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
