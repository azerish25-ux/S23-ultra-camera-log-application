"""Tests for TC-P132-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p132_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p132_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def spoken_controls(scopes=None, source=None):
    scopes = _GATE.fixture_scopes() if scopes is None else scopes
    source = _GATE.fixture_source() if source is None else source
    info = _GATE.analyze(_GATE.parse_scopes(scopes), _GATE.parse_source(source), False)
    controls = [
        {"name": record["id"], "value": _MODULE.spoken_value(record), "cancellable": True}
        for record in info["records"]
    ]
    controls.append({
        "name": "source",
        "value": f"domain={info['sourceDomain']} clippingCount={info['sourceClippingCount']}",
        "cancellable": True,
    })
    return controls


def payload(**overrides):
    base = {
        "evidenceId": "p132-tc05",
        "repeat": "camera operation",
        "scopes": _GATE.fixture_scopes(),
        "source": _GATE.fixture_source(),
        "applyMutant": False,
        "unlabeledCanvasOnly": False,
        "controls": spoken_controls(),
    }
    base.update(overrides)
    return base


class TCP13205(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P132-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_spoken_domains_and_clipping_count_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)
        self.assertTrue(result["preservedResults"][2]["clippingSpoken"])
        self.assertIn("clippingCount=3", payload()["controls"][1]["value"])

    def test_unlabeled_canvas_is_rejected(self):
        result = evaluate(payload(unlabeledCanvasOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_a_wrong_spoken_clipping_count_is_rejected(self):
        controls = spoken_controls()
        controls[1] = dict(controls[1])
        controls[1]["value"] = controls[1]["value"].replace("clippingCount=3", "clippingCount=9")
        result = evaluate(payload(controls=controls))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)

    def test_blank_control_name_is_rejected(self):
        controls = spoken_controls()
        controls[0] = dict(controls[0])
        controls[0]["name"] = " "
        result = evaluate(payload(controls=controls))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(controls=[{"name": "only"}]))
