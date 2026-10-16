"""Tests for TC-P121-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p121_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p121_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p121-untagged",
        "repeat": "hdr-untagged",
        "filename": "untagged-hdr.mov",
        "detectedTransfer": None,
        "containerTransfer": None,
        "detectedRange": None,
        "detectedRotation": 0,
        "detectedTiming": "constant",
        "userTransfer": "explicit-untagged-not-sdr",
        "userRange": "explicit-unknown-range",
        "userRotationPolicy": None,
        "userTimingPolicy": None,
        "emittedTransfer": None,
        "emittedRange": None,
        "emittedRotation": None,
        "emittedTiming": None,
        "extensionDecidesColor": False,
    }
    base.update(overrides)
    return base


class TCP12101(unittest.TestCase):
    def assert_contract(self, result, evidence="p121-untagged"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P121-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Ambiguous imported signal")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Import media with absent or contradictory color tags, rotation, or timing metadata.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Separate detected facts from user interpretation and avoid silent normalization to an assumed source type.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Filename extension alone must not determine transfer or dynamic range.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat HDR-looking untagged clips, variable rates, and portrait rotation.",
        )

    def test_untagged_facts_stay_separate_from_interpretation(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertIsNone(kept["facts"]["transfer"])
        self.assertEqual(kept["interpretation"]["transfer"], "explicit-untagged-not-sdr")
        self.assertIsNone(kept["emitted"]["transfer"])

    def test_filename_extension_and_silent_sdr_are_rejected(self):
        result = evaluate(payload(extensionDecidesColor=True, emittedTransfer="bt709"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("silent-normalization-to-assumed-source", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIsNone(result["preservedResults"][1]["facts"]["transfer"])
        self.assertEqual(result["preservedResults"][1]["emitted"]["transfer"], "bt709")

    def test_portrait_rotation_requires_a_declared_policy(self):
        clean = evaluate(
            payload(
                evidenceId="p121-portrait",
                repeat="portrait-rotation",
                filename="portrait.mov",
                detectedTransfer="bt709",
                detectedRange="tv",
                detectedRotation=90,
                userRotationPolicy="declared-portrait",
                emittedTransfer="bt709",
                emittedRange="tv",
                emittedRotation=90,
                userTransfer=None,
                userRange=None,
            )
        )
        self.assert_contract(clean, "p121-portrait")
        self.assertEqual(clean["decision"], "recorded")
        self.assertEqual(clean["preservedResults"][1]["facts"]["rotation"], 90)
        hidden = evaluate(payload(repeat="portrait-rotation", detectedRotation=90, emittedRotation=0))
        self.assertEqual(hidden["decision"], "rejected")
        self.assertIn("rotated-media-without-declared-policy", hidden["rejectedClaims"])
        self.assertIn("silent-normalization-to-assumed-source", hidden["rejectedClaims"])

    def test_variable_rate_and_contradictory_tags(self):
        clean = evaluate(
            payload(
                evidenceId="p121-vfr",
                repeat="variable-rate",
                detectedTiming="vfr",
                userTimingPolicy="declared-vfr",
                emittedTiming="vfr",
            )
        )
        self.assert_contract(clean, "p121-vfr")
        self.assertEqual(clean["decision"], "recorded")
        conflict = evaluate(
            payload(
                detectedTransfer="bt709",
                containerTransfer="smpte2084",
                emittedTransfer="bt709",
            )
        )
        self.assertEqual(conflict["decision"], "rejected")
        self.assertIn("contradictory-color-tags-resolved-silently", conflict["rejectedClaims"])
        kept = conflict["preservedResults"][1]["facts"]
        self.assertEqual(kept["transfer"], "bt709")
        self.assertEqual(kept["containerTransfer"], "smpte2084")
        open_conflict = evaluate(payload(detectedTransfer="bt709", containerTransfer="smpte2084"))
        self.assertEqual(open_conflict["decision"], "recorded")
        self.assertIsNone(open_conflict["preservedResults"][1]["emitted"]["transfer"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(detectedRotation=45))
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="other"))
