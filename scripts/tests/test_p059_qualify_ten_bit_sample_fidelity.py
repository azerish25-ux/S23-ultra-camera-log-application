"""Host checks for the P059 ten-bit sample-fidelity fixture. Not a physical S23 probe.

TC-P059-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p059_qualify_ten_bit_sample_fidelity import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_TEST,
    ORACLE,
    assess,
    eight_bit_pattern,
    pack_msb,
    quantize_eight,
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
    path = ROOT / "docs" / "P059_QUALIFY_TEN_BIT_SAMPLE_FIDELITY.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P059TenBitFidelityTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P059")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "ten_bit_fidelity"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P059")
        self.assertEqual(MAP_ID, "s23-ten-bit-sample-fidelity-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("high-resolution code ramp", METHOD)
        self.assertIn("eight-bit-degraded negative control", METHOD)
        self.assertIn("SPS and decoded sample layout", METHOD)
        self.assertIn("codec, configuration, and software build", METHOD)
        self.assertEqual(
            FIXTURE,
            "A Main10 stream carrying an eight-bit-quantized ramp expanded into ten-bit sample "
            "containers.",
        )
        self.assertEqual(
            ORACLE,
            "The negative control fails precision criteria even though its bitstream advertises "
            "ten-bit storage.",
        )
        self.assertEqual(MUTANT, "Accept ten-bit fidelity from SPS bit depth alone.")
        self.assertEqual(quantize_eight(1), 0)
        self.assertEqual(quantize_eight(1023), 1020)
        self.assertEqual(pack_msb(4), 256)

    def test_fixture_fails_precision_and_keeps_the_ramp(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P059")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        reference = [int(item) for item in raw["referenceRamp"]]
        decoded = [int(item) for item in raw["decoded"]]
        self.assertEqual(decoded, [quantize_eight(code) for code in reference])
        self.assertTrue(eight_bit_pattern(reference, decoded))
        self.assertEqual([int(item) for item in raw["packedWords"]], [pack_msb(code) for code in decoded])
        self.assertEqual(int(raw["sps"]["bitDepthLumaMinus8"]) + 8, 10)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "precision_failed")
        self.assertEqual(result["rejectedClaims"], ["eight-bit-quantized-ramp"])
        self.assertNotIn("sps-bit-depth-alone", result["rejectedClaims"])
        self.assertIn("codec:hevc", result["preservedResults"])
        self.assertIn("profile:Main10", result["preservedResults"])
        self.assertIn("configuration:main10-high-tier-level51", result["preservedResults"])
        self.assertIn("softwareBuild:host-fixture-p059", result["preservedResults"])
        self.assertIn(
            "binding:hevc|main10-high-tier-level51|host-fixture-p059",
            result["preservedResults"],
        )
        self.assertIn("sps-luma-depth:10", result["preservedResults"])
        self.assertIn("sps-chroma-depth:10", result["preservedResults"])
        self.assertIn("chroma-format:4:2:0", result["preservedResults"])
        self.assertIn("layout:P010:msb", result["preservedResults"])
        self.assertIn("size:3840x8", result["preservedResults"])
        self.assertIn("stride:3840", result["preservedResults"])
        self.assertIn("quantization:eight-bit-expanded", result["preservedResults"])
        self.assertIn("unique-decoded:6", result["preservedResults"])
        self.assertIn("mismatch-count:7", result["preservedResults"])
        self.assertIn("pair:1:1->0", result["preservedResults"])
        self.assertIn("pair:10:1023->1020", result["preservedResults"])
        self.assertIn("word:4:256", result["preservedResults"])
        self.assertIn("word:10:65280", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertTrue(any("SPS bit depth 10 does not" in item for item in result["openQuestions"]))
        self.assertTrue(any("not a physical S23" in item for item in result["openQuestions"]))
        self.assertNotIn(MUTANT, result["reasons"])

    def test_mutant_sps_bit_depth_alone_is_rejected(self) -> None:
        raw = load_document()
        self.assertEqual(int(raw["sps"]["bitDepthLumaMinus8"]) + 8, 10)
        honest = assess(raw)
        mutant = assess(raw, sole_test=MUTANT_TEST)
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "ten_bit_fidelity", "precision_failed"})
        self.assertEqual(
            mutant["rejectedClaims"],
            ["sps-bit-depth-alone", "eight-bit-quantized-ramp"],
        )
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn("pair:1:1->0", mutant["preservedResults"])
        self.assertIn("mismatch-count:7", mutant["preservedResults"])
        self.assertIn("sps-luma-depth:10", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("SPS bit depth was not accepted as ten-bit image fidelity", mutant["reasons"])
        self.assertNotIn("sps-bit-depth-alone", honest["rejectedClaims"])

    def test_mutant_still_rejects_when_numeric_codes_match(self) -> None:
        raw = load_document()
        raw["decoded"] = list(raw["referenceRamp"])
        raw["quantization"] = "ten-bit-native"
        raw["packedWords"] = [str(pack_msb(int(code))) for code in raw["decoded"]]
        self.assertFalse(eight_bit_pattern(
            [int(code) for code in raw["referenceRamp"]],
            [int(code) for code in raw["decoded"]],
        ))
        honest = assess(raw)
        mutant = assess(raw, sole_test="sps-bit-depth-alone")
        self.assertEqual(honest["decision"], "withheld")
        self.assertEqual(honest["rejectedClaims"], [])
        self.assertNotIn(honest["decision"], {"qualified", "allowed", "ten_bit_fidelity"})
        self.assertIn("mismatch-count:0", honest["preservedResults"])
        self.assertIn("a host numeric match is not ten-bit fidelity", " ".join(honest["reasons"]))
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["sps-bit-depth-alone"])
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "withheld", "precision_failed"})

    def test_low_six_alignment_keeps_the_eight_bit_inventory(self) -> None:
        raw = load_document()
        raw["layout"]["alignment"] = "lsb"
        raw["packedWords"] = list(raw["decoded"])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["eight-bit-quantized-ramp", "low-six-bit-alignment"],
        )
        self.assertIn("layout:P010:lsb", result["preservedResults"])
        self.assertIn("pair:10:1023->1020", result["preservedResults"])
        self.assertIn("size:3840x8", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "precision_failed"})

    def test_stride_and_profile_depth_faults_do_not_wipe_pairs(self) -> None:
        narrow = load_document()
        narrow["layout"]["rowStride"] = "16"
        stride = assess(narrow)
        self.assertEqual(stride["decision"], "rejected")
        self.assertIn("stride-below-width", stride["rejectedClaims"])
        self.assertIn("eight-bit-quantized-ramp", stride["rejectedClaims"])
        self.assertIn("stride:16", stride["preservedResults"])
        self.assertIn("size:3840x8", stride["preservedResults"])
        self.assertIn("pair:6:255->252", stride["preservedResults"])
        shallow = load_document()
        shallow["sps"]["bitDepthLumaMinus8"] = "0"
        depth = assess(shallow)
        self.assertEqual(depth["decision"], "rejected")
        self.assertIn("profile-depth-contradiction", depth["rejectedClaims"])
        self.assertIn("sps-luma-depth:8", depth["preservedResults"])
        self.assertIn("pair:1:1->0", depth["preservedResults"])
        self.assertNotIn(depth["decision"], {"qualified", "allowed"})

    def test_label_contradiction_and_coarse_ramp_are_rejected(self) -> None:
        matched = load_document()
        matched["decoded"] = list(matched["referenceRamp"])
        matched["packedWords"] = [str(pack_msb(int(code))) for code in matched["decoded"]]
        matched["quantization"] = "eight-bit-expanded"
        label = assess(matched)
        self.assertEqual(label["decision"], "rejected")
        self.assertEqual(label["rejectedClaims"], ["quantization-label-contradiction"])
        self.assertIn("mismatch-count:0", label["preservedResults"])
        self.assertIn("quantization:eight-bit-expanded", label["preservedResults"])
        coarse = load_document()
        coarse["referenceRamp"] = ["0", "4", "8", "12"]
        coarse["decoded"] = ["0", "4", "8", "12"]
        coarse["packedWords"] = [str(pack_msb(code)) for code in (0, 4, 8, 12)]
        coarse["quantization"] = "ten-bit-native"
        result = assess(coarse)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("ramp-not-high-resolution", result["rejectedClaims"])
        self.assertIn("pair:3:12->12", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_software_build_binding_is_preserved_on_failure(self) -> None:
        raw = load_document()
        raw["softwareBuild"] = "host-fixture-p059-alt"
        result = assess(raw)
        self.assertEqual(result["decision"], "precision_failed")
        self.assertIn("softwareBuild:host-fixture-p059-alt", result["preservedResults"])
        self.assertNotIn("softwareBuild:host-fixture-p059", result["preservedResults"])
        self.assertIn(
            "binding:hevc|main10-high-tier-level51|host-fixture-p059-alt",
            result["preservedResults"],
        )
        self.assertIn("eight-bit-quantized-ramp", result["rejectedClaims"])

    def test_unpacked_word_mismatch_is_rejected(self) -> None:
        raw = load_document()
        raw["packedWords"][4] = "4"
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unpacked-word-mismatch", result["rejectedClaims"])
        self.assertIn("word:4:4", result["preservedResults"])
        self.assertIn("pair:4:4->4", result["preservedResults"])

    def test_invalid_document_and_sole_test_raise(self) -> None:
        raw = load_document()
        cases = []
        broken = copy.deepcopy(raw)
        broken["schemaVersion"] = 2
        cases.append(broken)
        extra = copy.deepcopy(raw)
        extra["extra"] = True
        cases.append(extra)
        phase = copy.deepcopy(raw)
        phase["phase"] = "P058"
        cases.append(phase)
        coded = copy.deepcopy(raw)
        coded["decoded"][0] = 0
        cases.append(coded)
        align = copy.deepcopy(raw)
        align["layout"]["alignment"] = "MSB"
        cases.append(align)
        short = copy.deepcopy(raw)
        short["referenceRamp"] = raw["referenceRamp"][:-1]
        cases.append(short)
        for item in cases:
            with self.subTest(phase=item.get("phase")):
                with self.assertRaises(ValueError):
                    validate_document(item)
        with self.assertRaises(ValueError):
            assess(raw, sole_test="qualified")
        with self.assertRaises(ValueError):
            assess(raw, sole_test="allowed")


if __name__ == "__main__":
    unittest.main()
