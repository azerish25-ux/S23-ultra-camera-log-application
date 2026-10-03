"""Host checks for the P042 black-response fixture. Not a physical S23 probe.

TC-P042-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p042_measure_black_response_and_read_noise import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    rational,
    residual_sum,
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
PRESERVED = [
    "black-level:100",
    "exposure:10000000ns",
    "gain:1",
    "uncertainty:1",
    "saturation-code:1023",
    "normalization-offset:0",
    "frame:dark-a:sum=-8:n=16",
    "frame:dark-b:sum=-8:n=16",
    "signed-mean:-1/2",
    "signed-sum:-16",
    "sample-count:32",
    "hot-column:3",
    "temporal-persistence:column-3",
    "hot-pixel-count:8",
    "row-structure:uniform",
    "read-noise-variance:2/3",
    "read-noise-excluded:hot-column-3",
    "sensor-saturation:0",
    "normalization-applied:no",
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P042_MEASURE_BLACK_RESPONSE_AND_READ_NOISE.json").read_text(
            encoding="utf-8"
        )
    )


def flat(value: str) -> list[str]:
    return [value] * 16


class P042BlackResponseTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P042")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P042")
        self.assertEqual(MAP_ID, "s23-black-response-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("controlled dark sequences", METHOD)
        self.assertIn("signed residuals", METHOD)
        self.assertIn("hot-pixel structure", METHOD)
        self.assertIn("sensor code saturation", METHOD)
        self.assertEqual(
            FIXTURE,
            "Dark frames containing a small negative mean after an intentionally "
            "incorrect black subtraction and a persistent hot column.",
        )
        self.assertEqual(
            ORACLE,
            "The fit detects the bias and structured defect rather than clipping all "
            "negative samples to zero.",
        )
        self.assertEqual(
            MUTANT,
            "Clamp black-subtracted RAW to zero before computing statistics.",
        )

    def test_fixture_detects_negative_bias_and_hot_column(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P042")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(rational(-16, 32), "-1/2")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "bias_detected")
        self.assertEqual(
            result["rejectedClaims"],
            ["negative-black-bias", "persistent-hot-column"],
        )
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn("signed-mean:-1/2", result["preservedResults"])
        self.assertIn("signed-sum:-16", result["preservedResults"])
        self.assertIn("hot-column:3", result["preservedResults"])
        self.assertIn("frame:dark-a:sum=-8:n=16", result["preservedResults"])
        self.assertIn("frame:dark-b:sum=-8:n=16", result["preservedResults"])
        self.assertNotIn("signed-mean:0/1", result["preservedResults"])
        self.assertNotIn("signed-sum:0", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("signed mean -1/2 after black subtraction 100", result["reasons"])
        self.assertIn("persistent hot column 3 mean 6/1", result["reasons"])
        self.assertIn(
            "read noise temporal variance 2/3 dn^2 on signed residuals",
            result["reasons"],
        )
        self.assertIn(
            "uncertainty 1dn does not authorize clamping negative samples",
            result["reasons"],
        )
        self.assertIn(
            "sensor saturation 0 is separate from normalization offset 0",
            result["reasons"],
        )
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn(
            "signed mean is inside the 1dn uncertainty report and was not clipped",
            result["openQuestions"],
        )
        self.assertIn("denoising is not a sensor improvement", result["openQuestions"])

    def test_mutant_clamp_is_rejected_and_keeps_the_signed_mean(self) -> None:
        raw = load_document()
        result = assess(raw, statistic="clamp-to-zero")
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bias_detected"})
        self.assertEqual(
            result["rejectedClaims"],
            ["clamp-black-subtracted-raw", "negative-black-bias", "persistent-hot-column"],
        )
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn("signed-mean:-1/2", result["preservedResults"])
        self.assertIn("signed-sum:-16", result["preservedResults"])
        self.assertNotIn("signed-mean:0/1", result["preservedResults"])
        self.assertNotIn("signed-sum:48", result["preservedResults"])
        self.assertIn(MUTANT, result["reasons"])
        self.assertIn("persistent hot column 3 mean 6/1", result["reasons"])
        self.assertIn("clamped statistics were rejected", result["openQuestions"])

    def test_implementing_the_mutant_would_hide_the_negative_mean(self) -> None:
        raw = load_document()
        signed = residual_sum(raw, clamp=False)
        clamped = residual_sum(raw, clamp=True)
        self.assertEqual(signed, -16)
        self.assertEqual(clamped, 48)
        self.assertLess(signed, 0)
        self.assertGreaterEqual(clamped, 0)
        self.assertNotEqual(signed, clamped)
        published = assess(raw)
        self.assertIn(f"signed-sum:{signed}", published["preservedResults"])
        self.assertNotIn(f"signed-sum:{clamped}", published["preservedResults"])
        self.assertNotEqual(published["decision"], "qualified")

    def test_sensor_saturation_is_separate_from_normalization(self) -> None:
        raw = load_document()
        raw["frames"][0]["samples"][0] = "1023"
        raw["normalizationOffset"] = "5"
        result = assess(raw)
        self.assert_result(result)
        self.assertIn("sensor-saturation:1", result["preservedResults"])
        self.assertIn("normalization-offset:5", result["preservedResults"])
        self.assertIn("normalization-applied:no", result["preservedResults"])
        self.assertIn("signed-sum:-12", result["preservedResults"])
        self.assertNotIn("signed-sum:911", result["preservedResults"])
        self.assertIn(
            "sensor saturation 1 is separate from normalization offset 5",
            result["reasons"],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_normalization_offset_does_not_change_the_signed_mean(self) -> None:
        raw = load_document()
        shifted = copy.deepcopy(raw)
        shifted["normalizationOffset"] = "8"
        self.assertEqual(residual_sum(shifted), residual_sum(raw))
        result = assess(shifted)
        self.assertEqual(result["decision"], "bias_detected")
        self.assertIn("signed-mean:-1/2", result["preservedResults"])
        self.assertIn("normalization-offset:8", result["preservedResults"])
        self.assertIn("normalization-applied:no", result["preservedResults"])
        self.assertIn(
            "sensor saturation 0 is separate from normalization offset 8",
            result["reasons"],
        )

    def test_centered_residuals_are_withheld(self) -> None:
        raw = load_document()
        for frame in raw["frames"]:
            frame["samples"] = flat("100")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("signed-mean:0/1", result["preservedResults"])
        self.assertIn("signed-sum:0", result["preservedResults"])
        self.assertIn("hot-column:none", result["preservedResults"])
        self.assertIn("read-noise-variance:0/1", result["preservedResults"])
        self.assertIn(
            "centered fixture residuals are not a physical read-noise measurement",
            result["openQuestions"],
        )

    def test_invalid_documents_and_statistics_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        one_frame = copy.deepcopy(valid)
        one_frame["frames"] = one_frame["frames"][:1]
        bad_sample = copy.deepcopy(valid)
        bad_sample["frames"][0]["samples"][1] = "-1"
        float_width = copy.deepcopy(valid)
        float_width["width"] = 4.0
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P041"
        clamped_text = copy.deepcopy(valid)
        clamped_text["mutant"] = "Clamp and continue."
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            one_frame,
            bad_sample,
            float_width,
            wrong_phase,
            clamped_text,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, statistic="clamp")
        self.assertEqual(assess(valid)["decision"], "bias_detected")


if __name__ == "__main__":
    unittest.main()
