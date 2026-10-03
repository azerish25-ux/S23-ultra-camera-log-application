"""TC-P061-06 source-lineage laundering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p061_tc06", Path(__file__).resolve().parents[1] / "gates" / "p061_tc06.py"
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
        "acquisition": "hlg-derived",
        "exportLabel": "RAW-derived",
        "containerBits": 10,
        "visuallyFlat": True,
        "stage": "export-name",
    }
    base.update(overrides)
    return base


class TcP06106(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P061-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("RAW-derived", _MODULE.INTERVENTION)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Changing the encoding cannot upgrade the source acquisition category.",
        )
        self.assertIn("import", _MODULE.REPEAT)
        self.assertIn("shared metadata", _MODULE.REPEAT)

    def test_ten_bit_flat_hlg_is_not_raw(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["lineage-laundering", "encoding-cannot-upgrade"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:hlg-derived", result["preservedResults"])
        self.assertIn("bits:10", result["preservedResults"])
        self.assertIn("flat:true", result["preservedResults"])
        self.assertIn("label:RAW-derived", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "lineage_kept"})

    def test_honest_hlg_label_is_kept(self):
        result = evaluate(payload(exportLabel="hlg-derived", visuallyFlat=False, containerBits=8))
        self.assertEqual(result["decision"], "lineage_kept")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:hlg-derived", result["preservedResults"])

    def test_repeat_import_and_recipe(self):
        for stage in ("import", "recipe"):
            result = evaluate(payload(acquisition="sdr", exportLabel="native-camera-equivalent", stage=stage))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"stage:{stage}", result["preservedResults"])
            self.assertIn("acquisition:sdr", result["preservedResults"])
            self.assertIn("encoding-cannot-upgrade", result["rejectedClaims"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_shared_metadata(self):
        result = evaluate(payload(stage="shared-metadata", exportLabel="native-camera-equivalent"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stage:shared-metadata", result["preservedResults"])
        self.assertIn("bits:10", result["preservedResults"])
        self.assertIn("flat:true", result["preservedResults"])

    def test_raw_label_on_raw_sensor_is_not_qualification(self):
        result = evaluate(payload(acquisition="raw-sensor", exportLabel="RAW-derived", stage="import"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:raw-sensor", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "containerBits": 12},
            {**valid, "visuallyFlat": "yes"},
            {**valid, "stage": "preview"},
            {**valid, "exportLabel": "log"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
