"""Host checks for the P058 gamut and matrix fixture. Not a physical S23 probe.

TC-P058-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p058_define_gamut_and_matrix_conventions import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_ACCEPT,
    ORACLE,
    apply_matrix,
    assess,
    coefficients_would_replace_primaries,
    implied_primaries,
    validate_document,
    white_preserved,
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
    path = ROOT / "docs" / "P058_DEFINE_GAMUT_AND_MATRIX_CONVENTIONS.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P058GamutMatrixTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P058")
        self.assertNotIn(result["decision"], {"qualified", "allowed", MUTANT_ACCEPT})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-gamut-matrix-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("working-space to AWG3", METHOD)
        self.assertIn("YUV matrix", METHOD)
        self.assertIn("LogC4", METHOD)
        self.assertEqual(
            FIXTURE,
            "An AWG3 LogC3 file whose metadata incorrectly identifies Rec.709 primaries "
            "because Rec.709 YUV coefficients were used.",
        )
        self.assertEqual(
            ORACLE,
            "The signal validator rejects the contradictory descriptor and requires the "
            "explicit sidecar interpretation.",
        )
        self.assertEqual(MUTANT, "Treat matrix coefficients and color primaries as interchangeable metadata.")
        self.assertEqual(implied_primaries("BT.709"), "Rec.709")
        self.assertEqual(implied_primaries("BT.2020"), "Rec.2020")

    def test_fixture_rejects_rec709_primaries_taken_from_yuv_coefficients(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P058")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertTrue(white_preserved(raw["conversion"]["matrix"]))
        self.assertEqual(apply_matrix(raw["conversion"]["matrix"], ["0.18", "0.18", "0.18"]), ("0.18", "0.18", "0.18"))
        self.assertTrue(coefficients_would_replace_primaries(raw))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["yuv-not-rgb-primaries", "contradictory-primaries"])
        self.assertIn("signal:AWG3:LogC3:D65", result["preservedResults"])
        self.assertIn("transfer:LogC3", result["preservedResults"])
        self.assertIn("direction:working-to-AWG3", result["preservedResults"])
        self.assertIn("precision:decimal-string", result["preservedResults"])
        self.assertIn("matrix:1,0,0,0,1,0,0,0,1", result["preservedResults"])
        self.assertIn("yuv:BT.709:0.2126,0.7152,0.0722", result["preservedResults"])
        self.assertIn("declared-primaries:Rec.709", result["preservedResults"])
        self.assertIn("range:video", result["preservedResults"])
        self.assertIn("derived-from:yuv-coefficients", result["preservedResults"])
        self.assertIn("sidecar:absent:AWG3:BT.709", result["preservedResults"])
        self.assertIn("logc4:outside", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertIn("explicit sidecar interpretation required", result["openQuestions"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn(MUTANT_ACCEPT, result["reasons"])

    def test_mutant_does_not_treat_coefficients_as_primaries(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, interpretation="coefficients-as-primaries")
        self.assert_result(mutant)
        self.assertTrue(coefficients_would_replace_primaries(raw))
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "sidecar_required", MUTANT_ACCEPT})
        self.assertEqual(
            mutant["rejectedClaims"],
            ["coefficients-as-primaries", "yuv-not-rgb-primaries", "contradictory-primaries"],
        )
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn("signal:AWG3:LogC3:D65", mutant["preservedResults"])
        self.assertIn("yuv:BT.709:0.2126,0.7152,0.0722", mutant["preservedResults"])
        self.assertIn("declared-primaries:Rec.709", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("mutant interpretation rejected", mutant["openQuestions"])
        self.assertNotIn("coefficients-as-primaries", honest["rejectedClaims"])

    def test_explicit_sidecar_is_required_and_does_not_qualify(self) -> None:
        raw = load_document()
        raw["sidecar"]["present"] = True
        raw["sidecar"]["explicit"] = True
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "sidecar_required")
        self.assertNotIn(result["decision"], {"qualified", "allowed", MUTANT_ACCEPT})
        self.assertEqual(result["rejectedClaims"], ["yuv-not-rgb-primaries", "contradictory-primaries"])
        self.assertIn("sidecar:explicit:AWG3:BT.709", result["preservedResults"])
        self.assertIn("declared-primaries:Rec.709", result["preservedResults"])
        self.assertIn("interpretation is bound to the explicit sidecar", result["openQuestions"])
        self.assertNotIn("explicit sidecar interpretation required", result["openQuestions"])
        copied = load_document()
        copied["sidecar"]["present"] = True
        copied["sidecar"]["explicit"] = True
        copied["sidecar"]["primaries"] = "Rec.709"
        wrong = assess(copied)
        self.assertEqual(wrong["decision"], "rejected")
        self.assertIn("explicit sidecar interpretation required", wrong["openQuestions"])
        self.assertIn("signal:AWG3:LogC3:D65", wrong["preservedResults"])

    def test_consistent_descriptor_is_withheld(self) -> None:
        raw = load_document()
        raw["descriptor"]["declaredPrimaries"] = "AWG3"
        raw["descriptor"]["derivedFrom"] = "explicit-primaries"
        self.assertFalse(coefficients_would_replace_primaries(raw))
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("declared-primaries:AWG3", result["preservedResults"])
        self.assertIn("yuv:BT.709:0.2126,0.7152,0.0722", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", MUTANT_ACCEPT})
        mutant = assess(raw, interpretation="coefficients-as-primaries")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["coefficients-as-primaries"])
        self.assertEqual(mutant["preservedResults"], result["preservedResults"])

    def test_reversed_direction_broken_white_and_logc4_stay_rejected(self) -> None:
        reversed_doc = load_document()
        reversed_doc["conversion"]["direction"] = "AWG3-to-working"
        reversed_result = assess(reversed_doc)
        self.assertEqual(reversed_result["decision"], "rejected")
        self.assertIn("reversed-matrix-direction", reversed_result["rejectedClaims"])
        self.assertIn("matrix:1,0,0,0,1,0,0,0,1", reversed_result["preservedResults"])
        self.assertIn("contradictory-primaries", reversed_result["rejectedClaims"])

        broken = load_document()
        broken["conversion"]["matrix"] = ["2", "0", "0", "0", "1", "0", "0", "0", "1"]
        self.assertFalse(white_preserved(broken["conversion"]["matrix"]))
        broken_result = assess(broken)
        self.assertEqual(broken_result["decision"], "rejected")
        self.assertIn("white-not-preserved", broken_result["rejectedClaims"])
        self.assertIn("matrix:2,0,0,0,1,0,0,0,1", broken_result["preservedResults"])
        self.assertIn("yuv:BT.709:0.2126,0.7152,0.0722", broken_result["preservedResults"])

        logc4 = load_document()
        logc4["signal"]["encoding"] = "LogC4"
        logc4["signal"]["transfer"] = "LogC4"
        logc4["descriptor"]["transfer"] = "LogC4"
        outside = assess(logc4)
        self.assertEqual(outside["decision"], "rejected")
        self.assertIn("logc4-outside-profile", outside["rejectedClaims"])
        self.assertIn("signal:AWG3:LogC4:D65", outside["preservedResults"])
        self.assertIn("logc4:outside", outside["preservedResults"])
        self.assertNotIn(outside["decision"], {"qualified", "allowed"})

    def test_invalid_documents_and_interpretation_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["storage"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P057"
        bad_mutant = copy.deepcopy(valid)
        bad_mutant["mutant"] = "Accept the YUV matrix as primaries."
        swapped = copy.deepcopy(valid)
        swapped["storage"]["kr"] = "0.7152"
        swapped["storage"]["kg"] = "0.2126"
        explicit = copy.deepcopy(valid)
        explicit["sidecar"]["explicit"] = True
        short = copy.deepcopy(valid)
        short["conversion"]["matrix"] = ["1", "0", "0"]
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_mutant,
            swapped,
            explicit,
            short,
            {**valid, "schemaVersion": 2},
            {**valid, "implementationBaseRevision": "abc"},
            {**valid, "separateImplementation": "false"},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, interpretation="interchangeable")
        with self.assertRaises(ValueError):
            implied_primaries("AWG3")


if __name__ == "__main__":
    unittest.main()
