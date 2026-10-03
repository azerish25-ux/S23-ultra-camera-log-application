"""Host checks for the P046 illuminant-adaptation fixture. Not a physical S23 probe.

TC-P046-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p046_implement_illuminant_adaptation_carefully import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    CONDITION_LIMIT,
    DECLARED,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    condition_fraction,
    validate_document,
    von_kries_gains,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
PRESERVED = [
    "scene:daylight+narrow-band-colored-led:mixed=true",
    "neutral:global-neutral:global:1200,1000,800:patch=daylight-gray",
    "endpoint:reference-white:daylight:row-camera-to-xyz:neutral=1000,1000,1000:"
    "matrix=2,1,0,0,2,1,1,0,2:cond=7/3:response=3000,3000,3000",
    "endpoint:spectral-sensitivity:narrow-band-led:row-camera-to-xyz:neutral=400,1000,200:"
    "matrix=5,0,0,0,3,0,0,0,4:cond=5/3:response=2000,3000,800",
    "adaptation:von-kries-reference-white:5/6,1/1,5/4",
    "spectral-sensitivity:narrow-band-led:unchanged",
    "interpolation:not-requested",
]
LERP = "element-lerp:1/2:7/2,1/2,0/1,0/1,5/2,1/2,1/2,0/1,3/1"
DAYLIGHT = {
    "id": "daylight",
    "role": "reference-white",
    "convention": "row-camera-to-xyz",
    "neutral": ["1000", "1000", "1000"],
    "matrix": [["2", "1", "0"], ["0", "2", "1"], ["1", "0", "2"]],
}
TUNGSTEN = {
    "id": "tungsten",
    "role": "reference-white",
    "convention": "row-camera-to-xyz",
    "neutral": ["900", "1000", "1100"],
    "matrix": [["4", "1", "0"], ["1", "4", "1"], ["0", "1", "4"]],
}


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P046_IMPLEMENT_ILLUMINANT_ADAPTATION_CAREFULLY.json").read_text(
            encoding="utf-8"
        )
    )


def single_daylight(raw: dict) -> dict:
    document = copy.deepcopy(raw)
    document["scene"] = {"illuminants": ["daylight"], "mixed": False}
    document["endpoints"] = [copy.deepcopy(DAYLIGHT)]
    return document


class P046IlluminantAdaptationTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P046")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P046")
        self.assertEqual(MAP_ID, "s23-illuminant-adaptation-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertEqual(DECLARED, "von-kries-reference-white")
        self.assertEqual(CONDITION_LIMIT, (20, 1))
        self.assertIn("endpoint matrix and neutral vector", METHOD)
        self.assertIn("Mixed illumination remains a limitation", METHOD)
        self.assertEqual(
            FIXTURE,
            "A scene containing daylight and narrow-band colored LEDs with one global "
            "neutral measurement.",
        )
        self.assertEqual(
            ORACLE,
            "The pipeline applies only its declared adaptation and labels the mixed-light "
            "color uncertainty rather than claiming universal matching.",
        )
        self.assertEqual(
            MUTANT,
            "Interpolate arbitrary matrix elements without checking endpoint conventions "
            "or neutral response.",
        )

    def test_fixture_labels_mixed_light_and_keeps_the_spectral_model(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P046")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(condition_fraction([[2, 1, 0], [0, 2, 1], [1, 0, 2]]), (7, 3))
        self.assertEqual(condition_fraction([[5, 0, 0], [0, 3, 0], [0, 0, 4]]), (5, 3))
        self.assertEqual(von_kries_gains([1000, 1000, 1000], [1200, 1000, 800]), ["5/6", "1/1", "5/4"])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "adaptation_limited")
        self.assertEqual(
            result["rejectedClaims"],
            ["universal-matching", "spectral-sensitivity-rewrite"],
        )
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn("spectral-sensitivity:narrow-band-led:unchanged", result["preservedResults"])
        self.assertNotIn(LERP, result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("conditioning daylight 7/3, narrow-band-led 5/3", result["reasons"])
        self.assertIn(
            "declared adaptation von-kries-reference-white:5/6,1/1,5/4 leaves spectral sensitivity unchanged",
            result["reasons"],
        )
        self.assertIn(
            "mixed-light color uncertainty remains; one global neutral does not solve arbitrary spectra",
            result["reasons"],
        )
        self.assertIn("interpolation was not applied", result["reasons"])
        self.assertIn("reference white vector, distinct from a camera spectral sensitivity model",
                      " ".join(result["reasons"]))
        self.assertIn("distinct from reference-white adaptation", " ".join(result["reasons"]))
        self.assertEqual(
            result["openQuestions"],
            [
                "mixed illumination is not solved by one global neutral",
                "host fixture is not a physical S23 measurement",
            ],
        )
        self.assertTrue(any("does not qualify a physical S23" in item for item in result["reasons"]))
        self.assertNotIn(MUTANT, result["reasons"])

    def test_mutant_unchecked_interpolation_is_rejected(self) -> None:
        raw = load_document()
        result = assess(raw, sole_test="unchecked-element-interpolation")
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(
            result["decision"],
            {"qualified", "allowed", "adaptation_limited", "adaptation_declared", "matched"},
        )
        self.assertEqual(
            result["rejectedClaims"],
            [
                "unchecked-element-interpolation",
                "endpoint-convention-not-checked",
                "neutral-response-not-checked",
                LERP,
                "universal-matching",
                "spectral-sensitivity-rewrite",
            ],
        )
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertNotIn(LERP, result["preservedResults"])
        self.assertIn("adaptation:von-kries-reference-white:5/6,1/1,5/4", result["preservedResults"])
        self.assertIn("spectral-sensitivity:narrow-band-led:unchanged", result["preservedResults"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn("element interpolation was not installed as the adaptation", result["reasons"])
        self.assertEqual(result["openQuestions"][0], "unchecked element interpolation was rejected")

    def test_mutant_does_not_replace_a_checked_reference_white_domain(self) -> None:
        raw = load_document()
        raw["scene"] = {"illuminants": ["daylight"], "mixed": False}
        raw["neutralMeasurement"]["channels"] = ["1000", "1000", "1000"]
        raw["endpoints"] = [DAYLIGHT, TUNGSTEN, raw["endpoints"][1]]
        raw["interpolation"] = {
            "requested": True,
            "weightNumerator": "1",
            "weightDenominator": "2",
            "checkedConventions": True,
            "checkedNeutralResponse": True,
        }
        honest = assess(raw)
        mutant = assess(raw, sole_test="unchecked-element-interpolation")
        self.assertEqual(honest["decision"], "adaptation_declared")
        self.assertNotIn(honest["decision"], {"qualified", "allowed"})
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn(
            "element-lerp:1/2:3/1,1/1,0/1,1/2,3/1,1/1,1/2,1/2,3/1",
            mutant["rejectedClaims"],
        )
        self.assertNotIn(
            "element-lerp:1/2:3/1,1/1,0/1,1/2,3/1,1/1,1/2,1/2,3/1",
            mutant["preservedResults"],
        )
        self.assertIn("adaptation:von-kries-reference-white:1/1,1/1,1/1", mutant["preservedResults"])
        self.assertIn("spectral-sensitivity:narrow-band-led:unchanged", mutant["preservedResults"])
        self.assertTrue(mutant["preservedResults"][-1].startswith("interpolation:valid:"))
        self.assertIn("matrix=5,0,0,0,3,0,0,0,4", "".join(mutant["preservedResults"]))

    def test_requested_interpolation_without_checks_is_rejected(self) -> None:
        raw = single_daylight(load_document())
        raw["interpolation"] = {
            "requested": True,
            "weightNumerator": "1",
            "weightDenominator": "2",
            "checkedConventions": False,
            "checkedNeutralResponse": True,
        }
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "adaptation_declared"})
        self.assertIn("unchecked-element-interpolation", result["rejectedClaims"])
        self.assertIn("endpoint-convention-not-checked", result["rejectedClaims"])
        self.assertNotIn("neutral-response-not-checked", result["rejectedClaims"])
        self.assertIn(MUTANT, result["reasons"])

    def test_singular_interpolation_domain_is_rejected(self) -> None:
        raw = single_daylight(load_document())
        raw["neutralMeasurement"]["channels"] = ["1", "1", "1"]
        raw["endpoints"] = [
            {
                "id": "white-a",
                "role": "reference-white",
                "convention": "row-camera-to-xyz",
                "neutral": ["1", "1", "1"],
                "matrix": [["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"]],
            },
            {
                "id": "white-b",
                "role": "reference-white",
                "convention": "row-camera-to-xyz",
                "neutral": ["1", "1", "1"],
                "matrix": [["1", "2", "0"], ["2", "1", "0"], ["0", "0", "1"]],
            },
        ]
        raw["interpolation"] = {
            "requested": True,
            "weightNumerator": "1",
            "weightDenominator": "2",
            "checkedConventions": True,
            "checkedNeutralResponse": True,
        }
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"][0], "singular-domain:1/2")
        self.assertIn("interpolation:invalid:singular-domain", result["preservedResults"])
        self.assertIn("adaptation:von-kries-reference-white:1/1,1/1,1/1", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_ill_conditioned_endpoint_keeps_its_matrix(self) -> None:
        raw = single_daylight(load_document())
        raw["neutralMeasurement"]["channels"] = ["1", "1", "1"]
        raw["endpoints"][0]["id"] = "near-white"
        raw["endpoints"][0]["neutral"] = ["1", "1", "1"]
        raw["endpoints"][0]["matrix"] = [["100", "99", "0"], ["99", "98", "0"], ["0", "0", "1"]]
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("ill-conditioned:near-white", result["rejectedClaims"])
        self.assertTrue(
            any("cond=39601/1" in item and "matrix=100,99,0,99,98,0,0,0,1" in item
                for item in result["preservedResults"])
        )
        self.assertIn("interpolation:invalid:endpoint", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_single_illuminant_is_declared_not_qualified(self) -> None:
        result = assess(single_daylight(load_document()))
        self.assertEqual(result["decision"], "adaptation_declared")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["universal-matching"])
        self.assertIn("scene:daylight:mixed=false", result["preservedResults"])
        self.assertNotIn("spectral-sensitivity-rewrite", result["rejectedClaims"])
        self.assertIn(
            "declared adaptation is not a camera spectral-sensitivity measurement",
            result["openQuestions"],
        )

    def test_missing_reference_white_is_withheld(self) -> None:
        raw = load_document()
        raw["scene"] = {"illuminants": ["daylight"], "mixed": False}
        raw["endpoints"] = [raw["endpoints"][1]]
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("missing-reference-white", result["rejectedClaims"])
        self.assertIn("adaptation:unavailable", result["preservedResults"])
        self.assertIn("spectral-sensitivity:narrow-band-led:unchanged", result["preservedResults"])

    def test_non_global_neutral_is_withheld(self) -> None:
        raw = single_daylight(load_document())
        raw["neutralMeasurement"]["scope"] = "local"
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"][0], "non-global-neutral")
        self.assertIn("neutral:global-neutral:local:1200,1000,800:patch=daylight-gray",
                      result["preservedResults"])

    def test_mixed_request_does_not_become_universal_matching(self) -> None:
        raw = load_document()
        raw["endpoints"] = [DAYLIGHT, TUNGSTEN, raw["endpoints"][1]]
        raw["interpolation"] = {
            "requested": True,
            "weightNumerator": "1",
            "weightDenominator": "2",
            "checkedConventions": True,
            "checkedNeutralResponse": True,
        }
        result = assess(raw)
        self.assertEqual(result["decision"], "adaptation_limited")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("interpolation:invalid:mixed-illumination", result["preservedResults"])
        self.assertIn("universal-matching", result["rejectedClaims"])
        self.assertIn("interpolation is not valid for mixed illumination", result["reasons"])

    def test_one_reference_white_cannot_interpolate_against_spectral_sensitivity(self) -> None:
        raw = load_document()
        raw["interpolation"] = {
            "requested": True,
            "weightNumerator": "1",
            "weightDenominator": "2",
            "checkedConventions": True,
            "checkedNeutralResponse": True,
        }
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("interpolation-endpoint-count", result["rejectedClaims"])
        self.assertIn("spectral-sensitivity:narrow-band-led:unchanged", result["preservedResults"])
        self.assertIn("interpolation:invalid:endpoint-count", result["preservedResults"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P045"
        bad_weight = copy.deepcopy(valid)
        bad_weight["interpolation"]["weightNumerator"] = "2"
        bad_weight["interpolation"]["weightDenominator"] = "4"
        mixed = copy.deepcopy(valid)
        mixed["scene"]["mixed"] = False
        singular_text = copy.deepcopy(valid)
        singular_text["endpoints"][0]["matrix"][0][0] = "02"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_weight,
            mixed,
            singular_text,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, sole_test="element-lerp")


if __name__ == "__main__":
    unittest.main()
