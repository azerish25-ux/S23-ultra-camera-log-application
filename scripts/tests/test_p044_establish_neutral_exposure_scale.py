"""Host checks for the P044 neutral exposure scale. Not a physical S23 probe.

TC-P044-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p044_establish_neutral_exposure_scale import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    exposure_ratio,
    patch_token,
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
FIXTURE_CLAIMS = [
    "white-object:misidentified-bright-white",
    "grey-specular:misidentified-partial-clip",
    "grey-specular:partial-specular-clip",
    "grey-specular:textured",
    "grey-specular:not-neutral",
    "whole-frame-mean-not-middle-grey",
]
FIXTURE_PRESERVED = [
    "frame:frame-neutral-044",
    "roi:white-object:120,40,80,80",
    "roi:grey-specular:400,220,60,60",
    "white-object:signal=9100:clip=0:specular=0:class=bright-white:as=eighteen-percent-grey",
    "grey-specular:signal=4200:clip=18:specular=1:class=partial-clip:as=eighteen-percent-grey",
    "whole-frame-mean:7200",
    "middle-grey:1800",
    "chromatic-fit:withheld",
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P044_ESTABLISH_NEUTRAL_EXPOSURE_SCALE.json").read_text(encoding="utf-8")
    )


def grey(**overrides) -> dict:
    value = {
        "id": "grey-card",
        "roi": "10,20,30,40",
        "userConfirmed": True,
        "identifiedAs": "eighteen-percent-grey",
        "signalLevel": "3600",
        "texture": "low",
        "clippedFraction": "0",
        "specular": False,
        "neutralDelta": "10",
        "actualClass": "eighteen-percent-grey",
    }
    value.update(overrides)
    return value


class P044NeutralExposureScaleTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P044")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P044")
        self.assertEqual(MAP_ID, "s23-neutral-exposure-scale-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("user-confirmed patch", METHOD)
        self.assertIn("clipping, texture, signal level, and color neutrality", METHOD)
        self.assertIn("ROI coordinates and source frame identity", METHOD)
        self.assertIn("separately from chromatic fitting", METHOD)
        self.assertIn("reject invalid patches", METHOD)
        self.assertEqual(
            FIXTURE,
            "A bright white object misidentified as eighteen-percent grey and a grey patch "
            "partly clipped by a specular reflection.",
        )
        self.assertEqual(
            ORACLE,
            "The calibration workflow requests valid evidence and records uncertainty instead of "
            "producing a confidently measured scale.",
        )
        self.assertEqual(
            MUTANT,
            "Assume the mean image luminance always corresponds to middle grey.",
        )
        self.assertEqual(exposure_ratio("1800", "3600"), "1/2")

    def test_fixture_requests_evidence_instead_of_a_measured_scale(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P044")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], FIXTURE_CLAIMS)
        self.assertEqual(result["preservedResults"], FIXTURE_PRESERVED)
        self.assertEqual(result["preservedResults"][3], patch_token(raw["patches"][0]))
        self.assertNotIn("exposure-scale:1/1", result["preservedResults"])
        self.assertFalse(any(item.startswith("exposure-scale:") for item in result["preservedResults"]))
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(
            "white-object is a bright white object misidentified as eighteen-percent grey",
            result["reasons"],
        )
        self.assertIn(
            "grey-specular is partly clipped by a specular reflection",
            result["reasons"],
        )
        self.assertIn("whole-frame mean 7200 is not middle grey 1800", result["reasons"])
        self.assertIn("exposure scale is separate from chromatic fitting", result["reasons"])
        self.assertIn("uncertainty recorded; no confidently measured scale", result["reasons"])
        self.assertIn("valid neutral-patch evidence requested", result["openQuestions"])
        self.assertIn("uncertainty recorded; scale not measured", result["openQuestions"])
        self.assertTrue(any("does not qualify a physical S23" in item for item in result["reasons"]))
        self.assertNotIn(MUTANT, result["reasons"])

    def test_mutant_mean_luminance_is_not_middle_grey(self) -> None:
        raw = load_document()
        result = assess(raw, sole_test="mean-luminance-middle-grey")
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(
            result["decision"],
            {"qualified", "allowed", "provisional", "measured", "measured_scale"},
        )
        self.assertEqual(
            result["rejectedClaims"],
            ["mean-luminance-middle-grey", *FIXTURE_CLAIMS],
        )
        self.assertEqual(result["preservedResults"], FIXTURE_PRESERVED)
        joined = " ".join(result["preservedResults"])
        self.assertNotIn("exposure-scale:", joined)
        self.assertNotIn("middle-grey:7200", joined)
        self.assertNotIn("scale:1", joined)
        self.assertIn("whole-frame-mean:7200", result["preservedResults"])
        self.assertIn("middle-grey:1800", result["preservedResults"])
        self.assertIn("roi:white-object:120,40,80,80", result["preservedResults"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn("mean luminance was not treated as middle grey", result["openQuestions"])
        self.assertIn("whole-frame mean 7200 is not middle grey 1800", result["reasons"])

    def test_equal_frame_mean_still_does_not_invent_a_scale(self) -> None:
        raw = load_document()
        raw["wholeFrameMeanLuminance"] = "1800"
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})
        self.assertNotIn("whole-frame-mean-not-middle-grey", result["rejectedClaims"])
        self.assertIn("white-object:misidentified-bright-white", result["rejectedClaims"])
        self.assertFalse(any(item.startswith("exposure-scale:") for item in result["preservedResults"]))
        self.assertIn("whole-frame-mean:1800", result["preservedResults"])
        self.assertIn("middle-grey:1800", result["preservedResults"])
        self.assertIn("equal frame mean is not used as the neutral target", result["reasons"])
        self.assertIn(
            "frame-mean equality is not a neutral-target measurement",
            result["openQuestions"],
        )
        mutant = assess(raw, sole_test="mean-luminance-middle-grey")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertFalse(any(item.startswith("exposure-scale:") for item in mutant["preservedResults"]))
        self.assertNotIn("exposure-scale:1/1", mutant["preservedResults"])

    def test_valid_patch_is_provisional_and_separate_from_the_frame_mean(self) -> None:
        raw = load_document()
        raw["patches"] = [grey()]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["whole-frame-mean-not-middle-grey"])
        self.assertIn("frame:frame-neutral-044", result["preservedResults"])
        self.assertIn("roi:grey-card:10,20,30,40", result["preservedResults"])
        self.assertIn(patch_token(grey()), result["preservedResults"])
        self.assertIn("exposure-scale:1/2", result["preservedResults"])
        self.assertIn("uncertainty:neutral-delta-10", result["preservedResults"])
        self.assertIn("chromatic-fit:withheld", result["preservedResults"])
        self.assertNotIn("exposure-scale:2/1", result["preservedResults"])
        self.assertIn(
            "provisional exposure scale 1/2 is not a confidently measured profile",
            result["reasons"],
        )
        self.assertIn(
            "provisional scale records uncertainty and is not a confident measurement",
            result["openQuestions"],
        )
        mutant = assess(raw, sole_test="mean-luminance-middle-grey")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"][0], "mean-luminance-middle-grey")
        self.assertIn("exposure-scale:1/2", mutant["preservedResults"])
        self.assertNotIn("exposure-scale:1/1", mutant["preservedResults"])
        self.assertNotIn("exposure-scale:2/1", mutant["preservedResults"])

    def test_disagreeing_valid_patches_do_not_pick_a_scale(self) -> None:
        raw = load_document()
        raw["patches"] = [
            grey(id="grey-a", signalLevel="3600"),
            grey(id="grey-b", roi="8,8,16,16", signalLevel="1800", neutralDelta="0"),
        ]
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("scale-disagreement", result["rejectedClaims"])
        self.assertIn("candidate-scale:grey-a:1/2", result["preservedResults"])
        self.assertIn("candidate-scale:grey-b:1/1", result["preservedResults"])
        self.assertFalse(any(item.startswith("exposure-scale:") for item in result["preservedResults"]))
        self.assertIn("valid patches disagree; scale withheld", result["openQuestions"])

    def test_invalid_documents_and_sole_test_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["patches"]
        empty = copy.deepcopy(valid)
        empty["patches"] = []
        duplicate = copy.deepcopy(valid)
        duplicate["patches"].append(copy.deepcopy(duplicate["patches"][0]))
        bad_roi = copy.deepcopy(valid)
        bad_roi["patches"][0]["roi"] = "120,40,0,80"
        above = copy.deepcopy(valid)
        above["patches"][0]["signalLevel"] = "10001"
        bad_clip = copy.deepcopy(valid)
        bad_clip["patches"][1]["clippedFraction"] = "101"
        bad_bool = copy.deepcopy(valid)
        bad_bool["patches"][0]["specular"] = 1
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P043"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        drifted = copy.deepcopy(valid)
        drifted["mutant"] = "Use the frame mean."
        zero_signal = copy.deepcopy(valid)
        zero_signal["patches"][0]["signalLevel"] = "0"
        high_middle = copy.deepcopy(valid)
        high_middle["middleGreyCode"] = "10000"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            empty,
            duplicate,
            bad_roi,
            above,
            bad_clip,
            bad_bool,
            wrong_phase,
            bad_revision,
            drifted,
            zero_signal,
            high_middle,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, sole_test="mean-is-grey")


if __name__ == "__main__":
    unittest.main()
