"""TC-P006-05: measurements need a unit and a domain before comparison."""

from __future__ import annotations

import math
import sys
import unittest

sys.path.insert(0, "/workspace/s23/scripts/gates")

from p006_tc05 import evaluate

CASE_ID = "TC-P006-05"
KEYS = ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"]

# Repetition plan: timing, color, memory, geometric blur, source-precision.
REPETITIONS = (
    ("timing", "ms", "elapsed_ms", 12),
    ("color", "deltaE", "display_value", 1.4),
    ("memory", "MiB", "process_rss", 256),
    ("geometric blur", "px", "scene_value", 0.35),
    ("source-precision", "bits", "source_code_value", 10),
)


def measurement(name, value, unit, domain):
    return {"name": name, "value": value, "unit": unit, "domain": domain}


def payload(measurements, compare=None, case_id=CASE_ID):
    return {"caseId": case_id, "measurements": measurements, "compare": compare}


def assert_contract(test, result):
    test.assertEqual(list(result.keys()), KEYS)
    test.assertEqual(result["caseId"], CASE_ID)
    test.assertIsInstance(result["decision"], str)
    test.assertNotEqual(result["decision"], "allowed")
    for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
        test.assertIsInstance(result[key], list)
        test.assertTrue(all(isinstance(item, str) and item for item in result[key]))
    test.assertTrue(result["reasons"])


class MeasurementWithoutUnitsTests(unittest.TestCase):
    def test_missing_unit_rejects_that_name_and_preserves_complete_measurements(self):
        result = evaluate(payload([
            measurement("timing", 12, None, "elapsed_ms"),
            measurement("color", 1.2, "deltaE", "display_value"),
        ]))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "clarification_required")
        self.assertEqual(result["rejectedClaims"], ["timing"])
        self.assertEqual(result["preservedResults"], ["color"])
        self.assertNotIn("timing", result["preservedResults"])

    def test_missing_domain_requires_clarification(self):
        result = evaluate(payload([
            measurement("memory", 128, "MiB", None),
            measurement("timing", 8, "ms", "elapsed_ms"),
        ]))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "clarification_required")
        self.assertIn("memory", result["rejectedClaims"])
        self.assertIn("timing", result["preservedResults"])
        self.assertNotIn("memory", result["preservedResults"])

    def test_blank_unit_or_domain_is_missing(self):
        result = evaluate(payload([
            measurement("geometric blur", 0.2, "  ", "scene_value"),
            measurement("source-precision", 10, "bits", ""),
            measurement("color", 0.8, "deltaE", "display_value"),
        ]))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "clarification_required")
        self.assertEqual(result["rejectedClaims"], ["geometric blur", "source-precision"])
        self.assertEqual(result["preservedResults"], ["color"])

    def test_bare_number_is_not_allowed(self):
        result = evaluate(payload([
            measurement("timing", 0, None, None),
        ]))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "clarification_required")
        self.assertEqual(result["rejectedClaims"], ["timing"])
        self.assertEqual(result["preservedResults"], [])
        self.assertNotEqual(result["decision"], "allowed")
        self.assertTrue(any("bare number" in reason for reason in result["reasons"]))

    def test_elapsed_ms_versus_us_is_blocked_and_names_both_domains(self):
        result = evaluate(payload([
            measurement("timing", 5, "ms", "elapsed_ms"),
            measurement("timing-us", 5000, "us", "elapsed_us"),
        ], compare=["timing", "timing-us"]))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        named = " ".join(result["reasons"])
        self.assertIn("elapsed_ms", named)
        self.assertIn("elapsed_us", named)
        self.assertEqual(result["preservedResults"], ["timing", "timing-us"])
        self.assertTrue(result["rejectedClaims"])

    def test_display_versus_scene_is_blocked_even_when_units_match(self):
        result = evaluate(payload([
            measurement("color", 0.4, "deltaE", "display_value"),
            measurement("scene color", 0.4, "deltaE", "scene_value"),
        ], compare=["color", "scene color"]))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        named = " ".join(result["reasons"])
        self.assertIn("display_value", named)
        self.assertIn("scene_value", named)
        self.assertNotEqual(result["decision"], "allowed")
        self.assertNotEqual(result["decision"], "comparable")

    def test_same_domain_compare_is_comparable(self):
        result = evaluate(payload([
            measurement("timing", 16, "ms", "elapsed_ms"),
            measurement("render timing", 18, "ms", "elapsed_ms"),
        ], compare=["render timing", "timing"]))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "comparable")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["timing", "render timing"])
        self.assertIn("elapsed_ms", " ".join(result["reasons"]))

    def test_null_compare_with_qualified_measurements_is_comparable(self):
        result = evaluate(payload([
            measurement("memory", 64, "MiB", "process_rss"),
            measurement("color", 2, "deltaE", "scene_value"),
        ], compare=None))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "comparable")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["memory", "color"])
        self.assertEqual(result["openQuestions"], [])

    def test_omitted_compare_is_comparable_when_qualified(self):
        body = {
            "caseId": CASE_ID,
            "measurements": [measurement("timing", 1, "ms", "elapsed_ms")],
        }
        result = evaluate(body)
        assert_contract(self, result)
        self.assertEqual(result["decision"], "comparable")

    def test_incomplete_measurement_takes_priority_over_domain_mismatch(self):
        result = evaluate(payload([
            measurement("timing", 4, "ms", "elapsed_ms"),
            measurement("timing-us", 9, None, "elapsed_us"),
        ], compare=["timing", "timing-us"]))
        assert_contract(self, result)
        self.assertEqual(result["decision"], "clarification_required")
        self.assertIn("timing-us", result["rejectedClaims"])
        self.assertIn("timing", result["preservedResults"])
        self.assertNotEqual(result["decision"], "allowed")

    def test_repetition_across_timing_color_memory_blur_and_source_precision(self):
        foils = {
            "elapsed_ms": "elapsed_us",
            "display_value": "scene_value",
            "process_rss": "gpu_rss",
            "scene_value": "display_value",
            "source_code_value": "encoded_value",
        }
        for name, unit, domain, value in REPETITIONS:
            missing_unit = evaluate(payload([
                measurement(name, value, None, domain),
                measurement("kept", 1, unit, domain),
            ]))
            assert_contract(self, missing_unit)
            self.assertEqual(missing_unit["decision"], "clarification_required")
            self.assertIn(name, missing_unit["rejectedClaims"])
            self.assertIn("kept", missing_unit["preservedResults"])
            self.assertNotIn(name, missing_unit["preservedResults"])

            missing_domain = evaluate(payload([
                measurement(name, value, unit, None),
                measurement("kept", 1, unit, domain),
            ]))
            assert_contract(self, missing_domain)
            self.assertEqual(missing_domain["decision"], "clarification_required")
            self.assertEqual(missing_domain["rejectedClaims"], [name])
            self.assertEqual(missing_domain["preservedResults"], ["kept"])

            bare = evaluate(payload([measurement(name, value, None, None)]))
            assert_contract(self, bare)
            self.assertEqual(bare["decision"], "clarification_required")
            self.assertNotEqual(bare["decision"], "allowed")
            self.assertIn(name, bare["rejectedClaims"])

            qualified = evaluate(payload([
                measurement(name, value, unit, domain),
                measurement(name + " pair", value, unit, domain),
            ], compare=[name, name + " pair"]))
            assert_contract(self, qualified)
            self.assertEqual(qualified["decision"], "comparable")
            self.assertIn(domain, " ".join(qualified["reasons"]))

            other_domain = foils[domain]
            blocked = evaluate(payload([
                measurement(name, value, unit, domain),
                measurement(name + " other", value, unit, other_domain),
            ], compare=[name, name + " other"]))
            assert_contract(self, blocked)
            self.assertEqual(blocked["decision"], "blocked")
            named = " ".join(blocked["reasons"])
            self.assertIn(domain, named)
            self.assertIn(other_domain, named)
            self.assertIn(name, blocked["preservedResults"])

    def test_wrong_case_id_and_bad_payload_raise_value_error(self):
        good = [measurement("timing", 1, "ms", "elapsed_ms")]
        with self.assertRaises(ValueError):
            evaluate(payload(good, case_id="TC-P006-06"))
        with self.assertRaises(ValueError):
            evaluate(payload(good, case_id="TC-P006-05 "))
        for bad in (
            None,
            [],
            "timing",
            {"measurements": good, "compare": None},
            {"caseId": CASE_ID, "compare": None},
            {"caseId": CASE_ID, "measurements": None, "compare": None},
            {"caseId": CASE_ID, "measurements": [None], "compare": None},
            {"caseId": CASE_ID, "measurements": [{"value": 1, "unit": "ms", "domain": "elapsed_ms"}], "compare": None},
            {"caseId": CASE_ID, "measurements": [{"name": "", "value": 1, "unit": "ms", "domain": "elapsed_ms"}], "compare": None},
            {"caseId": CASE_ID, "measurements": [{"name": "timing", "value": True, "unit": "ms", "domain": "elapsed_ms"}], "compare": None},
            {"caseId": CASE_ID, "measurements": [{"name": "timing", "value": "12", "unit": "ms", "domain": "elapsed_ms"}], "compare": None},
            {"caseId": CASE_ID, "measurements": [{"name": "timing", "value": math.nan, "unit": "ms", "domain": "elapsed_ms"}], "compare": None},
            {"caseId": CASE_ID, "measurements": [{"name": "timing", "value": math.inf, "unit": "ms", "domain": "elapsed_ms"}], "compare": None},
            {"caseId": CASE_ID, "measurements": [{"name": "timing", "value": 1, "unit": 1, "domain": "elapsed_ms"}], "compare": None},
            {"caseId": CASE_ID, "measurements": [{"name": "timing", "value": 1, "unit": "ms", "domain": 2}], "compare": None},
            payload(good, compare=["timing"]),
            payload(good, compare=["timing", "missing"]),
            payload(good, compare="timing"),
            payload(
                [
                    measurement("timing", 1, "ms", "elapsed_ms"),
                    measurement("timing", 2, "ms", "elapsed_ms"),
                ]
            ),
        ):
            with self.assertRaises(ValueError):
                evaluate(bad)


if __name__ == "__main__":
    unittest.main()
