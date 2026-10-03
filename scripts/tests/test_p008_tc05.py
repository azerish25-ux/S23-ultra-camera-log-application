"""Tests for TC-P008-05 measurement unit and domain gate."""

from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

_GATE = Path(__file__).resolve().parents[1] / "gates" / "p008_tc05.py"
_SPEC = importlib.util.spec_from_file_location("p008_tc05", _GATE)
assert _SPEC is not None and _SPEC.loader is not None
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)

KEYS = {"caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"}
REMOTE = "0123456789abcdef0123456789abcdef01234567"


def measurement(name, value, unit, domain):
    return {"name": name, "value": value, "unit": unit, "domain": domain}


def payload(measurements, compare, remote=REMOTE, local_build=True):
    return {
        "measurements": measurements,
        "compare": compare,
        "remoteCommit": remote,
        "localBuildSucceeded": local_build,
    }


class P008Tc05Test(unittest.TestCase):
    def assert_contract(self, result, decision):
        self.assertEqual(KEYS, set(result))
        self.assertEqual(
            ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"],
            list(result),
        )
        self.assertEqual("TC-P008-05", result["caseId"])
        self.assertEqual(decision, result["decision"])
        self.assertNotIn(result["decision"], {"allowed", "complete"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertIn(REMOTE, result["preservedResults"])
        self.assertIn("physical-device gate pending", result["openQuestions"])

    def test_timing_missing_unit_requires_clarification_and_preserves_complete_peer(self):
        result = gate.evaluate(payload([
            measurement("frame interval", 16.7, None, "sensor_time"),
            measurement("nominal interval", 16.67, "ms", "sensor_time"),
        ], ["frame interval", "nominal interval"]))
        self.assert_contract(result, "clarification_required")
        self.assertEqual(["frame interval"], result["rejectedClaims"])
        self.assertEqual(["nominal interval", REMOTE], result["preservedResults"])
        self.assertIn("unit or domain missing for frame interval", result["openQuestions"])

    def test_timing_blank_domain_is_missing_not_comparable(self):
        result = gate.evaluate(payload([
            measurement("cadence", 24, "ms", "   "),
        ], None, local_build=False))
        self.assert_contract(result, "clarification_required")
        self.assertEqual(["cadence"], result["rejectedClaims"])
        self.assertEqual([REMOTE], result["preservedResults"])

    def test_timing_milliseconds_versus_microseconds_is_blocked(self):
        for left_unit, right_unit in (("ms", "us"), ("milliseconds", "microseconds"), ("ms", "µs")):
            with self.subTest(left_unit=left_unit, right_unit=right_unit):
                result = gate.evaluate(payload([
                    measurement("frame interval", 16.7, left_unit, "sensor_time"),
                    measurement("frame interval scaled", 16700, right_unit, "sensor_time"),
                ], ["frame interval", "frame interval scaled"]))
                self.assert_contract(result, "blocked")
                self.assertIn("frame interval", result["rejectedClaims"])
                self.assertIn("frame interval scaled", result["rejectedClaims"])
                self.assertIn("frame interval vs frame interval scaled", result["rejectedClaims"])
                self.assertIn("frame interval", result["preservedResults"])
                self.assertNotIn(result["decision"], {"allowed", "complete", "comparable"})

    def test_timing_same_unit_and_domain_is_comparable_not_complete(self):
        for local_build in (True, False):
            with self.subTest(local_build=local_build):
                result = gate.evaluate(payload([
                    measurement("frame interval", 16.7, "ms", "sensor_time"),
                    measurement("expected interval", 16.67, "milliseconds", "sensor_time"),
                ], ["frame interval", "expected interval"], local_build=local_build))
                self.assert_contract(result, "comparable")
                self.assertEqual([], result["rejectedClaims"])
                self.assertEqual(["frame interval", "expected interval", REMOTE], result["preservedResults"])
                if local_build:
                    self.assertTrue(any("Local build success" in reason for reason in result["reasons"]))

    def test_color_display_versus_scene_is_blocked(self):
        result = gate.evaluate(payload([
            measurement("display color", 1.4, "deltaE", "display"),
            measurement("scene color", 1.4, "deltaE", "scene"),
        ], ["display color", "scene color"]))
        self.assert_contract(result, "blocked")
        self.assertIn("display color vs scene color", result["rejectedClaims"])
        self.assertIn("display color", result["preservedResults"])
        self.assertIn("scene color", result["preservedResults"])

    def test_color_missing_domain_preserves_complete_measurement(self):
        result = gate.evaluate(payload([
            measurement("display color", 2.0, "deltaE", None),
            measurement("reference color", 1.0, "deltaE", "display"),
        ], None))
        self.assert_contract(result, "clarification_required")
        self.assertEqual(["display color"], result["rejectedClaims"])
        self.assertEqual(["reference color", REMOTE], result["preservedResults"])
        self.assertNotIn("complete", result["decision"])
        self.assertNotEqual("allowed", result["decision"])

    def test_color_same_display_domain_is_comparable_despite_local_build(self):
        result = gate.evaluate(payload([
            measurement("display color", 1.1, "deltaE", "Display"),
            measurement("display limit", 2.0, "deltaE", "display"),
        ], ["display color", "display limit"], local_build=True))
        self.assert_contract(result, "comparable")
        self.assertNotEqual("complete", result["decision"])

    def test_memory_missing_unit_and_byte_versus_mebibyte_are_distinct(self):
        missing = gate.evaluate(payload([
            measurement("heap", 128, None, "process"),
            measurement("codec buffer", 64, "MiB", "process"),
        ], ["heap", "codec buffer"]))
        self.assert_contract(missing, "clarification_required")
        self.assertIn("heap", missing["rejectedClaims"])
        self.assertIn("codec buffer", missing["preservedResults"])

        blocked = gate.evaluate(payload([
            measurement("heap", 128, "MiB", "process"),
            measurement("codec buffer", 134217728, "bytes", "process"),
        ], ["heap", "codec buffer"]))
        self.assert_contract(blocked, "blocked")
        self.assertIn("heap vs codec buffer", blocked["rejectedClaims"])

        comparable = gate.evaluate(payload([
            measurement("heap", 128, "MiB", "process"),
            measurement("budget", 256, "MiB", "process"),
        ], ["heap", "budget"], local_build=True))
        self.assert_contract(comparable, "comparable")

    def test_geometric_blur_display_versus_scene_and_missing_domain(self):
        blocked = gate.evaluate(payload([
            measurement("geometric blur", 1.5, "px", "display"),
            measurement("scene blur", 0.02, "px", "scene"),
        ], ["geometric blur", "scene blur"]))
        self.assert_contract(blocked, "blocked")
        self.assertIn("geometric blur vs scene blur", blocked["rejectedClaims"])

        missing = gate.evaluate(payload([
            measurement("geometric blur", 1.5, "px", None),
            measurement("reference blur", 1.0, "px", "display"),
        ], None))
        self.assert_contract(missing, "clarification_required")
        self.assertEqual(["geometric blur"], missing["rejectedClaims"])
        self.assertIn("reference blur", missing["preservedResults"])

        same = gate.evaluate(payload([
            measurement("geometric blur", 1.5, "px", "display"),
            measurement("blur limit", 2.0, "px", "display"),
        ], ["geometric blur", "blur limit"]))
        self.assert_contract(same, "comparable")

    def test_source_precision_missing_unit_and_sensor_versus_codec_domain(self):
        missing = gate.evaluate(payload([
            measurement("source precision", 10, None, "sensor"),
            measurement("declared bits", 10, "bits", "sensor"),
        ], ["source precision", "declared bits"]))
        self.assert_contract(missing, "clarification_required")
        self.assertEqual(["source precision"], missing["rejectedClaims"])
        self.assertEqual(["declared bits", REMOTE], missing["preservedResults"])

        blocked = gate.evaluate(payload([
            measurement("source precision", 10, "bits", "sensor"),
            measurement("codec precision", 10, "bits", "codec"),
        ], ["source precision", "codec precision"], local_build=True))
        self.assert_contract(blocked, "blocked")
        self.assertNotEqual("complete", blocked["decision"])

        comparable = gate.evaluate(payload([
            measurement("source precision", 10, "bits", "sensor"),
            measurement("precision floor", 10, "bits", "sensor"),
        ], ["source precision", "precision floor"], local_build=True))
        self.assert_contract(comparable, "comparable")
        self.assertIn(REMOTE, comparable["preservedResults"])

    def test_omitted_unit_key_matches_explicit_null(self):
        result = gate.evaluate({
            "measurements": [
                {"name": "render latency", "value": 8, "domain": "pipeline"},
                {"name": "budget", "value": 10, "unit": "ms", "domain": "pipeline"},
            ],
            "compare": None,
            "remoteCommit": REMOTE,
            "localBuildSucceeded": True,
        })
        self.assert_contract(result, "clarification_required")
        self.assertEqual(["render latency"], result["rejectedClaims"])
        self.assertEqual(["budget", REMOTE], result["preservedResults"])

    def test_no_compare_with_complete_measurements_is_comparable(self):
        result = gate.evaluate(payload([
            measurement("frame interval", 16.7, "ms", "sensor_time"),
        ], None, local_build=True))
        self.assert_contract(result, "comparable")

    def test_bad_input_raises_value_error(self):
        valid = payload([measurement("frame interval", 1, "ms", "sensor_time")], None)
        with self.assertRaises(ValueError):
            gate.evaluate(None)
        with self.assertRaises(ValueError):
            gate.evaluate([])
        missing = dict(valid)
        del missing["remoteCommit"]
        with self.assertRaises(ValueError):
            gate.evaluate(missing)
        with self.assertRaises(ValueError):
            gate.evaluate(payload([], None))
        with self.assertRaises(ValueError):
            gate.evaluate(payload([{"name": "frame interval", "unit": "ms", "domain": "sensor_time"}], None))
        with self.assertRaises(ValueError):
            gate.evaluate(payload([measurement("frame interval", True, "ms", "sensor_time")], None))
        with self.assertRaises(ValueError):
            gate.evaluate(payload([measurement("frame interval", math.nan, "ms", "sensor_time")], None))
        with self.assertRaises(ValueError):
            gate.evaluate(payload([measurement("frame interval", 1, 1, "sensor_time")], None))
        with self.assertRaises(ValueError):
            gate.evaluate(payload([
                measurement("frame interval", 1, "ms", "sensor_time"),
                measurement("frame interval", 2, "ms", "sensor_time"),
            ], None))
        with self.assertRaises(ValueError):
            gate.evaluate(payload([measurement("frame interval", 1, "ms", "sensor_time")], ["missing", "frame interval"]))
        with self.assertRaises(ValueError):
            gate.evaluate(payload([measurement("frame interval", 1, "ms", "sensor_time")], ["frame interval"]))
        with self.assertRaises(ValueError):
            gate.evaluate(payload([measurement("frame interval", 1, "ms", "sensor_time")], None, remote="  "))
        with self.assertRaises(ValueError):
            gate.evaluate({
                "measurements": [measurement("frame interval", 1, "ms", "sensor_time")],
                "compare": None,
                "remoteCommit": REMOTE,
                "localBuildSucceeded": 1,
            })


if __name__ == "__main__":
    unittest.main()
