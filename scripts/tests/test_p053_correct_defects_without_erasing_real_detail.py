"""Host checks for the P053 defect-correction fixture. Not a physical S23 probe.

TC-P053-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p053_correct_defects_without_erasing_real_detail import (  # noqa: E402
    BASE_REVISION,
    DECLARED_TEST,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_ACCEPT,
    MUTANT_TEST,
    ORACLE,
    assess,
    local_median,
    threshold_removals,
    validate_document,
    _load,
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
    path = ROOT / "docs" / "P053_CORRECT_DEFECTS_WITHOUT_ERASING_REAL_DETAIL.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P053DefectCorrectionTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P053")
        self.assertNotIn(result["decision"], {"qualified", "allowed", MUTANT_ACCEPT})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-defect-correction-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("measured defect maps", METHOD)
        self.assertIn("Do not replace every isolated bright pixel", METHOD)
        self.assertEqual(FIXTURE, "A measured hot pixel adjacent to a real small moving specular highlight.")
        self.assertIn("moving highlight is preserved", ORACLE)
        self.assertEqual(MUTANT, "Remove every isolated bright pixel using one intensity threshold.")
        self.assertEqual(DECLARED_TEST, "measured-defect-map")
        self.assertEqual(MUTANT_TEST, "intensity-threshold")

    def test_fixture_corrects_the_hot_pixel_and_keeps_the_moving_highlight(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P053")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        loaded = _load(raw)
        for frame in loaded["frames"]:
            self.assertEqual(local_median(loaded, frame, 2, 2), 100)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "highlight_preserved")
        self.assertEqual(result["rejectedClaims"], ["intensity-threshold-removal"])
        for token in (
            "original:0:2,2:900:defect",
            "original:0:3,2:880:highlight",
            "original:1:4,4:860:highlight",
            "original:2:7,1:1023:highlight",
            "highlight:0:3,2:880:preserved",
            "highlight:1:4,4:860:preserved",
            "highlight:2:7,1:1023:preserved",
            "saturated-boundary:2:7,1",
            "mask:0:2,2:9/10",
            "corrected:0:2,2:100",
            "corrected:1:2,2:100",
            "corrected:2:2,2:100",
            "map:hot-2-2:2,2:hot:9/10",
            "corrections-inspectable:mask-and-original",
            "domain:scene-linear",
            "original-retained:true",
        ):
            self.assertIn(token, result["preservedResults"])
        self.assertFalse(any(item.startswith("corrected:0:3,2:") for item in result["preservedResults"]))
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(METHOD, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])

    def test_mutant_threshold_removal_is_rejected_and_keeps_the_highlight(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, sole_test=MUTANT_TEST)
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "highlight_preserved", MUTANT_ACCEPT})
        self.assertEqual(
            mutant["rejectedClaims"],
            [
                "intensity-threshold-removal",
                "removed:0:2,2:900",
                "removed:0:3,2:880",
                "removed:1:2,2:910",
                "removed:1:4,4:860",
                "removed:2:2,2:895",
                "removed:2:7,1:1023",
            ],
        )
        self.assertEqual(threshold_removals(_load(raw)), mutant["rejectedClaims"][1:])
        self.assertIn("original:0:3,2:880:highlight", mutant["preservedResults"])
        self.assertIn("highlight:0:3,2:880:preserved", mutant["preservedResults"])
        self.assertIn("highlight:2:7,1:1023:preserved", mutant["preservedResults"])
        self.assertIn("saturated-boundary:2:7,1", mutant["preservedResults"])
        self.assertFalse(any(item.startswith("corrected:") for item in mutant["preservedResults"]))
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("intensity-threshold removal was rejected", mutant["openQuestions"])
        self.assertNotEqual(mutant["decision"], honest["decision"])
        self.assertIn("original:0:2,2:900:defect", mutant["preservedResults"])

    def test_low_confidence_and_failed_local_test_withhold_without_erasing_highlights(self) -> None:
        low = load_document()
        low["defectMap"][0]["confidence"] = "1/2"
        withheld = assess(low)
        self.assert_result(withheld)
        self.assertEqual(withheld["decision"], "withheld")
        self.assertIn("low-confidence:hot-2-2", withheld["rejectedClaims"])
        self.assertIn("highlight:1:4,4:860:preserved", withheld["preservedResults"])
        self.assertNotIn("corrected:0:2,2:100", withheld["preservedResults"])
        bright = load_document()
        bright["background"] = "900"
        blocked = assess(bright)
        self.assertEqual(blocked["decision"], "withheld")
        self.assertIn("local-test-failed:hot-2-2", blocked["rejectedClaims"])
        self.assertIn("original:0:3,2:880:highlight", blocked["preservedResults"])
        self.assertIn("background:900", blocked["preservedResults"])
        self.assertNotIn(blocked["decision"], {"qualified", "allowed", MUTANT_ACCEPT})

    def test_undeclared_domain_and_discarded_original_are_rejected(self) -> None:
        encoded = load_document()
        encoded["sourceDomain"] = "display-encoded"
        result = assess(encoded)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("undeclared-source-domain:display-encoded", result["rejectedClaims"])
        self.assertIn("original:2:7,1:1023:highlight", result["preservedResults"])
        self.assertFalse(any(item.startswith("corrected:") for item in result["preservedResults"]))
        dropped = load_document()
        dropped["retainOriginal"] = False
        discarded = assess(dropped)
        self.assertEqual(discarded["decision"], "rejected")
        self.assertIn("original-discarded", discarded["rejectedClaims"])
        self.assertIn("original:0:2,2:900:defect", discarded["preservedResults"])
        self.assertIn("highlight:0:3,2:880:preserved", discarded["preservedResults"])

    def test_highlight_listed_on_the_defect_map_is_not_corrected(self) -> None:
        raw = load_document()
        raw["frames"][1]["samples"] = [
            {"x": 2, "y": 2, "value": "860", "role": "highlight"},
        ]
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("highlight-on-defect-map:1:2,2", result["rejectedClaims"])
        self.assertIn("original:1:2,2:860:highlight", result["preservedResults"])
        self.assertFalse(any(item.startswith("corrected:1:2,2:") for item in result["preservedResults"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed", "highlight_preserved"})

    def test_several_frames_and_saturated_boundary_stay_in_the_inventory(self) -> None:
        raw = load_document()
        result = assess(raw)
        frame_ids = {item.split(":")[1] for item in result["preservedResults"] if item.startswith("original:")}
        self.assertEqual(frame_ids, {"0", "1", "2"})
        self.assertIn("saturated-boundary:2:7,1", result["preservedResults"])
        self.assertGreaterEqual(len([item for item in result["preservedResults"] if item.startswith("highlight:")]), 2)

    def test_invalid_documents_and_sole_test_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["defectMap"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P052"
        bad_mutant = copy.deepcopy(valid)
        bad_mutant["mutant"] = "Delete bright pixels."
        unreduced = copy.deepcopy(valid)
        unreduced["minConfidence"] = "2/4"
        empty = copy.deepcopy(valid)
        empty["frames"] = []
        duplicate = copy.deepcopy(valid)
        duplicate["frames"][0]["samples"].append({"x": 2, "y": 2, "value": "1", "role": "background"})
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_mutant,
            unreduced,
            empty,
            duplicate,
            {**valid, "schemaVersion": 2},
            {**valid, "implementationBaseRevision": "abc"},
            {**valid, "sourceDomain": "camera-rgb"},
            {**valid, "width": True},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, sole_test="delete-brights")


if __name__ == "__main__":
    unittest.main()
