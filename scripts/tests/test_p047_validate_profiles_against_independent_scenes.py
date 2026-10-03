"""Host checks for the P047 independent profile acceptance fixture.

Not a physical S23 probe. TC-P047-01..08 are separate modules and are not
executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p047_validate_profiles_against_independent_scenes import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    LIMITATION,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_CLAIM,
    ORACLE,
    apply_preferred_appearance_as_accuracy,
    assess,
    calibration_error_terms,
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
FIXTURE_CLAIMS = ["color-gate:fabric-sat", "neutral-gate:neutral-grey"]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P047_VALIDATE_PROFILES_AGAINST_INDEPENDENT_SCENES.json").read_text(
            encoding="utf-8"
        )
    )


class P047ProfileAcceptanceTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P047")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "colorimetric"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P047")
        self.assertEqual(MAP_ID, "s23-independent-profile-acceptance-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("artistic preference", METHOD)
        self.assertIn("behaviour separately", METHOD)
        self.assertIn("not used for fitting", METHOD)
        self.assertEqual(
            FIXTURE,
            "A profile that makes one skin sample attractive while moving neutral greys "
            "and saturated fabric beyond the declared tolerance.",
        )
        self.assertEqual(
            ORACLE,
            "The neutral and color gates fail independently of subjective preference.",
        )
        self.assertEqual(
            MUTANT,
            "Use a preferred cinematic appearance as proof of camera colorimetric accuracy.",
        )
        self.assertIn("not a phone default", LIMITATION)
        self.assertIn("not colorimetric accuracy", LIMITATION)

    def test_fixture_fails_neutral_and_color_gates_without_using_preference(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P047")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["limitation"], LIMITATION)
        self.assertEqual(raw["profile"]["appearance"], "preferred-cinematic")
        self.assertEqual(raw["profile"]["preferenceScore"], "0.92")
        classes = {item["sceneClass"] for item in raw["scenes"]}
        self.assertEqual(
            classes,
            {"skin", "foliage", "fabrics", "neutral", "colored-light", "high-contrast"},
        )
        skin_repeats = {item["repeatId"] for item in raw["scenes"] if item["sceneClass"] == "skin"}
        self.assertEqual(skin_repeats, {"r1", "r2"})
        self.assertTrue(all(item["usedForFitting"] is False for item in raw["scenes"]))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], FIXTURE_CLAIMS)
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("neutral gate failed", result["reasons"])
        self.assertIn("color gate failed", result["reasons"])
        self.assertNotIn("exposure gate failed", result["reasons"])
        self.assertNotIn("noise gate failed", result["reasons"])
        self.assertNotIn("highlight gate failed", result["reasons"])
        self.assertIn("artistic preference was excluded from calibration error", result["reasons"])
        joined = "\n".join(result["preservedResults"])
        for scene in (
            "skin-a",
            "skin-b",
            "foliage-a",
            "fabric-sat",
            "neutral-grey",
            "colored-light-a",
            "high-contrast-a",
        ):
            self.assertIn("scene:" + scene + ":", joined)
        self.assertIn("training-error:0.006", result["preservedResults"])
        self.assertIn("training-patch:train-neutral-1", result["preservedResults"])
        self.assertIn("training-patch:train-skin-1", result["preservedResults"])
        self.assertIn(
            "preference:profile-skin-attractive:0.92:not-calibration-error",
            result["preservedResults"],
        )
        self.assertIn("scene-preference:skin-a:0.95:excluded", result["preservedResults"])
        self.assertIn(LIMITATION, result["openQuestions"])
        self.assertIn("physical S23 profile acceptance unverified", result["openQuestions"])
        terms = calibration_error_terms(raw)
        blob = "\n".join(terms)
        self.assertIn("training:0.006", terms)
        self.assertIn("fabric-sat:colorDelta:0.11", terms)
        self.assertIn("neutral-grey:neutralDelta:0.08", terms)
        self.assertNotIn("0.92", blob)
        self.assertNotIn("0.95", blob)
        self.assertNotIn("preference", blob)
        self.assertNotIn("cinematic", blob)

    def test_preference_does_not_change_gate_failures(self) -> None:
        raw = load_document()
        before = calibration_error_terms(raw)
        claims = assess(raw)["rejectedClaims"]
        for score, appearance in (
            ("0.77", "unspecified"),
            ("1", "preferred-cinematic"),
            ("0", "neutral"),
        ):
            edited = copy.deepcopy(raw)
            edited["profile"]["preferenceScore"] = score
            edited["profile"]["appearance"] = appearance
            for scene in edited["scenes"]:
                scene["preferenceScore"] = score
            result = assess(edited)
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(result["rejectedClaims"], claims)
            self.assertNotIn(result["decision"], {"qualified", "allowed", "colorimetric"})
            self.assertEqual(calibration_error_terms(edited), before)
            self.assertNotIn("preference", "\n".join(calibration_error_terms(edited)))

    def test_mutant_preferred_appearance_is_not_colorimetric_accuracy(self) -> None:
        raw = load_document()
        mutant = apply_preferred_appearance_as_accuracy(raw)
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "colorimetric", "withheld"})
        self.assertEqual(mutant["rejectedClaims"], FIXTURE_CLAIMS + [MUTANT_CLAIM])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn(ORACLE, mutant["reasons"])
        self.assertIn(
            "preferred cinematic appearance is not camera colorimetric accuracy",
            mutant["reasons"],
        )
        self.assertIn("scene:fabric-sat:fabrics:repeat:r1", mutant["preservedResults"])
        self.assertIn("scene:neutral-grey:neutral:repeat:r1", mutant["preservedResults"])
        self.assertIn("scene:skin-a:skin:repeat:r1", mutant["preservedResults"])
        self.assertTrue(
            any(item.endswith(":not-calibration-error") for item in mutant["preservedResults"])
        )

    def test_in_tolerance_host_pass_stays_withheld(self) -> None:
        raw = load_document()
        raw["scenes"][3]["colorDelta"] = "0.02"
        raw["scenes"][4]["neutralDelta"] = "0.01"
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("a host pass does not install this profile as the phone default", result["reasons"])
        self.assertIn("preferred cinematic appearance is not colorimetric accuracy", result["reasons"])
        self.assertIn("scene:fabric-sat:fabrics:repeat:r1", result["preservedResults"])
        self.assertIn("delta:neutral-grey:neutralDelta:0.01", result["preservedResults"])
        mutant = apply_preferred_appearance_as_accuracy(raw)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], [MUTANT_CLAIM])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "colorimetric", "withheld"})

    def test_fitting_scene_does_not_wipe_the_inventory(self) -> None:
        raw = load_document()
        raw["scenes"][0]["usedForFitting"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("used-for-fitting:skin-a", result["rejectedClaims"])
        self.assertIn("color-gate:fabric-sat", result["rejectedClaims"])
        self.assertIn("neutral-gate:neutral-grey", result["rejectedClaims"])
        self.assertIn("scene:foliage-a:foliage:repeat:r1", result["preservedResults"])
        self.assertIn("training-error:0.006", result["preservedResults"])

    def test_invalid_document_raises(self) -> None:
        raw = load_document()
        cases = []
        broken = copy.deepcopy(raw)
        broken["schemaVersion"] = 2
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["phase"] = "P046"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        del broken["mutant"]
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["extra"] = True
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["profile"]["preferenceScore"] = "0.920"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["scenes"][0]["neutralDelta"] = "0.01"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["scenes"] = [item for item in broken["scenes"] if item["sceneClass"] != "foliage"]
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["scenes"][1]["id"] = "skin-a"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["training"]["patchIds"] = ["skin-a"]
        cases.append(broken)
        broken = copy.deepcopy(raw)
        for item in broken["scenes"]:
            item["repeatId"] = "r1"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["profile"]["appearance"] = "cinematic"
        cases.append(broken)
        for item in cases:
            with self.subTest(phase=item.get("phase"), keys=sorted(item)):
                with self.assertRaises(ValueError):
                    validate_document(item)


if __name__ == "__main__":
    unittest.main()
