"""Host checks for the P020 white-balance intent model. Not a physical S23 probe.

TC-P020-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p020_implement_stable_white_balance_controls import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    METHOD,
    MODEL_ID,
    MUTANT,
    ORACLE,
    assess_balance,
    project_balance,
    validate_model,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
HANDOFF_KEYS = (
    "phase",
    "caseIds",
    "changedFiles",
    "commit",
    "testsRun",
    "failures",
    "unverified",
    "nextPhase",
)
GAINS = "1.84,1.00,1.00,1.52"
POINT = "0.543,1.00,0.66"


def load_fixture() -> dict:
    path = ROOT / "docs" / "P020_IMPLEMENT_STABLE_WHITE_BALANCE_CONTROLS.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P020-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P020WhiteBalanceTests(unittest.TestCase):
    def test_fixture_encodes_method_oracle_mutant_and_base_revision(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_model(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P020")
        self.assertEqual(raw["modelId"], MODEL_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertIn("creative warm preview", raw["fixture"])
        self.assertIn("unsupported hardware Kelvin", raw["fixture"])
        self.assertFalse(raw["hardware"]["kelvinSupported"])
        self.assertFalse(raw["hardware"]["independentlyCalibrated"])
        self.assertEqual(raw["hardware"]["kelvinRequest"], "5600")
        self.assertEqual(raw["hardware"]["selectedPreset"], "daylight")
        self.assertTrue(raw["hardware"]["locked"])
        self.assertTrue(raw["hardware"]["transformAccessible"])
        self.assertEqual(raw["hardware"]["gains"]["red"], "1.84")
        self.assertEqual(raw["preview"]["creativeTemperature"], "warm")
        self.assertEqual(raw["preview"]["creativeKelvinSlider"], "3200")
        self.assertEqual(raw["preview"]["tintSlider"], "plus_8")
        self.assertTrue(raw["preview"]["recordsAdjustment"])
        self.assertFalse(raw["preview"]["writesCaptureMetadata"])
        self.assertTrue(raw["rawNeutral"]["sourceMetadataUnchanged"])
        self.assertEqual(raw["rawNeutral"]["profileVersion"], "neutral-v1")
        self.assertNotEqual(raw["preview"]["creativeKelvinSlider"], raw["hardware"]["kelvinRequest"])

    def test_projection_keeps_capture_and_look_apart(self) -> None:
        raw = load_fixture()
        projected = project_balance(raw)
        self.assertEqual(projected["hardware"]["namespace"], "hardware.white_balance")
        self.assertEqual(projected["rawNeutral"]["namespace"], "raw.neutral")
        self.assertEqual(projected["previewRecipe"]["namespace"], "preview.recipe")
        self.assertEqual(projected["hardware"]["kelvin"], "unavailable")
        self.assertEqual(projected["hardware"]["gains"]["blue"], "1.52")
        self.assertEqual(projected["rawNeutral"]["point"], POINT)
        self.assertTrue(projected["rawNeutral"]["sourceMetadataUnchanged"])
        self.assertEqual(projected["previewRecipe"]["creativeKelvinSlider"], "3200")
        self.assertEqual(projected["previewRecipe"]["creativeTemperature"], "warm")
        self.assertFalse(projected["previewRecipe"]["writesCaptureMetadata"])
        measured = projected["measuredSensorWhiteBalance"]
        self.assertEqual(measured["source"], "hardware")
        self.assertEqual(measured["preset"], "daylight")
        self.assertEqual(measured["kelvin"], "unavailable")
        self.assertEqual(measured["gains"], GAINS)
        self.assertNotIn("creativeKelvinSlider", measured)
        self.assertNotIn("3200", measured["kelvin"])
        self.assertNotIn("warm", measured["kelvin"])

    def test_honest_fixture_is_separated_and_keeps_the_oracle(self) -> None:
        raw = load_fixture()
        result = assess_balance(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P020")
        self.assertEqual(result["decision"], "separated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("raw.point:" + POINT, result["preservedResults"])
        self.assertIn("raw.sourceMetadata:unchanged", result["preservedResults"])
        self.assertIn("preview.creativeKelvinSlider:3200", result["preservedResults"])
        self.assertIn("preview.temperature:warm", result["preservedResults"])
        self.assertIn("preview.tint:plus_8", result["preservedResults"])
        self.assertIn("measured.kelvin:unavailable", result["preservedResults"])
        self.assertIn("hardware.gains:" + GAINS, result["preservedResults"])
        self.assertIn("hardware.preset:daylight", result["preservedResults"])
        self.assertTrue(any("source metadata stays unchanged" in item for item in result["reasons"]))
        self.assertTrue(any("preview recipe records its adjustment" in item for item in result["reasons"]))
        self.assertTrue(any("unsupported Kelvin remains unavailable" in item for item in result["reasons"]))
        self.assertIn("unsupported hardware Kelvin remains unavailable", result["openQuestions"])
        self.assertIn(
            "Kelvin values are provisional unless independently calibrated",
            result["openQuestions"],
        )

    def test_mutant_is_rejected_and_does_not_overwrite_measured_evidence(self) -> None:
        raw = load_fixture()
        honest = assess_balance(raw, mutant=False)
        poisoned = assess_balance(raw, mutant=True)
        self.assertEqual(poisoned["decision"], "rejected")
        self.assertNotIn(poisoned["decision"], {"qualified", "allowed", "separated"})
        self.assertEqual(poisoned["rejectedClaims"], ["creative-temperature-as-measured-wb"])
        self.assertEqual(honest["preservedResults"], poisoned["preservedResults"])
        self.assertIn("measured.kelvin:unavailable", poisoned["preservedResults"])
        self.assertIn("measured.gains:" + GAINS, poisoned["preservedResults"])
        self.assertIn("preview.creativeKelvinSlider:3200", poisoned["preservedResults"])
        self.assertIn("preview.temperature:warm", poisoned["preservedResults"])
        self.assertNotIn("measured.kelvin:3200", poisoned["preservedResults"])
        self.assertNotIn("measured.kelvin:warm", poisoned["preservedResults"])
        for item in poisoned["preservedResults"]:
            if item.startswith("measured."):
                self.assertNotIn("3200", item)
                self.assertNotIn("warm", item)
        self.assertTrue(any(item == MUTANT for item in poisoned["reasons"]))
        self.assertTrue(
            any("was not written into measured sensor white-balance" in item for item in poisoned["reasons"])
        )
        self.assertIn("raw.point:" + POINT, poisoned["preservedResults"])
        self.assertEqual(honest["decision"], "separated")

    def test_creative_tint_that_writes_capture_metadata_is_rejected(self) -> None:
        raw = load_fixture()
        raw["preview"]["writesCaptureMetadata"] = True
        result = assess_balance(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "separated"})
        self.assertIn("creative-tint-wrote-capture-metadata", result["rejectedClaims"])
        self.assertIn("raw.point:" + POINT, result["preservedResults"])
        self.assertIn("raw.sourceMetadata:unchanged", result["preservedResults"])
        self.assertIn("measured.kelvin:unavailable", result["preservedResults"])
        self.assertIn("preview.tint:plus_8", result["preservedResults"])

    def test_unversioned_raw_neutral_change_is_rejected_and_the_point_remains(self) -> None:
        raw = load_fixture()
        raw["rawNeutral"]["sourceMetadataUnchanged"] = False
        raw["rawNeutral"]["red"] = "0.400"
        result = assess_balance(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unversioned-raw-neutral", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("raw.point:0.400,1.00,0.66", result["preservedResults"])
        self.assertIn("raw.profile:neutral-v1", result["preservedResults"])
        self.assertIn("raw.priorProfile:neutral-v1", result["preservedResults"])
        self.assertIn("raw.sourceMetadata:changed", result["preservedResults"])
        self.assertIn("preview.creativeKelvinSlider:3200", result["preservedResults"])

    def test_versioned_profile_change_is_not_qualification(self) -> None:
        raw = load_fixture()
        raw["rawNeutral"]["sourceMetadataUnchanged"] = False
        raw["rawNeutral"]["profileVersion"] = "neutral-v2"
        raw["rawNeutral"]["red"] = "0.400"
        result = assess_balance(raw)
        self.assertEqual(result["decision"], "versioned")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("raw.profile:neutral-v2", result["preservedResults"])
        self.assertIn("raw.priorProfile:neutral-v1", result["preservedResults"])
        self.assertIn("raw.point:0.400,1.00,0.66", result["preservedResults"])
        self.assertTrue(any("neutral-v2" in item for item in result["openQuestions"]))

    def test_supported_but_uncalibrated_kelvin_is_withheld(self) -> None:
        raw = load_fixture()
        raw["hardware"]["kelvinSupported"] = True
        result = assess_balance(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "separated"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("measured.kelvin:provisional:5600", result["preservedResults"])
        self.assertNotIn("measured.kelvin:3200", result["preservedResults"])
        self.assertIn("preview.creativeKelvinSlider:3200", result["preservedResults"])
        self.assertIn("raw.sourceMetadata:unchanged", result["preservedResults"])
        self.assertTrue(any("provisional" in item for item in result["reasons"]))

    def test_calibrated_kelvin_is_still_not_the_creative_slider(self) -> None:
        raw = load_fixture()
        raw["hardware"]["kelvinSupported"] = True
        raw["hardware"]["independentlyCalibrated"] = True
        result = assess_balance(raw, mutant=True)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("measured.kelvin:calibrated:5600", result["preservedResults"])
        self.assertIn("preview.creativeKelvinSlider:3200", result["preservedResults"])
        self.assertNotIn("measured.kelvin:3200", result["preservedResults"])
        self.assertEqual(project_balance(raw)["measuredSensorWhiteBalance"]["kelvin"], "calibrated:5600")

    def test_inaccessible_gains_are_not_invented(self) -> None:
        raw = load_fixture()
        raw["hardware"]["transformAccessible"] = False
        raw["hardware"]["gains"] = None
        raw["hardware"]["colorTransform"] = None
        result = assess_balance(raw)
        self.assertEqual(result["decision"], "separated")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("hardware.gains:unavailable", result["preservedResults"])
        self.assertIn("measured.gains:unavailable", result["preservedResults"])
        self.assertIn("hardware.transform:unavailable", result["preservedResults"])
        self.assertNotIn("hardware.gains:" + GAINS, result["preservedResults"])
        self.assertIn("gains and transforms were not accessible", result["openQuestions"])
        self.assertIn("raw.point:" + POINT, result["preservedResults"])

    def test_missing_preview_record_is_rejected(self) -> None:
        raw = load_fixture()
        raw["preview"]["recordsAdjustment"] = False
        result = assess_balance(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("preview-adjustment-unrecorded", result["rejectedClaims"])
        self.assertIn("measured.kelvin:unavailable", result["preservedResults"])
        self.assertIn("raw.sourceMetadata:unchanged", result["preservedResults"])

    def test_invalid_models_raise(self) -> None:
        valid = load_fixture()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P019"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "fffd5c9a63cb732e103052acae29ae0c251585cc"
        wrong_method = copy.deepcopy(valid)
        wrong_method["method"] = "copy the slider into the sensor"
        calibrated_without_support = copy.deepcopy(valid)
        calibrated_without_support["hardware"]["independentlyCalibrated"] = True
        float_gain = copy.deepcopy(valid)
        float_gain["hardware"]["gains"]["red"] = 1.84
        bad_preset = copy.deepcopy(valid)
        bad_preset["hardware"]["selectedPreset"] = "tungsten"
        version_lie = copy.deepcopy(valid)
        version_lie["rawNeutral"]["profileVersion"] = "neutral-v2"
        collapsed = copy.deepcopy(valid)
        collapsed["preview"]["namespace"] = "hardware.white_balance"
        inaccessible_with_gains = copy.deepcopy(valid)
        inaccessible_with_gains["hardware"]["transformAccessible"] = False
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            wrong_method,
            calibrated_without_support,
            float_gain,
            bad_preset,
            version_lie,
            collapsed,
            inaccessible_with_gains,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_model(sample)
        with self.assertRaises(ValueError):
            assess_balance(valid, mutant="true")

    def test_doc_and_handoff_state_the_host_limit(self) -> None:
        note = (ROOT / "docs" / "P020_IMPLEMENT_STABLE_WHITE_BALANCE_CONTROLS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("host fixture", note.lower())
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p020*.py' -v",
            note,
        )
        self.assertIn("Non-claims", note)
        self.assertIn("physical", note.lower())
        self.assertIn("assess_balance", note)
        handoff = load_handoff()
        self.assertEqual(tuple(handoff), HANDOFF_KEYS)
        self.assertEqual(handoff["phase"], "P020")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(handoff["nextPhase"], "blocked")
        self.assertEqual(handoff["caseIds"], [f"TC-P020-0{index}" for index in range(1, 9)])
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p020*.py' -v",
            handoff["testsRun"],
        )
        self.assertTrue(any("physical S23" in item for item in handoff["unverified"]))
        self.assertIn(
            "scripts/gates/p020_implement_stable_white_balance_controls.py",
            handoff["changedFiles"],
        )


if __name__ == "__main__":
    unittest.main()
