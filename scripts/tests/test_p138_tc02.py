"""Tests for TC-P138-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p138_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p138_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p138-tc02",
        "repeat": "mixed color/monochrome",
        "family": _GATE.sample_family(),
        "max_entries": 12,
        "sourceMethods": ["daylight", "low-light", "monochrome", "format"],
        "sceneIds": ["scene-12"],
        "assignToEveryShot": False,
    }
    base.update(overrides)
    return base


class TCP13802(unittest.TestCase):
    def assert_contract(self, result, evidence="p138-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P138-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_supported_variants_keep_scene_uncertainty(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][2]
        self.assertEqual(detail["sceneStock"], [None])
        self.assertEqual(detail["sceneLens"], [None])
        self.assertIn("monochrome", detail["variantsPresent"])
        self.assertIn("format", detail["variantsPresent"])
        self.assertTrue(_MODULE.CASE["negative"].startswith("A title match alone must not"))

    def test_title_match_assigned_to_every_scene_is_rejected(self):
        family = [
            _GATE.make_entry(
                f"scene-{index}",
                stock="5219",
                lens="Cooke S4 35mm",
                traces=[],
                scope="every-shot",
                documented=True,
            )
            for index in (1, 2)
        ]
        result = evaluate(payload(
            family=family,
            sourceMethods=["daylight", "low-light"],
            sceneIds=["scene-1", "scene-2"],
            assignToEveryShot=True,
            repeat="location-specific stock",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.TITLE_MATCH, result["rejectedClaims"])
        self.assertIn("supported-variants-not-separated", result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["sceneStock"], ["5219", "5219"])

    def test_mixed_format_repeat_preserves_a_different_evidence_id(self):
        evidence = "p138-tc02-formats"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="mixed formats",
            sourceMethods=["format", "monochrome"],
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_filled_scene_is_rejected_without_the_flag(self):
        family = _GATE.sample_family()
        family[4] = _GATE.make_entry(
            "scene-12",
            stock="5219",
            traces=[_GATE.trace("stock", "title-only")],
            variant="scene",
            scope="scene 12 only",
            documented=True,
        )
        result = evaluate(payload(family=family, assignToEveryShot=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceMethods=["daylight"]))
        with self.assertRaises(ValueError):
            evaluate(payload(sceneIds=["missing-scene"]))
