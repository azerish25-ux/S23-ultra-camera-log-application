"""TC-P062-06 source-lineage laundering."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p062_tc06", Path(__file__).resolve().parents[1] / "gates" / "p062_tc06.py"
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
        "sampleId": "export-1",
        "stage": "export-name",
        "acquisition": "sdr",
        "claimedLabel": "raw-derived",
        "encodingChanged": True,
        "containerBits": 10,
        "visuallyFlat": True,
    }
    base.update(overrides)
    return base


class TcP06206(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P062-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Changing the encoding cannot upgrade the source acquisition category.",
        )

    def test_sdr_raw_label_is_rejected_when_ten_bit_and_flat(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["lineage-laundering", "encoding-cannot-upgrade"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertIn("claimed:raw-derived", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])
        self.assertIn("visually-flat:yes", result["preservedResults"])
        self.assertIn("export-1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "lineage_recorded"})

    def test_hlg_native_camera_label_is_rejected(self):
        result = evaluate(
            payload(
                sampleId="hlg-flat",
                acquisition="hlg",
                claimedLabel="native-camera-equivalent",
                stage="shared-metadata",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("lineage-laundering", result["rejectedClaims"])
        self.assertIn("native-camera-equivalence", result["rejectedClaims"])
        self.assertIn("acquisition:hlg", result["preservedResults"])
        self.assertIn("visually-flat:yes", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])

    def test_repeat_import_and_recipe(self):
        for stage in ("import", "recipe"):
            result = evaluate(payload(stage=stage, sampleId=stage))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"stage:{stage}", result["preservedResults"])
            self.assertIn("claimed:raw-derived", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_export_name_and_shared_metadata(self):
        for stage in ("export-name", "shared-metadata"):
            result = evaluate(payload(stage=stage, encodingChanged=False))
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(result["rejectedClaims"], ["lineage-laundering"])
            self.assertIn(f"stage:{stage}", result["preservedResults"])

    def test_encoding_change_cannot_upgrade_sdr_to_hlg(self):
        result = evaluate(payload(claimedLabel="hlg-derived", sampleId="enc"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["encoding-cannot-upgrade"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertIn("claimed:hlg-derived", result["preservedResults"])

    def test_matching_raw_label_is_not_qualification(self):
        result = evaluate(
            payload(acquisition="raw", claimedLabel="raw-derived", encodingChanged=False, sampleId="raw-ok")
        )
        self.assertEqual(result["decision"], "lineage_recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:raw", result["preservedResults"])
        self.assertIn("claimed:raw-derived", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "acquisition"},
            {**valid, "extra": True},
            {**valid, "containerBits": 12},
            {**valid, "containerBits": True},
            {**valid, "stage": "grade"},
            {**valid, "visuallyFlat": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
