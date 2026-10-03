"""TC-P073-03 nonmonotonic density fit."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p073_tc03", Path(__file__).resolve().parents[1] / "gates" / "p073_tc03.py"
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
        "region": "toe",
        "smoothLooking": True,
        "reversesWedge": True,
        "declaredBehavior": "monotonic",
        "released": False,
    }
    base.update(overrides)
    return base


class TcP07303(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P073-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("density ordering", _MODULE.INTERVENTION)
        self.assertIn("exposure wedge", _MODULE.NEGATIVE)
        self.assertIn("toe", _MODULE.REPEAT)
        self.assertIn("endpoint", _MODULE.REPEAT)
        self.assertIn("model\u2019s", _MODULE.EXPECTED)

    def test_smooth_toe_reversal_fails(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["wedge-reversal"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("region:toe", result["preservedResults"])
        self.assertIn("smooth:true", result["preservedResults"])
        self.assertIn("wedge-reversed:true", result["preservedResults"])
        self.assertTrue(any("smooth appearance does not excuse" in item for item in result["reasons"]))

    def test_shoulder_repeat_reversal_fails_before_release(self):
        result = evaluate(payload(region="shoulder", smoothLooking=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("region:shoulder", result["preservedResults"])
        self.assertIn("wedge-reversal", result["rejectedClaims"])
        self.assertNotIn("smooth appearance does not excuse a reversed exposure wedge", result["reasons"])

    def test_released_midsection_reversal_keeps_the_region(self):
        result = evaluate(payload(region="midsection", released=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["wedge-reversal", "released-before-constraint"])
        self.assertIn("region:midsection", result["preservedResults"])
        self.assertIn("released:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "fit_constrained"})

    def test_endpoint_monotonic_fit_is_constrained(self):
        result = evaluate(payload(region="endpoint", smoothLooking=False, reversesWedge=False))
        self.assertEqual(result["decision"], "fit_constrained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("region:endpoint", result["preservedResults"])
        self.assertIn("declared:monotonic", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_unconstrained_fit_is_withheld_before_release(self):
        result = evaluate(payload(reversesWedge=False, declaredBehavior="unconstrained", smoothLooking=False))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("region:toe", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_unconstrained_release_is_rejected(self):
        result = evaluate(
            payload(region="endpoint", reversesWedge=False, declaredBehavior="unconstrained", released=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unconstrained-release"])
        self.assertIn("region:endpoint", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "region"},
            {**valid, "extra": True},
            {**valid, "region": "gamma"},
            {**valid, "declaredBehavior": "measured"},
            {**valid, "smoothLooking": "true"},
            {**valid, "reversesWedge": 1},
            {**valid, "released": None},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
