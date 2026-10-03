"""TC-P055-04 nonlinear processing order."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p055_tc04", Path(__file__).resolve().parents[1] / "gates" / "p055_tc04.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def payload(**overrides):
    base = {
        "graphId": "color-graph",
        "operation": "color",
        "domain": "scene-linear",
        "movedAcrossBoundary": False,
        "referenceAgrees": True,
        "visuallyPlausible": True,
    }
    base.update(overrides)
    return base


class TcP05504(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P055-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "A visually plausible result is insufficient when operation order violates the contract.",
        )
        self.assertIn("encoding boundary", _MODULE.INTERVENTION)

    def test_declared_order_is_held(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "order_held")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("domain:scene-linear", result["preservedResults"])
        self.assertIn("operation:color", result["preservedResults"])

    def test_repeat_logarithmic_disagreement_is_rejected(self):
        result = evaluate(
            payload(
                operation="exposure-scale",
                domain="logarithmic",
                movedAcrossBoundary=True,
                referenceAgrees=False,
                visuallyPlausible=False,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["altered-graph"])
        self.assertIn("domain:logarithmic", result["preservedResults"])
        self.assertIn("graph:color-graph", result["preservedResults"])

    def test_repeat_display_encoded_plausible_result_still_fails(self):
        result = evaluate(
            payload(
                operation="blur",
                domain="display-encoded",
                movedAcrossBoundary=True,
                referenceAgrees=False,
                visuallyPlausible=True,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["altered-graph", "visually-plausible-insufficient"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("domain:display-encoded", result["preservedResults"])
        self.assertIn("plausible:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "order_held"})

    def test_repeat_scene_linear_move_without_disagreement_is_withheld(self):
        result = evaluate(payload(operation="reduction", movedAcrossBoundary=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("domain:scene-linear", result["preservedResults"])
        self.assertIn("operation:reduction", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "domain": "aces"},
            {**valid, "operation": "sharpen"},
            {**valid, "visuallyPlausible": "yes"},
            {**valid, "graphId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
