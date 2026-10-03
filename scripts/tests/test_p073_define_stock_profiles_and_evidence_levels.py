"""Host checks for the P073 stock-profile catalogue. Not a physical S23 probe.

TC-P073-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p073_define_stock_profiles_and_evidence_levels import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    assess,
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
CURVE_A = "curve=0.12,0.4,1.1,2.4"
CURVE_B = "curve=0.18,0.55,1.35,2.1"


def load_document() -> dict:
    path = ROOT / "docs" / "P073_DEFINE_STOCK_PROFILES_AND_EVIDENCE_LEVELS.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _profile(preserved: list[str], profile_id: str) -> str:
    return next(item for item in preserved if item.startswith(f"profile:{profile_id}:"))


def _as_measured(profile: dict, parameter: str) -> None:
    profile["evidenceLevel"] = "measured"
    profile["confidence"] = "high"
    profile["sourceReferences"] = ["lab-wedge"]
    profile["measuredParameters"] = [parameter]
    profile["artisticControls"] = []


class P073StockProfileTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P073")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-stock-profiles-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("stock family", METHOD)
        self.assertIn("reconstructed artistic controls", METHOD)
        self.assertIn("stable profile identifiers", METHOD)
        self.assertIn("version every numerical change", METHOD)
        self.assertEqual(
            FIXTURE,
            "Two creative interpretations of the same nominal stock with different density curves "
            "and uncertain source data.",
        )
        self.assertEqual(
            ORACLE,
            "The catalogue exposes them as versioned interpretations rather than falsely identical "
            "calibrated materials.",
        )
        self.assertEqual(
            MUTANT,
            "Use a stock marketing name as proof that all numerical parameters are physically measured.",
        )

    def test_fixture_exposes_two_versioned_interpretations(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P073")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["nominalStock"], "vision-400")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "versioned_interpretations")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "rejected"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn("uncertain source data stays reconstructed or synthetic rather than measured", result["reasons"])
        self.assertIn(
            "vision-400-a version 1 and vision-400-b version 1 are distinct versioned interpretations",
            result["reasons"],
        )
        preserved = result["preservedResults"]
        self.assertIn("nominal:vision-400", preserved)
        first = _profile(preserved, "vision-400-a")
        second = _profile(preserved, "vision-400-b")
        self.assertIn("display=Vision 400", first)
        self.assertIn("display=Vision 400", second)
        self.assertIn(CURVE_A, first)
        self.assertIn(CURVE_B, second)
        self.assertIn("evidence=reconstructed", first)
        self.assertIn("evidence=synthetic", second)
        self.assertIn("confidence=low", first)
        self.assertIn("family=color-negative", first)
        self.assertIn("balance=daylight", second)
        self.assertIn("units=log-density", first)
        self.assertIn("licence=unspecified", second)
        self.assertIn("artistic=print-contrast", first)
        self.assertIn("artistic=shoulder-roll", second)
        self.assertIn("measured=none", first)
        self.assertIn("measured=none", second)
        self.assertIn("sources=uncertain-datasheet", first)
        self.assertIn("sources=uncertain-scan", second)
        self.assertIn("virtual=none", first)
        self.assertIn("appearance=none", second)
        self.assertNotIn("evidence=measured", " ".join(preserved))

    def test_mutant_marketing_name_does_not_prove_parameters_are_measured(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "versioned_interpretations")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["marketing-name-as-measurement"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "versioned_interpretations"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn(
            "a stock marketing name is not proof that numerical parameters are physically measured",
            mutant["reasons"],
        )
        self.assertIn("marketing name was rejected as measurement proof", mutant["openQuestions"])
        preserved = mutant["preservedResults"]
        self.assertIn(CURVE_A, _profile(preserved, "vision-400-a"))
        self.assertIn(CURVE_B, _profile(preserved, "vision-400-b"))
        self.assertIn("evidence=reconstructed", _profile(preserved, "vision-400-a"))
        self.assertIn("evidence=synthetic", _profile(preserved, "vision-400-b"))
        self.assertNotIn("evidence=measured", " ".join(preserved))
        self.assertEqual(
            [item for item in honest["preservedResults"] if item.startswith("profile:")],
            [item for item in preserved if item.startswith("profile:")],
        )

    def test_new_version_keeps_a_numerical_change_distinct(self) -> None:
        raw = load_document()
        raw["profiles"][1]["profileId"] = "vision-400-a"
        raw["profiles"][1]["version"] = "2"
        result = assess(raw)
        self.assertEqual(result["decision"], "versioned_interpretations")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("profile:vision-400-a:version=1:" in item and CURVE_A in item for item in result["preservedResults"]))
        self.assertTrue(any("profile:vision-400-a:version=2:" in item and CURVE_B in item for item in result["preservedResults"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_same_version_with_a_new_curve_is_rejected_and_kept(self) -> None:
        raw = load_document()
        raw["profiles"][1]["profileId"] = "vision-400-a"
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["vision-400-a+vision-400-a:unversioned-numerical-change"])
        self.assertIn(CURVE_A, result["preservedResults"][1])
        self.assertIn(CURVE_B, result["preservedResults"][2])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "versioned_interpretations"})

    def test_identical_measured_curves_are_not_one_calibrated_material(self) -> None:
        raw = load_document()
        raw["profiles"][1]["densityCurve"] = list(raw["profiles"][0]["densityCurve"])
        _as_measured(raw["profiles"][0], "density-toe")
        _as_measured(raw["profiles"][1], "density-toe")
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["vision-400-a+vision-400-b:falsely-identical-calibrated"],
        )
        self.assertIn("evidence=measured", _profile(result["preservedResults"], "vision-400-a"))
        self.assertIn("evidence=measured", _profile(result["preservedResults"], "vision-400-b"))
        self.assertIn(CURVE_A, _profile(result["preservedResults"], "vision-400-b"))

    def test_distinct_measured_curves_stay_versioned_and_unqualified(self) -> None:
        raw = load_document()
        _as_measured(raw["profiles"][0], "density-toe")
        _as_measured(raw["profiles"][1], "density-shoulder")
        result = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assertEqual(result["decision"], "versioned_interpretations")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("measured parameters stay attached to profile identifiers, not the display name", result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn("marketing-name-as-measurement", mutant["rejectedClaims"])
        self.assertNotIn(mutant["decision"], {"versioned_interpretations", "qualified", "allowed"})

    def test_false_measurement_virtual_format_and_nonmonotonic_keep_inventory(self) -> None:
        raw = load_document()
        raw["profiles"][0]["evidenceLevel"] = "measured"
        raw["profiles"][0]["virtualFormat"] = "log"
        raw["profiles"][0]["displayName"] = "vision-400-a"
        raw["profiles"][1]["densityCurve"] = ["0.2", "0.8", "0.3", "1.5"]
        raw["profiles"][1]["measuredParameters"] = ["shoulder-roll"]
        raw["profiles"][1]["confidence"] = "high"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            [
                "vision-400-a:display-name-collides-with-id",
                "vision-400-a:bound-to-virtual-format",
                "vision-400-a:false-measurement",
                "vision-400-b:nonmonotonic-density",
                "vision-400-b:measured-parameters-on-interpretation",
                "vision-400-b:artistic-as-measured",
                "vision-400-b:high-confidence-without-measurement",
            ],
        )
        self.assertIn("curve=0.2,0.8,0.3,1.5", _profile(result["preservedResults"], "vision-400-b"))
        self.assertIn("virtual=log", _profile(result["preservedResults"], "vision-400-a"))
        self.assertIn("evidence=synthetic", _profile(result["preservedResults"], "vision-400-b"))

    def test_appearance_binding_and_duplicate_bytes_are_rejected(self) -> None:
        raw = load_document()
        raw["profiles"][0]["appearanceId"] = "print-look"
        raw["profiles"][1] = copy.deepcopy(raw["profiles"][0])
        raw["profiles"][1]["profileId"] = "vision-400-a"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("vision-400-a:bound-to-appearance", result["rejectedClaims"])
        self.assertIn("vision-400-a+vision-400-a:duplicate-bytes", result["rejectedClaims"])
        self.assertEqual(len([item for item in result["preservedResults"] if item.startswith("profile:")]), 2)

    def test_one_profile_is_withheld_and_preserved(self) -> None:
        raw = load_document()
        raw["profiles"] = [raw["profiles"][0]]
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(CURVE_A, _profile(result["preservedResults"], "vision-400-a"))
        self.assertIn("nominal:vision-400", result["preservedResults"])
        self.assertTrue(any("two versioned interpretations" in item for item in result["openQuestions"]))

    def test_invalid_documents_and_paths_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P072"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bad_method = copy.deepcopy(valid)
        bad_method["method"] = "Use the marketing name as calibration."
        bad_density = copy.deepcopy(valid)
        bad_density["profiles"][0]["densityCurve"] = ["0.10", "0.4", "1.1", "2.4"]
        bad_version = copy.deepcopy(valid)
        bad_version["profiles"][0]["version"] = "01"
        bad_prefix = copy.deepcopy(valid)
        bad_prefix["profiles"][0]["profileId"] = "other-stock-a"
        empty = copy.deepcopy(valid)
        empty["profiles"] = []
        bool_schema = copy.deepcopy(valid)
        bool_schema["schemaVersion"] = True
        duplicate_source = copy.deepcopy(valid)
        duplicate_source["profiles"][0]["sourceReferences"] = ["uncertain-datasheet", "uncertain-datasheet"]
        bad_family = copy.deepcopy(valid)
        bad_family["profiles"][0]["family"] = "vision3"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bad_method,
            bad_density,
            bad_version,
            bad_prefix,
            empty,
            bool_schema,
            duplicate_source,
            bad_family,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, path="qualified")
        with self.assertRaises(ValueError):
            assess(valid, path="allowed")


if __name__ == "__main__":
    unittest.main()
