"""Host checks for the P041 calibrated profile contract. Not a physical S23 probe.

TC-P041-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p041_define_the_calibrated_profile_contract import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    payload_digest,
    profile_token,
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
HASH_A = "4a8681c7f0a7bcebb39fb53bb5081ddbfd15b76597d563e98c7d7060693e8659"
HASH_B = "5117923f045a71ce294748cd8efa34edf493b32ff90e790edb24db04c2fd3bd5"


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P041_DEFINE_THE_CALIBRATED_PROFILE_CONTRACT.json").read_text(
            encoding="utf-8"
        )
    )


def matrix() -> list[list[str]]:
    return [
        ["0.436", "0.385", "0.143"],
        ["0.222", "0.717", "0.061"],
        ["0.014", "0.097", "0.714"],
    ]


def profile(**overrides) -> dict:
    value = {
        "id": "measured-chart",
        "authorAssertion": "measured",
        "category": "measured",
        "offeredFor": "research",
        "sourceIdentity": {
            "handset": "fixture-handset",
            "firmware": "fw-1",
            "route": "raw-logical-0",
            "logicalCamera": "logical-0",
        },
        "matrixDirection": "camera-rgb-to-xyz-d50",
        "matrix": matrix(),
        "whitePoint": "D50",
        "exposureScale": "1.25",
        "crop": "4000x3000+0+0",
        "cfa": "RGGB",
        "illuminant": "D65",
        "blackModel": {"offset": "64", "rowBias": "0.5", "columnBias": "-0.25"},
        "defectPolicy": "retain-signed",
        "fitProvenance": {"fitId": "fit-chart", "measurementReferences": ["chart-24-lab-1"]},
        "payloadHash": "0" * 64,
    }
    value.update(overrides)
    value["payloadHash"] = payload_digest(value)
    return value


def document(profiles: list[dict]) -> dict:
    return {
        "schemaVersion": 1,
        "phase": "P041",
        "mapId": MAP_ID,
        "implementationBaseRevision": BASE_REVISION,
        "method": METHOD,
        "fixture": FIXTURE,
        "oracle": ORACLE,
        "mutant": MUTANT,
        "profiles": profiles,
    }


class P041ProfileContractTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], CASE_ID)
        self.assertNotIn(result["decision"], {"qualified", "allowed", "certified"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P041")
        self.assertEqual(MAP_ID, "s23-calibrated-profile-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("source identity", METHOD)
        self.assertIn("matrix direction", METHOD)
        self.assertIn("manufacturer-derived provisional", METHOD)
        self.assertIn("reject nonfinite values", METHOD)
        self.assertEqual(
            FIXTURE,
            "A profile labelled measured but lacking measurement references, plus a synthetic "
            "profile offered for physical footage.",
        )
        self.assertEqual(
            ORACLE,
            "The importer retains the author assertion separately and refuses synthetic "
            "evidence as physical calibration.",
        )
        self.assertEqual(
            MUTANT,
            "Promote any imported profile with a measured string to certified status.",
        )

    def test_fixture_refuses_unreferenced_measured_and_synthetic_physical(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P041")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(payload_digest(raw["profiles"][0]), HASH_A)
        self.assertEqual(payload_digest(raw["profiles"][1]), HASH_B)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            [
                "unreferenced-measured-label:labelled-measured-no-refs",
                "synthetic-not-physical:synthetic-physical",
                "synthetic-as-physical:synthetic-physical",
            ],
        )
        self.assertIn(profile_token(raw["profiles"][0]), result["preservedResults"])
        self.assertIn(profile_token(raw["profiles"][1]), result["preservedResults"])
        self.assertIn("assertion:labelled-measured-no-refs:measured", result["preservedResults"])
        self.assertIn("assertion:synthetic-physical:synthetic", result["preservedResults"])
        self.assertIn(f"computed-hash:labelled-measured-no-refs:{HASH_A}", result["preservedResults"])
        self.assertIn(f"computed-hash:synthetic-physical:{HASH_B}", result["preservedResults"])
        self.assertIn(
            "importer-status:labelled-measured-no-refs:rejected-unreferenced",
            result["preservedResults"],
        )
        self.assertIn(
            "importer-status:synthetic-physical:rejected-synthetic-physical",
            result["preservedResults"],
        )
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("labelled-measured-no-refs author assertion measured was not promoted", result["reasons"])
        self.assertIn(
            "labelled-measured-no-refs retained for exploratory research",
            result["openQuestions"],
        )
        self.assertNotIn("certified", result["decision"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn("importer-status:labelled-measured-no-refs:certified", result["preservedResults"])
        self.assertTrue(any("does not qualify a physical S23" in item for item in result["reasons"]))

    def test_mutant_measured_string_is_not_certified(self) -> None:
        raw = load_document()
        raw["profiles"][1]["authorAssertion"] = "measured"
        result = assess(raw, promote_measured_string=True)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "certified", "measurement_record"})
        self.assertEqual(result["rejectedClaims"][0], "measured-string-to-certified")
        self.assertIn("unreferenced-measured-label:labelled-measured-no-refs", result["rejectedClaims"])
        self.assertIn("synthetic-as-physical:synthetic-physical", result["rejectedClaims"])
        self.assertIn("assertion:synthetic-physical:measured", result["preservedResults"])
        self.assertIn(profile_token(raw["profiles"][0]), result["preservedResults"])
        self.assertIn(f"computed-hash:synthetic-physical:{HASH_B}", result["preservedResults"])
        self.assertNotIn("status:certified", result["preservedResults"])
        self.assertNotIn("importer-status:synthetic-physical:certified", result["preservedResults"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn("a measured string is not certified status", result["reasons"])
        self.assertIn("measured-string promotion was rejected", result["openQuestions"])

    def test_mutant_does_not_certify_a_referenced_measured_profile(self) -> None:
        raw = document([profile()])
        honest = assess(raw)
        mutant = assess(raw, promote_measured_string=True)
        self.assertEqual(honest["decision"], "measurement_record")
        self.assertNotIn(honest["decision"], {"qualified", "allowed", "certified"})
        self.assertEqual(honest["rejectedClaims"], [])
        self.assertIn("importer-status:measured-chart:measurement_record", honest["preservedResults"])
        self.assertIn("assertion:measured-chart:measured", honest["preservedResults"])
        self.assertIn("measurement record is not certified status", honest["openQuestions"])
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "certified", "measurement_record"})
        self.assertIn("measured-string-to-certified", mutant["rejectedClaims"])
        self.assertIn("assertion:measured-chart:measured", mutant["preservedResults"])
        self.assertIn(profile_token(raw["profiles"][0]), mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])

    def test_nonfinite_payload_is_rejected_and_inventory_remains(self) -> None:
        item = profile()
        item["matrix"][0][0] = "NaN"
        item["payloadHash"] = payload_digest(item)
        result = assess(document([item]))
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["nonfinite:measured-chart:matrix[0][0]"])
        self.assertIn("assertion:measured-chart:measured", result["preservedResults"])
        self.assertIn(profile_token(item), result["preservedResults"])
        self.assertIn("importer-status:measured-chart:rejected-nonfinite", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "certified", "measurement_record"})

    def test_hash_mismatch_keeps_the_declared_profile(self) -> None:
        item = profile()
        item["exposureScale"] = "2"
        result = assess(document([item]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("payload-hash-mismatch:measured-chart", result["rejectedClaims"])
        self.assertIn(profile_token(item), result["preservedResults"])
        self.assertIn("assertion:measured-chart:measured", result["preservedResults"])
        self.assertNotEqual(
            payload_digest(item),
            item["payloadHash"],
        )
        self.assertIn(f"computed-hash:measured-chart:{payload_digest(item)}", result["preservedResults"])

    def test_manufacturer_provisional_is_not_measured(self) -> None:
        item = profile(
            id="vendor-start",
            authorAssertion="provisional",
            category="manufacturer-provisional",
            fitProvenance={"fitId": "fit-vendor", "measurementReferences": []},
        )
        result = assess(document([item]))
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "certified", "measurement_record"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("importer-status:vendor-start:provisional", result["preservedResults"])
        self.assertIn("assertion:vendor-start:provisional", result["preservedResults"])
        self.assertIn("vendor-start provisional is not a measured profile", result["openQuestions"])

    def test_measured_assertion_does_not_upgrade_provisional(self) -> None:
        item = profile(
            id="vendor-claimed",
            authorAssertion="measured",
            category="manufacturer-provisional",
            fitProvenance={"fitId": "fit-vendor", "measurementReferences": []},
        )
        result = assess(document([item]))
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], ["measured-assertion-on-provisional:vendor-claimed"])
        self.assertIn("assertion:vendor-claimed:measured", result["preservedResults"])
        self.assertIn("importer-status:vendor-claimed:provisional", result["preservedResults"])
        self.assertNotIn("importer-status:vendor-claimed:certified", result["preservedResults"])

    def test_synthetic_fixture_offer_is_withheld_from_physical_calibration(self) -> None:
        item = profile(
            id="synthetic-lab",
            authorAssertion="synthetic",
            category="synthetic",
            offeredFor="synthetic-fixture",
            fitProvenance={"fitId": "fit-synth", "measurementReferences": []},
        )
        result = assess(document([item]))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], ["synthetic-not-physical:synthetic-lab"])
        self.assertNotIn("synthetic-as-physical:synthetic-lab", result["rejectedClaims"])
        self.assertIn("importer-status:synthetic-lab:synthetic_retained", result["preservedResults"])
        self.assertIn("synthetic-lab synthetic evidence is refused as physical calibration", result["reasons"])

    def test_clamp_zero_defect_policy_is_rejected(self) -> None:
        item = profile(defectPolicy="clamp-zero")
        result = assess(document([item]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("clamped-defect-policy:measured-chart", result["rejectedClaims"])
        self.assertIn(profile_token(item), result["preservedResults"])
        self.assertIn("blackModel", json.dumps(item))

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P040"
        nan_number = copy.deepcopy(valid)
        nan_number["profiles"][0]["matrix"][1][1] = float("nan")
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            document([]),
            document([profile(id="0bad")]),
            nan_number,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, promote_measured_string="true")


if __name__ == "__main__":
    unittest.main()
