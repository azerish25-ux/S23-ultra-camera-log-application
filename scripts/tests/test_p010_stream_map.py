"""Host checks for the P010 ordinary stream map. Not a physical S23 probe.

TC-P010-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p010_stream_map import assess_combination, export_streams, validate_map


BASE = "fffd5c9a63cb732e103052acae29ae0c251585cc"
RESULT_KEYS = ("decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_map() -> dict:
    return json.loads((ROOT / "docs" / "STREAM_MAP.json").read_text(encoding="utf-8"))


def stream(**overrides) -> dict:
    value = {
        "logicalId": "0",
        "format": "YUV_420_888",
        "width": 1920,
        "height": 1080,
        "advertised": True,
        "minFps": "24",
        "maxFps": "30",
        "fixedCadenceEvidence": False,
        "aeRangeIncludesNominal": True,
        "queryError": None,
    }
    value.update(overrides)
    return value


def document(streams: list[dict], **overrides) -> dict:
    value = {
        "schemaVersion": 1,
        "phase": "P010",
        "mapId": "s23-stream-map-fixture",
        "implementationBaseRevision": BASE,
        "failedProperties": ["dynamicRangeProfiles"],
        "streams": streams,
    }
    value.update(overrides)
    return value


class P010StreamMapTests(unittest.TestCase):
    def test_fixture_validates_and_keeps_advertised_sizes(self) -> None:
        raw = load_map()
        self.assertIsNone(validate_map(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P010")
        self.assertEqual(raw["mapId"], "s23-stream-map-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE)
        self.assertEqual(raw["failedProperties"], ["dynamicRangeProfiles"])
        advertised = [item for item in raw["streams"] if item["advertised"] is True]
        self.assertGreaterEqual(len(advertised), 4)
        self.assertTrue(all(item["logicalId"] == "0" for item in advertised))
        sizes = {(item["width"], item["height"]) for item in advertised}
        self.assertIn((1920, 1080), sizes)
        self.assertIn((3840, 2160), sizes)
        formats = {item["format"] for item in advertised}
        self.assertIn("YUV_420_888", formats)
        self.assertIn("JPEG", formats)
        for item in raw["streams"]:
            self.assertIs(item["advertised"], True)
            self.assertIs(item["fixedCadenceEvidence"], False)
            self.assertIs(item["aeRangeIncludesNominal"], True)
            self.assertIsInstance(item["minFps"], str)
            self.assertIsInstance(item["maxFps"], str)
        fps_values = {item["minFps"] for item in raw["streams"]} | {item["maxFps"] for item in raw["streams"]}
        self.assertIn("30", fps_values)
        self.assertIn("29.97", fps_values)

    def test_export_preserves_3840_and_timing_error_does_not_erase_1080(self) -> None:
        raw = load_map()
        exported = export_streams(raw)
        self.assertEqual(len(exported), len(raw["streams"]))
        identities = [item["identity"] for item in exported]
        self.assertIn("3840x2160:YUV_420_888@0", identities)
        self.assertTrue(any(item.startswith("3840x2160:") for item in identities))
        self.assertIn("1920x1080:YUV_420_888@0", identities)
        timing_errors = [item for item in exported if item["queryError"] == "timing"]
        self.assertEqual(len(timing_errors), 1)
        self.assertEqual(timing_errors[0]["identity"], "1280x720:YUV_420_888@0")
        self.assertIs(timing_errors[0]["advertised"], True)
        self.assertLess(identities.index(timing_errors[0]["identity"]), identities.index("1920x1080:YUV_420_888@0"))
        uhd = next(item for item in exported if item["identity"] == "3840x2160:YUV_420_888@0")
        self.assertEqual(uhd["timing"]["minFps"], "24")
        self.assertEqual(uhd["timing"]["maxFps"], "29.97")
        self.assertIsInstance(uhd["timing"]["maxFps"], str)
        self.assertEqual(
            [item["queryError"] for item in exported],
            ["timing", None, None, None, None, None],
        )

    def test_fixed_cadence_is_withheld_when_only_the_ae_range_matches(self) -> None:
        raw = load_map()
        exported = export_streams(raw)
        self.assertTrue(exported)
        for item in exported:
            self.assertEqual(item["timing"]["fixedCadence"], "withheld")
            self.assertEqual(set(item["timing"]), {"minFps", "maxFps", "fixedCadence"})
        point = stream(width=1280, height=720, minFps="30", maxFps="30",
                       fixedCadenceEvidence=False, aeRangeIncludesNominal=True)
        ranged = stream(width=3840, height=2160, minFps="24", maxFps="29.97",
                        fixedCadenceEvidence=False, aeRangeIncludesNominal=True)
        evidenced = stream(width=640, height=480, minFps="24", maxFps="24",
                           fixedCadenceEvidence=True, aeRangeIncludesNominal=False)
        synthetic = export_streams(document([point, ranged, evidenced], failedProperties=[]))
        self.assertEqual(synthetic[0]["timing"]["fixedCadence"], "withheld")
        self.assertEqual(synthetic[1]["timing"]["fixedCadence"], "withheld")
        self.assertEqual(synthetic[1]["timing"]["maxFps"], "29.97")
        self.assertEqual(synthetic[2]["timing"]["fixedCadence"], "supported")
        self.assertEqual(len(synthetic), 3)

    def test_illegal_combination_rejects_without_deleting_the_export(self) -> None:
        raw = load_map()
        before = export_streams(raw)
        selected = [item["identity"] for item in before]
        result = assess_combination(raw, selected, True)
        after = export_streams(raw)
        self.assertEqual(before, after)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], selected)
        self.assertEqual(result["preservedResults"], selected)
        self.assertIn("3840x2160:YUV_420_888@0", result["preservedResults"])
        self.assertIn("1920x1080:YUV_420_888@0", result["preservedResults"])
        self.assertIn("1280x720:YUV_420_888@0", result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("dynamicRangeProfiles" in item for item in result["openQuestions"]))
        self.assertTrue(any("withheld" in item for item in result["openQuestions"]))
        self.assertEqual(json.loads((ROOT / "docs" / "STREAM_MAP.json").read_text(encoding="utf-8"))["streams"],
                         raw["streams"])

    def test_intact_constraints_are_a_candidate_and_still_preserve_the_export(self) -> None:
        raw = load_map()
        exported = export_streams(raw)
        selected = ["1920x1080:YUV_420_888@0", "1920x1080:JPEG@0"]
        result = assess_combination(raw, selected, False)
        self.assertEqual(result["decision"], "candidate")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], [item["identity"] for item in exported])
        self.assertIn("3840x2160:YUV_420_888@0", result["preservedResults"])
        self.assertGreater(len(result["preservedResults"]), len(selected))

    def test_violated_constraints_stay_rejected_even_with_cadence_evidence(self) -> None:
        raw = load_map()
        mutant = copy.deepcopy(raw)
        for item in mutant["streams"]:
            item["fixedCadenceEvidence"] = True
        selected = [item["identity"] for item in export_streams(mutant)]
        result = assess_combination(mutant, selected, True)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "qualified")
        self.assertEqual(result["rejectedClaims"], selected)
        self.assertEqual(result["preservedResults"], selected)
        self.assertTrue(all(item["timing"]["fixedCadence"] == "supported" for item in export_streams(mutant)))

    def test_invalid_maps_and_selections_raise(self) -> None:
        valid = load_map()
        dropped = copy.deepcopy(valid)
        dropped["streams"] = [item for item in dropped["streams"] if item["queryError"] != "timing"]
        self.assertIsNone(validate_map(dropped))
        numeric_fps = copy.deepcopy(valid)
        numeric_fps["streams"][1]["minFps"] = 30
        float_fps = copy.deepcopy(valid)
        float_fps["streams"][2]["maxFps"] = 29.97
        inverted = copy.deepcopy(valid)
        inverted["streams"][2]["minFps"] = "30"
        inverted["streams"][2]["maxFps"] = "29.97"
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["failedProperties"]
        empty = copy.deepcopy(valid)
        empty["streams"] = []
        duplicate = copy.deepcopy(valid)
        duplicate["streams"].append(copy.deepcopy(duplicate["streams"][1]))
        bad_query = copy.deepcopy(valid)
        bad_query["streams"][0]["queryError"] = ""
        bool_width = copy.deepcopy(valid)
        bool_width["streams"][1]["width"] = True
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            empty,
            numeric_fps,
            float_fps,
            inverted,
            duplicate,
            bad_query,
            bool_width,
            document([stream(logicalId=0)]),
            document([stream(advertised=1)]),
            document([stream(fixedCadenceEvidence=0, aeRangeIncludesNominal=1)]),
            document([stream()], schemaVersion=True),
            document([stream()], phase="P009"),
            document([stream()], mapId="other"),
            document([stream()], implementationBaseRevision="abc"),
            document([stream()], failedProperties=["dynamicRangeProfiles", "dynamicRangeProfiles"]),
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_map(sample)
        with self.assertRaises(ValueError):
            assess_combination(valid, ["not-a-stream"], False)
        with self.assertRaises(ValueError):
            assess_combination(valid, ["1920x1080:YUV_420_888@0"], "true")
        rejected = assess_combination(valid, ["not-a-stream"], True)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertEqual(rejected["rejectedClaims"], ["not-a-stream"])
        self.assertIn("1920x1080:YUV_420_888@0", rejected["preservedResults"])
        self.assertIn("3840x2160:YUV_420_888@0", rejected["preservedResults"])


if __name__ == "__main__":
    unittest.main()
