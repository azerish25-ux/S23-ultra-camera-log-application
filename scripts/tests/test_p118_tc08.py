"""Tests for TC-P118-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p118_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
EFFECTS = ["stabilization", "virtualFocus", "motionIntegration", "filmFinishing"]


def correction(**overrides):
    value = {
        "readoutSecondsPerRow": None,
        "readoutSource": None,
        "cameraVelocityY": 0.0,
        "warpLabel": "none",
        "claimsGlobalShutterRestored": False,
        "rows": [{"rowIndex": 0, "y": 1.0, "velocityY": 0.0, "role": "background"}],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p118-combined",
        "repeat": "scene-cut",
        "effects": list(EFFECTS),
        "independentPass": {name: True for name in EFFECTS},
        "combinedMeasured": True,
        "combinedEdgeCount": 1,
        "maskStable": True,
        "sourceCadence": 24.0,
        "outputCadence": 24.0,
        "cadenceExplained": False,
        "rgbGeometryId": "gate-a",
        "depthGeometryId": "gate-a",
    }
    base.update(correction())
    base.update(overrides)
    return base


class TCP11808(unittest.TestCase):
    def assert_contract(self, result, evidence="p118-combined"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P118-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Combined temporal effects")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Independent success of each effect cannot replace the combined regression.",
        )
        self.assertEqual(_MODULE.REQUIRED_EFFECTS, tuple(EFFECTS))

    def test_combined_regression_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("independent passes are not a substitute for the combined regression", result["reasons"])
        kept = next(item for item in result["preservedResults"] if isinstance(item, dict))
        self.assertEqual(kept["sourceCadence"], 24.0)
        self.assertEqual(kept["outputCadence"], 24.0)
        self.assertEqual(kept["rgbGeometryId"], "gate-a")

    def test_independent_passes_do_not_replace_the_combined_clip(self):
        result = evaluate(
            payload(
                combinedMeasured=False,
                combinedEdgeCount=2,
                maskStable=False,
                outputCadence=30.0,
                depthGeometryId="gate-b",
                repeat="chunk-resume",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.DOUBLED_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.UNSTABLE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.GEOMETRY_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        kept = next(item for item in result["preservedResults"] if isinstance(item, dict))
        self.assertEqual(kept["sourceCadence"], 24.0)
        self.assertEqual(kept["outputCadence"], 30.0)

    def test_explained_cadence_change_can_be_recorded(self):
        result = evaluate(payload(outputCadence=24.0 * 2, cadenceExplained=True, repeat="low-confidence"))
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(_MODULE.CADENCE_TOKEN, result["rejectedClaims"])

    def test_unknown_readout_warp_does_not_shift_rows(self):
        result = evaluate(
            payload(
                **correction(
                    warpLabel="rolling_shutter_correction",
                    rows=[{"rowIndex": 5, "y": 11.0, "velocityY": 2.0, "role": "foreground"}],
                )
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [11.0])
        self.assertEqual(result["preservedResults"][5], [0.0])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(combinedEdgeCount=True))
        with self.assertRaises(ValueError):
            evaluate(payload(effects=["stabilization"]))
