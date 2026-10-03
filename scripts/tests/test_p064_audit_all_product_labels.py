"""Host checks for the P064 product-label audit. Not a physical S23 probe.

TC-P064-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p064_audit_all_product_labels import (  # noqa: E402
    BASE_REVISION,
    CALIBRATION,
    CODEC,
    FIXTURE,
    HOST_LIMIT,
    LARGE_RECIPE,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_MODE,
    ORACLE,
    PHRASES,
    PRESET_NAME,
    PROCESSED,
    SDR_ORIGIN,
    VIRTUAL,
    assess,
    honest_export_label,
    mutant_export_label,
    preset_only_claims,
    validate_document,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def load_document() -> dict:
    path = ROOT / "docs" / "P064_AUDIT_ALL_PRODUCT_LABELS.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _acquisition(result: dict) -> list[str]:
    return [item for item in result["preservedResults"] if item.startswith("acquisition:")]


class P064ProductLabelTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P064")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-product-label-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("RAW-derived", METHOD)
        self.assertIn("HLG-derived", METHOD)
        self.assertIn("SDR-derived", METHOD)
        self.assertIn("provisional calibration", METHOD)
        self.assertIn("virtual format", METHOD)
        self.assertIn("processed look", METHOD)
        self.assertIn("sensor enlargement", METHOD)
        self.assertIn("guaranteed ARRI equivalence", METHOD)
        self.assertIn("recovered clipped detail", METHOD)
        self.assertEqual(FIXTURE, "A rendered SDR import exported with a large-format recipe and a ten-bit codec.")
        self.assertEqual(
            ORACLE,
            "The interface identifies a simulated look from an SDR source rather than "
            "native large-format or sensor-derived Log capture.",
        )
        self.assertEqual(MUTANT, "Build export labels only from the selected film preset name.")
        self.assertEqual(PRESET_NAME, "Large Format Log")
        self.assertEqual(CODEC, "Main10")
        self.assertEqual(LARGE_RECIPE, "large-format")
        self.assertEqual(SDR_ORIGIN, "rendered-sdr-import")
        self.assertEqual(CALIBRATION, "provisional-calibration")
        self.assertEqual(VIRTUAL, "virtual-format")
        self.assertEqual(PROCESSED, "processed-look")
        source = (ROOT / "scripts" / "gates" / "p064_audit_all_product_labels.py").read_text(encoding="utf-8")
        for index in range(1, 9):
            self.assertNotIn(f"p064_tc0{index}", source)

    def test_fixture_identifies_a_simulated_sdr_look(self) -> None:
        raw = load_document()
        before = copy.deepcopy(raw)
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw, before)
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P064")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(honest_export_label(raw), PHRASES["SDR-derived"])
        self.assertNotEqual(honest_export_label(raw), raw["export"]["presetName"])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "simulated_look")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(_acquisition(result), ["acquisition:SDR-derived"])
        self.assertIn("origin:rendered-sdr-import", result["preservedResults"])
        self.assertIn("transfer:Rec.709", result["preservedResults"])
        self.assertIn("recipe:large-format", result["preservedResults"])
        self.assertIn("preset:Large Format Log", result["preservedResults"])
        self.assertIn("codec:Main10", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])
        self.assertIn("visually-flat:true", result["preservedResults"])
        self.assertIn("category:SDR-derived", result["preservedResults"])
        self.assertIn("calibration:provisional-calibration", result["preservedResults"])
        self.assertIn("format:virtual-format", result["preservedResults"])
        self.assertIn("look:processed-look", result["preservedResults"])
        self.assertIn("surfaces:select,export,share", result["preservedResults"])
        self.assertIn("wording:" + PHRASES["SDR-derived"], result["preservedResults"])
        self.assertIn("marketing:sensor-enlargement:false", result["preservedResults"])
        self.assertIn("marketing:arri-equivalence:false", result["preservedResults"])
        self.assertIn("marketing:recovered-clipped-detail:false", result["preservedResults"])
        self.assertIn("evidence:machine-readable:true", result["preservedResults"])
        self.assertIn("evidence:ui-matches:true", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(PHRASES["SDR-derived"], result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertTrue(any("flat ten-bit" in item for item in result["openQuestions"]))
        self.assertEqual(raw, before)

    def test_mutant_preset_only_labels_are_rejected(self) -> None:
        raw = load_document()
        honest = assess(raw)
        self.assertEqual(mutant_export_label(raw), "Large Format Log")
        self.assertEqual(
            preset_only_claims("Large Format Log"),
            ["preset-only-label", "native-large-format", "sensor-derived-log"],
        )
        mutant = assess(raw, interpretation=MUTANT_MODE)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "simulated_look")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(
            mutant["rejectedClaims"],
            ["preset-only-label", "native-large-format", "sensor-derived-log"],
        )
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "simulated_look"})
        self.assertEqual(_acquisition(honest), _acquisition(mutant))
        self.assertEqual(_acquisition(mutant), ["acquisition:SDR-derived"])
        self.assertIn("preset:Large Format Log", mutant["preservedResults"])
        self.assertNotIn("acquisition:Large Format Log", mutant["preservedResults"])
        self.assertNotIn("acquisition:native-large-format", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("mutant interpretation rejected", mutant["openQuestions"])
        self.assertIn("codec:Main10", mutant["preservedResults"])
        self.assertIn("container-bits:10", mutant["preservedResults"])

    def test_marketing_claims_stay_rejected_and_keep_the_source(self) -> None:
        raw = load_document()
        raw["marketing"]["sensorEnlargement"] = True
        raw["marketing"]["guaranteedArriEquivalence"] = True
        raw["marketing"]["recoveredClippedDetail"] = True
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["sensor-enlargement", "guaranteed-arri-equivalence", "recovered-clipped-detail"],
        )
        self.assertEqual(_acquisition(result), ["acquisition:SDR-derived"])
        self.assertIn("preset:Large Format Log", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "simulated_look"})

    def test_native_sensor_format_and_missing_surface_keep_sdr(self) -> None:
        raw = load_document()
        raw["wording"]["formatKind"] = "native-sensor"
        raw["wording"]["surfaces"] = ["select", "export"]
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-surface", result["rejectedClaims"])
        self.assertIn("format-not-virtual", result["rejectedClaims"])
        self.assertIn("surfaces:select,export", result["preservedResults"])
        self.assertEqual(_acquisition(result), ["acquisition:SDR-derived"])
        self.assertNotIn("surfaces:select,export,share", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "simulated_look"})

    def test_label_that_disagrees_with_evidence_is_rejected(self) -> None:
        raw = load_document()
        raw["evidence"]["uiMatchesEvidence"] = False
        raw["wording"]["category"] = "RAW-derived"
        raw["wording"]["text"] = PHRASES["RAW-derived"]
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("label-evidence-mismatch", result["rejectedClaims"])
        self.assertIn("category-mismatch", result["rejectedClaims"])
        self.assertIn("acquisition:SDR-derived", result["preservedResults"])
        self.assertIn("category:RAW-derived", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "simulated_look"})

    def test_honest_raw_wording_is_withheld_not_qualified(self) -> None:
        raw = load_document()
        raw["source"]["acquisition"] = "RAW-derived"
        raw["source"]["origin"] = "saved-raw"
        raw["source"]["transfer"] = "LogC3"
        raw["wording"]["category"] = "RAW-derived"
        raw["wording"]["text"] = PHRASES["RAW-derived"]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("acquisition:RAW-derived", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "simulated_look"})
        mutant = assess(raw, interpretation=MUTANT_MODE)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn("acquisition:RAW-derived", mutant["preservedResults"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "simulated_look"})

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P063"
        bad_method = copy.deepcopy(valid)
        bad_method["method"] = "Build export labels only from the selected film preset name."
        bad_depth = copy.deepcopy(valid)
        bad_depth["export"]["containerBitDepth"] = True
        bad_surface = copy.deepcopy(valid)
        bad_surface["wording"]["surfaces"] = ["select", "select"]
        empty_surfaces = copy.deepcopy(valid)
        empty_surfaces["wording"]["surfaces"] = []
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_method,
            bad_depth,
            bad_surface,
            empty_surfaces,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, interpretation="qualified")
        with self.assertRaises(ValueError):
            assess(valid, interpretation="allowed")


if __name__ == "__main__":
    unittest.main()
