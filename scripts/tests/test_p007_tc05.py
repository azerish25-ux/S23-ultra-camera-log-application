"""TC-P007-05 measurement without units or coordinate domain."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gates"))
import p007_tc05 as gate


RESULT_KEYS = ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"]
STOCK = "Stock profile"
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_DUP = "c" * 64


def profiles(*digests: str) -> list[dict[str, str]]:
    return [{"displayName": STOCK, "sha256": digest} for digest in digests]


class MeasurementWithoutUnitsTests(unittest.TestCase):
    def payload(self, measurements, compare=None, prof=None) -> dict:
        return {
            "caseId": "TC-P007-05",
            "measurements": measurements,
            "compare": compare,
            "profiles": profiles(HASH_A, HASH_B) if prof is None else prof,
        }

    def assert_shape(self, result: dict, decision: str) -> None:
        self.assertEqual(RESULT_KEYS, list(result))
        self.assertEqual("TC-P007-05", result["caseId"])
        self.assertEqual(decision, result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertTrue(result["reasons"])
        self.assertNotIn("allowed", " ".join(result["reasons"]))

    def assert_hashes(self, result: dict, digests=(HASH_A, HASH_B)) -> None:
        for digest in digests:
            self.assertIn(digest, result["preservedResults"])
        self.assertEqual(len(digests), len([item for item in result["preservedResults"] if item in set(digests)]))

    def test_timing_bare_number_requires_clarification(self):
        result = gate.evaluate(self.payload([
            {"name": "frame-interval", "value": 33.3, "unit": None, "domain": None},
            {"name": "sensor-span", "value": 2_000_000_000, "unit": "ns", "domain": "sensor_timestamp"},
        ]))
        self.assert_shape(result, "clarification_required")
        self.assertEqual(["frame-interval"], result["rejectedClaims"])
        self.assertEqual(["sensor-span", HASH_A, HASH_B], result["preservedResults"])
        self.assertTrue(result["openQuestions"])
        self.assertIn("frame-interval", " ".join(result["reasons"]))
        self.assertIn("bare number", " ".join(result["reasons"]))

    def test_timing_milliseconds_versus_microseconds_is_blocked(self):
        result = gate.evaluate(self.payload(
            [
                {"name": "render-latency-ms", "value": 12.5, "unit": "ms", "domain": "elapsed"},
                {"name": "render-latency-us", "value": 12500, "unit": "us", "domain": "elapsed"},
            ],
            compare=["render-latency-ms", "render-latency-us"],
        ))
        self.assert_shape(result, "blocked")
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual(
            ["render-latency-ms", "render-latency-us", HASH_A, HASH_B],
            result["preservedResults"],
        )
        text = " ".join(result["reasons"])
        self.assertIn("milliseconds", text)
        self.assertIn("microseconds", text)
        self.assertTrue(result["openQuestions"])

    def test_color_missing_domain_is_not_allowed(self):
        result = gate.evaluate(self.payload([
            {"name": "patch-error", "value": 2.4, "unit": "deltaE2000", "domain": None},
            {"name": "mean-error", "value": 1.8, "unit": "deltaE2000", "domain": "chart_reflectance_D65"},
        ]))
        self.assert_shape(result, "clarification_required")
        self.assertEqual(["patch-error"], result["rejectedClaims"])
        self.assertIn("mean-error", result["preservedResults"])
        self.assertNotIn("patch-error", result["preservedResults"])
        self.assert_hashes(result)

    def test_color_display_versus_scene_is_blocked(self):
        result = gate.evaluate(self.payload(
            [
                {"name": "display-error", "value": 3.0, "unit": "deltaE2000", "domain": "display"},
                {"name": "scene-error", "value": 3.0, "unit": "deltaE2000", "domain": "scene"},
            ],
            compare=["display-error", "scene-error"],
        ))
        self.assert_shape(result, "blocked")
        text = " ".join(result["reasons"])
        self.assertIn("display", text)
        self.assertIn("scene", text)
        self.assertEqual(
            ["display-error", "scene-error", HASH_A, HASH_B],
            result["preservedResults"],
        )

    def test_memory_complete_without_compare_is_comparable(self):
        result = gate.evaluate(self.payload([
            {"name": "peak-resident", "value": 48000000, "unit": "bytes", "domain": "process_resident_memory"},
        ]))
        self.assert_shape(result, "comparable")
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])
        self.assertEqual(["peak-resident", HASH_A, HASH_B], result["preservedResults"])
        self.assertIn("same display name", " ".join(result["reasons"]))

    def test_memory_unit_mismatch_is_blocked(self):
        result = gate.evaluate(self.payload(
            [
                {"name": "peak-bytes", "value": 48000000, "unit": "bytes", "domain": "process_resident_memory"},
                {"name": "peak-mebibytes", "value": 45.8, "unit": "MiB", "domain": "process_resident_memory"},
            ],
            compare=["peak-bytes", "peak-mebibytes"],
        ))
        self.assert_shape(result, "blocked")
        self.assertEqual(["peak-bytes", "peak-mebibytes", HASH_A, HASH_B], result["preservedResults"])

    def test_geometric_blur_same_domain_is_comparable(self):
        result = gate.evaluate(self.payload(
            [
                {"name": "blur-radius", "value": 1.25, "unit": "pixels", "domain": "output_image_plane"},
                {"name": "blur-reference", "value": 1.10, "unit": "pixels", "domain": "output_image_plane"},
            ],
            compare=["blur-radius", "blur-reference"],
        ))
        self.assert_shape(result, "comparable")
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])
        self.assertEqual(
            ["blur-radius", "blur-reference", HASH_A, HASH_B],
            result["preservedResults"],
        )

    def test_geometric_blur_missing_unit_rejects_only_that_name(self):
        result = gate.evaluate(self.payload(
            [
                {"name": "blur-radius", "value": 2, "unit": None, "domain": "output_image_plane"},
                {"name": "edge-width", "value": 4, "unit": "pixels", "domain": "output_image_plane"},
            ],
            compare=["blur-radius", "edge-width"],
        ))
        self.assert_shape(result, "clarification_required")
        self.assertEqual(["blur-radius"], result["rejectedClaims"])
        self.assertEqual(["edge-width", HASH_A, HASH_B], result["preservedResults"])

    def test_geometric_blur_display_versus_scene_is_blocked(self):
        result = gate.evaluate(self.payload(
            [
                {"name": "display-blur", "value": 1.5, "unit": "pixels", "domain": "display"},
                {"name": "scene-blur", "value": 0.02, "unit": "mm", "domain": "scene"},
            ],
            compare=["display-blur", "scene-blur"],
        ))
        self.assert_shape(result, "blocked")
        self.assertIn("display values with scene values", " ".join(result["reasons"]))

    def test_source_precision_domains_are_not_interchangeable(self):
        result = gate.evaluate(self.payload(
            [
                {"name": "decoded-levels", "value": 600, "unit": "code_value", "domain": "decoded_P010"},
                {"name": "sensor-bits", "value": 10, "unit": "bits", "domain": "physical_sensor_signal"},
            ],
            compare=["decoded-levels", "sensor-bits"],
        ))
        self.assert_shape(result, "blocked")
        self.assertEqual(
            ["decoded-levels", "sensor-bits", HASH_A, HASH_B],
            result["preservedResults"],
        )

    def test_source_precision_same_domain_is_comparable(self):
        result = gate.evaluate(self.payload(
            [
                {"name": "codec-mean-error", "value": 0.2, "unit": "code_value", "domain": "decoded_P010"},
                {"name": "codec-peak-error", "value": 1.0, "unit": "code_value", "domain": "decoded_P010"},
            ],
            compare=["codec-mean-error", "codec-peak-error"],
        ))
        self.assert_shape(result, "comparable")
        self.assertNotEqual("allowed", result["decision"])

    def test_source_precision_bare_number_is_rejected(self):
        result = gate.evaluate(self.payload([
            {"name": "effective-bits", "value": 12, "unit": None, "domain": "physical_sensor_signal"},
        ]))
        self.assert_shape(result, "clarification_required")
        self.assertEqual(["effective-bits"], result["rejectedClaims"])
        self.assertEqual([HASH_A, HASH_B], result["preservedResults"])

    def test_compare_null_keeps_distinct_complete_domains_comparable(self):
        result = gate.evaluate(self.payload([
            {"name": "frame-interval", "value": 33.3, "unit": "ms", "domain": "elapsed"},
            {"name": "peak-resident", "value": 8, "unit": "bytes", "domain": "process_resident_memory"},
        ]))
        self.assert_shape(result, "comparable")
        self.assertEqual(
            ["frame-interval", "peak-resident", HASH_A, HASH_B],
            result["preservedResults"],
        )

    def test_identical_display_names_preserve_distinct_hashes_once(self):
        prof = profiles(HASH_B, HASH_A, HASH_B, HASH_DUP, HASH_A)
        result = gate.evaluate(self.payload(
            [{"name": "peak-resident", "value": 1, "unit": "bytes", "domain": "process_resident_memory"}],
            prof=prof,
        ))
        self.assert_shape(result, "comparable")
        self.assertEqual(["peak-resident", HASH_B, HASH_A, HASH_DUP], result["preservedResults"])
        self.assertEqual(1, result["preservedResults"].count(HASH_A))
        self.assertIn(STOCK, " ".join(result["reasons"]))

    def test_schema_and_case_id_errors(self):
        with self.assertRaises(ValueError):
            gate.evaluate(["not", "a", "dict"])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload([]) | {"caseId": "TC-P007-06"})
        with self.assertRaises(ValueError):
            gate.evaluate({"caseId": "TC-P007-05", "compare": None, "profiles": []})
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload([
                {"name": "frame-interval", "value": True, "unit": "ms", "domain": "elapsed"},
            ]))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload([
                {"name": "frame-interval", "value": float("nan"), "unit": "ms", "domain": "elapsed"},
            ]))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(
                [
                    {"name": "frame-interval", "value": 1, "unit": "ms", "domain": "elapsed"},
                    {"name": "frame-interval", "value": 2, "unit": "ms", "domain": "elapsed"},
                ],
            ))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(
                [{"name": "frame-interval", "value": 1, "unit": "ms", "domain": "elapsed"}],
                compare=["missing", "frame-interval"],
            ))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(
                [{"name": "frame-interval", "value": 1, "unit": "", "domain": "elapsed"}],
            ))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload([], prof=[{"displayName": STOCK}]))


if __name__ == "__main__":
    unittest.main()
