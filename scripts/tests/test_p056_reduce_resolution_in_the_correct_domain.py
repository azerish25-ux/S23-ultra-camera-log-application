"""Host checks for the P056 linear-domain reduction. Not a physical S23 probe.

TC-P056-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p056_reduce_resolution_in_the_correct_domain import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_ACCEPT,
    ORACLE,
    assess,
    box_values,
    canonical,
    cubic_values,
    logc_box_values,
    reduction_ratio,
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
    path = ROOT / "docs" / "P056_REDUCE_RESOLUTION_IN_THE_CORRECT_DOMAIN.json"
    return json.loads(path.read_text(encoding="utf-8"))


def independent_box(pixels: list[str], width: int, out_w: int, out_h: int) -> list[Fraction]:
    """Small mathematical mean that does not call the phase reducer."""
    values = [Fraction(item) for item in pixels]
    height = len(values) // width
    bin_w = width // out_w
    bin_h = height // out_h
    output: list[Fraction] = []
    for oy in range(out_h):
        for ox in range(out_w):
            total = Fraction(0)
            count = 0
            for y in range(oy * bin_h, (oy + 1) * bin_h):
                for x in range(ox * bin_w, (ox + 1) * bin_w):
                    total += values[y * width + x]
                    count += 1
            output.append(total / count)
    return output


def independent_logc_bin() -> Fraction:
    samples = [Fraction("0.04"), Fraction(1), Fraction(1), Fraction("0.04")]
    encoded = [item / (item + 1) for item in samples]
    average = sum(encoded, Fraction(0)) / len(encoded)
    return average / (1 - average)


class P056ReductionTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P056")
        self.assertNotIn(result["decision"], {"qualified", "allowed", MUTANT_ACCEPT})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-linear-domain-reduction-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("scene-linear reduction", METHOD)
        self.assertIn("box averaging", METHOD)
        self.assertEqual(
            FIXTURE,
            "Alternating dark and bright linear pixels whose arithmetic average differs from the "
            "average of their encoded values.",
        )
        self.assertEqual(
            ORACLE,
            "The output agrees with the declared linear-domain reference and records the actual "
            "reduction ratio.",
        )
        self.assertEqual(MUTANT, "Average LogC-encoded values and label the result scene-linear reduction.")

    def test_fixture_matches_the_linear_reference_and_records_the_ratio(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P056")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        expected = independent_box(raw["pixels"], 4, 2, 2)
        self.assertEqual(box_values(raw), expected)
        self.assertEqual([canonical(item) for item in expected], ["0.52", "0.5", "0.04", "1"])
        self.assertNotEqual(box_values(raw), cubic_values(raw))
        self.assertEqual(logc_box_values(raw)[0], independent_logc_bin())
        self.assertEqual(canonical(independent_logc_bin()), "7/19")
        self.assertNotEqual(logc_box_values(raw), box_values(raw))
        self.assertEqual(reduction_ratio(raw), Fraction(1, 4))
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "linear-reduced")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("reduction-ratio:1/4", result["preservedResults"])
        self.assertIn("axes:1/2x1/2", result["preservedResults"])
        self.assertIn("box:0:0.52", result["preservedResults"])
        self.assertIn("box:1:0.5", result["preservedResults"])
        self.assertIn("box:2:0.04", result["preservedResults"])
        self.assertIn("box:3:1", result["preservedResults"])
        self.assertIn("cubic:0:0.4728125", result["preservedResults"])
        self.assertIn("logc-average:0:7/19", result["preservedResults"])
        self.assertIn("logc-average:1:0.44", result["preservedResults"])
        self.assertIn("declared:0:0.52", result["preservedResults"])
        self.assertIn("pixel:0:0.04", result["preservedResults"])
        self.assertIn("pixel:15:1", result["preservedResults"])
        self.assertIn("tiled:0.52,0.5,0.04,1", result["preservedResults"])
        self.assertIn("untiled:0.52,0.5,0.04,1", result["preservedResults"])
        self.assertIn("crop:0,0,4x4", result["preservedResults"])
        self.assertIn("geometry:full-frame-crop", result["preservedResults"])
        self.assertIn("pipeline:crop,antialias,scene-linear-reduction", result["preservedResults"])
        self.assertIn("resampler:box", result["preservedResults"])
        self.assertIn("antialias:box-prefilter", result["preservedResults"])
        self.assertIn("encoding:host-logc-toy", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("reduction ratio 1/4", result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", MUTANT_ACCEPT})

    def test_mutant_logc_average_is_not_labeled_scene_linear(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, average_domain="logc")
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "linear-reduced", MUTANT_ACCEPT})
        self.assertEqual(
            mutant["rejectedClaims"],
            ["logc-average-labeled-scene-linear", "encoded-average-disagrees"],
        )
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn("logc-average:0:7/19", mutant["preservedResults"])
        self.assertIn("box:0:0.52", mutant["preservedResults"])
        self.assertIn("reduction-ratio:1/4", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("log-domain average was not accepted as scene-linear reduction", mutant["openQuestions"])
        self.assertNotIn("logc-average-labeled-scene-linear", honest["rejectedClaims"])

    def test_constant_field_still_rejects_the_logc_label(self) -> None:
        raw = load_document()
        raw["pixels"] = ["0.52"] * 16
        raw["declaredReference"] = ["0.52", "0.52", "0.52", "0.52"]
        self.assertEqual(logc_box_values(raw), box_values(raw))
        honest = assess(raw)
        mutant = assess(raw, average_domain="logc")
        self.assertEqual(honest["decision"], "linear-reduced")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["logc-average-labeled-scene-linear"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "linear-reduced", MUTANT_ACCEPT})
        self.assertIn("logc-average:0:0.52", mutant["preservedResults"])
        self.assertIn("box:0:0.52", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])

    def test_reference_mismatch_keeps_the_pixel_inventory(self) -> None:
        raw = load_document()
        raw["declaredReference"] = ["0.5", "0.5", "0.04", "1"]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["reference-mismatch"])
        self.assertIn("pixel:0:0.04", result["preservedResults"])
        self.assertIn("box:0:0.52", result["preservedResults"])
        self.assertIn("declared:0:0.5", result["preservedResults"])
        self.assertIn("logc-average:0:7/19", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "linear-reduced"})

    def test_cubic_tile_seam_disagrees_and_full_tile_can_match(self) -> None:
        raw = load_document()
        raw["resampler"] = "cubic"
        raw["antialias"] = "separable-cubic"
        raw["declaredReference"] = ["0.4728125", "0.5496875", "0.2046875", "0.8328125"]
        self.assertEqual([canonical(item) for item in cubic_values(raw)], raw["declaredReference"])
        seamed = assess(raw)
        self.assertEqual(seamed["decision"], "rejected")
        self.assertIn("tile-mismatch", seamed["rejectedClaims"])
        self.assertIn("tiled:0.52,0.5,0.04,1", seamed["preservedResults"])
        self.assertIn("untiled:0.4728125,0.5496875,0.2046875,0.8328125", seamed["preservedResults"])
        raw["tileSize"] = 4
        whole = assess(raw)
        self.assertEqual(whole["decision"], "linear-reduced")
        self.assertEqual(whole["rejectedClaims"], [])
        self.assertIn("resampler:cubic", whole["preservedResults"])
        self.assertIn("antialias:separable-cubic", whole["preservedResults"])
        self.assertNotIn(whole["decision"], {"qualified", "allowed", MUTANT_ACCEPT})

    def test_crop_provenance_uses_the_window_not_the_full_frame(self) -> None:
        raw = load_document()
        raw["crop"] = {"originX": 2, "originY": 0, "width": 2, "height": 2}
        raw["outputWidth"] = 1
        raw["outputHeight"] = 1
        raw["declaredReference"] = ["0.5"]
        raw["tileSize"] = 2
        result = assess(raw)
        self.assertEqual(result["decision"], "linear-reduced")
        self.assertIn("geometry:cropped", result["preservedResults"])
        self.assertIn("crop:2,0,2x2", result["preservedResults"])
        self.assertIn("reduction-ratio:1/4", result["preservedResults"])
        self.assertIn("box:0:0.5", result["preservedResults"])
        self.assertIn("pixel:0:0.04", result["preservedResults"])
        self.assertIn("pixel:15:1", result["preservedResults"])

    def test_mislabeled_upscale_is_rejected_and_keeps_pixels(self) -> None:
        raw = load_document()
        raw["outputWidth"] = 8
        raw["outputHeight"] = 8
        raw["declaredReference"] = ["0.5"] * 64
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["mislabeled-upscale"])
        self.assertIn("reduction-ratio:4/1", result["preservedResults"])
        self.assertIn("box:unavailable", result["preservedResults"])
        self.assertIn("pixel:0:0.04", result["preservedResults"])
        self.assertIn("tiled:unavailable", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "linear-reduced"})

    def test_same_size_output_is_not_a_reduction(self) -> None:
        raw = load_document()
        raw["outputWidth"] = 4
        raw["outputHeight"] = 4
        raw["declaredReference"] = list(raw["pixels"])
        raw["tileSize"] = 4
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("not-a-reduction", result["rejectedClaims"])
        self.assertIn("reduction-ratio:1/1", result["preservedResults"])
        self.assertIn("pixel:3:0.8", result["preservedResults"])

    def test_invalid_documents_and_average_domain_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["pixels"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P055"
        bad_mutant = copy.deepcopy(valid)
        bad_mutant["mutant"] = "Average the linear values."
        short = copy.deepcopy(valid)
        short["pixels"] = ["0.04"]
        bad_alias = copy.deepcopy(valid)
        bad_alias["antialias"] = "separable-cubic"
        up_tile = copy.deepcopy(valid)
        up_tile["tileSize"] = 3
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_mutant,
            short,
            bad_alias,
            {**valid, "schemaVersion": 2},
            {**valid, "implementationBaseRevision": "abc"},
            {**valid, "domain": "logc"},
            {**valid, "encoding": "logc3"},
            {**valid, "resampler": "lanczos"},
            {**valid, "declaredReference": ["0.52"]},
            {**valid, "pixels": ["0.040"] + valid["pixels"][1:]},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, average_domain="display")
        with self.assertRaises(ValueError):
            assess(up_tile)


if __name__ == "__main__":
    unittest.main()
