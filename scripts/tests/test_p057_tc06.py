"""TC-P057-06 encoding changes do not upgrade acquisition lineage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p057_tc06", Path(__file__).resolve().parents[1] / "gates" / "p057_tc06.py"
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
        "stage": "import",
        "acquisition": "sdr",
        "label": "raw-derived",
        "containerBits": 10,
        "visuallyFlat": True,
    }
    base.update(overrides)
    return base


class TcP05706(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P057-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_import_cannot_relabel_sdr_as_raw(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["lineage-upgrade", "stage:import"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("acquisition:sdr", result["preservedResults"])
        self.assertIn("label:raw-derived", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])
        self.assertIn("visually-flat:true", result["preservedResults"])

    def test_repeat_export_name_of_hlg_as_native_equivalent(self):
        result = evaluate(
            payload(
                stage="export-name",
                acquisition="hlg",
                label="native-camera-equivalent",
                visuallyFlat=True,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("stage:export-name", result["rejectedClaims"])
        self.assertIn("acquisition:hlg", result["preservedResults"])
        self.assertIn("label:native-camera-equivalent", result["preservedResults"])
        self.assertTrue(any("visually flat" in item for item in result["reasons"]))

    def test_repeat_recipe_and_shared_metadata(self):
        for stage in ("recipe", "shared-metadata"):
            result = evaluate(payload(stage=stage, containerBits=8, visuallyFlat=False))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"stage:{stage}", result["preservedResults"])
            self.assertIn("acquisition:sdr", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_raw_label_on_raw_acquisition_is_not_a_qualification(self):
        result = evaluate(payload(acquisition="raw", label="raw-derived", stage="export-name"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:raw", result["preservedResults"])
        self.assertIn("label:raw-derived", result["preservedResults"])

    def test_matching_sdr_label_stays_withheld(self):
        result = evaluate(payload(label="sdr", visuallyFlat=False, containerBits=8))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("label:sdr", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "stage": "grade"},
            {**valid, "acquisition": "log"},
            {**valid, "containerBits": True},
            {**valid, "visuallyFlat": "yes"},
            {k: v for k, v in valid.items() if k != "label"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
