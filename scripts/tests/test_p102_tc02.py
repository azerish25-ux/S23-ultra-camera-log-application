"""Tests for TC-P102-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p102_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p102_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def corners(width, height, scale_x, scale_y, pad_x, pad_y):
    markers = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    output = [[x * scale_x + pad_x, y * scale_y + pad_y] for x, y in markers]
    restored = [[x, y] for x, y in markers]
    return output, restored


def payload(**overrides):
    width, height = 1920, 1080
    scale_x, scale_y, pad_x, pad_y = 1, 1, 0, 420
    output, restored = corners(width, height, scale_x, scale_y, pad_x, pad_y)
    base = {
        "evidenceId": "p102-evidence",
        "repeat": "landscape",
        "width": width,
        "height": height,
        "scaleX": scale_x,
        "scaleY": scale_y,
        "padX": pad_x,
        "padY": pad_y,
        "channelOrder": "RGB",
        "stretchRecorded": False,
        "outputCorners": output,
        "restoredCorners": restored,
    }
    base.update(overrides)
    return base


class TCP10202(unittest.TestCase):
    def assert_contract(self, result, evidence="p102-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P102-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any(item == "physical S23 measurement was not run" for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_good_input_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_directive_negative_is_rejected(self):
        output, restored = corners(1920, 1080, 1, 2, 0, 0)
        result = evaluate(payload(
            scaleY=2,
            padY=0,
            stretchRecorded=False,
            outputCorners=output,
            restoredCorners=restored,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrecorded-stretching-swapped-color-channels-fail", result["rejectedClaims"])

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p102-tc02-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(width=1080, height=1080))
