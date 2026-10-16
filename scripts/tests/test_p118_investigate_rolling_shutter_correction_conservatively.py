"""Host checks for P118. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_investigate_rolling_shutter_correction_conservatively",
    Path(__file__).resolve().parents[1] / "gates" / "p118_investigate_rolling_shutter_correction_conservatively.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
ROWS = [
    {"rowIndex": 0, "y": 10.0, "velocityY": 4.0, "role": "background"},
    {"rowIndex": 2, "y": 20.0, "velocityY": 4.0, "role": "background"},
    {"rowIndex": 1, "y": 8.0, "velocityY": -2.0, "role": "foreground"},
]


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P118",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p118-pan-lines",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "readoutSecondsPerRow": 0.5,
        "readoutSource": "measured",
        "cameraVelocityY": 4.0,
        "warpLabel": "rolling_shutter_correction",
        "claimsGlobalShutterRestored": False,
        "rows": ROWS,
    }
    value.update(overrides)
    return value


class P118Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P118")
        self.assertEqual(_MODULE.WORKSTREAM, 15)
        self.assertEqual(_MODULE.TITLE, "Investigate rolling-shutter correction conservatively")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P117",))
        self.assertEqual(
            _MODULE.GOAL,
            "Explore geometric correction only with enough timing and motion evidence.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A fast pan across vertical lines with an independently moving foreground person.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The system reports residual error and does not warp the person using an unjustified "
            "global camera-motion assumption.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Apply one global shear correction to every object without validating motion.",
        )
        self.assertEqual(
            _MODULE.DELIVERABLE,
            "Rolling-shutter research report and bounded experimental mode",
        )
        self.assertIn("sensor-timing-based correction", _MODULE.METHOD)
        self.assertIn("restrict correction when foreground motion violates a global model", _MODULE.METHOD)

    def test_row_time_and_corrected_coordinate(self):
        self.assertEqual(_MODULE.row_time_offset(0, 0.5), 0.0)
        self.assertEqual(_MODULE.row_time_offset(2, 0.5), 1.0)
        self.assertEqual(_MODULE.row_time_offset(1, 0.5), 0.5)
        self.assertEqual(_MODULE.corrected_row_coordinate(20.0, 4.0, 1.0), 24.0)
        self.assertEqual(_MODULE.corrected_row_coordinate(8.0, -2.0, 0.5), 7.0)
        self.assertEqual(_MODULE.max_row_shift_pixels([0.0, 4.0, -1.0]), 4.0)
        self.assertEqual(_MODULE.max_row_shift_pixels([]), 0.0)
        self.assertTrue(_MODULE.correction_permitted(0.5, "measured"))
        self.assertFalse(_MODULE.correction_permitted(0.0, "measured"))
        self.assertFalse(_MODULE.correction_permitted(-1.0, "measured"))
        self.assertFalse(_MODULE.correction_permitted(0.5, "documented"))
        self.assertFalse(_MODULE.correction_permitted(0.5, "unknown"))
        self.assertFalse(_MODULE.correction_permitted(None, "measured"))
        self.assertFalse(_MODULE.correction_permitted(float("nan"), "measured"))
        self.assertFalse(_MODULE.correction_permitted(True, "measured"))

    def test_measured_correction_is_recorded_and_reports_max_shift(self):
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P118")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p118-pan-lines", result["preservedResults"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])
        self.assertIn("correction_applied true", result["preservedResults"])
        self.assertIn("maxRowShiftPixels=4", result["preservedResults"])
        self.assertIn("residualErrorPixels=3", result["preservedResults"])
        self.assertEqual(result["preservedResults"][5], [10.0, 20.0, 8.0])
        self.assertEqual(result["preservedResults"][6], [10.0, 24.0, 7.0])
        self.assertEqual(result["preservedResults"][7], [0.0, 4.0, -1.0])
        self.assertEqual(result["preservedResults"][8], [0.0, 1.0, 0.5])
        self.assertNotEqual(result["preservedResults"][6][2], 10.0)
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("yPrime=y+velocityY*rowTime", result["reasons"])

    def test_published_fixture_matches_the_numeric_example(self):
        payload = json.loads(
            (ROOT / "docs" / "P118_INVESTIGATE_ROLLING_SHUTTER_CORRECTION_CONSERVATIVELY.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][6], [10.0, 24.0, 7.0])
        self.assertIn("maxRowShiftPixels=4", result["preservedResults"])
        handoff = json.loads((ROOT / "docs" / "evidence" / "P118-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P118")
        self.assertEqual(handoff["nextPhase"], "P119")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertIn("physical S23 capture", handoff["unverified"])

    def test_unknown_labelled_warp_is_rejected_without_shifting_rows(self):
        rows = [{"rowIndex": 2, "y": 20.0, "velocityY": 4.0, "role": "background"}]
        result = assess(
            document(
                readoutSecondsPerRow=None,
                readoutSource=None,
                warpLabel="rolling_shutter_correction",
                rows=rows,
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNKNOWN_READOUT_WARP, result["rejectedClaims"])
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertIn("maxRowShiftPixels=0", result["preservedResults"])
        self.assertEqual(result["preservedResults"][5], [20.0])
        self.assertEqual(result["preservedResults"][6], [20.0])
        self.assertEqual(result["preservedResults"][7], [0.0])
        self.assertEqual(result["preservedResults"][8], [None])
        self.assertNotEqual(result["preservedResults"][6], [24.0])
        self.assertIn("p118-pan-lines", result["preservedResults"])

    def test_honest_missing_readout_is_recorded_with_correction_applied_false(self):
        result = assess(
            document(
                readoutSecondsPerRow=None,
                readoutSource="unknown",
                warpLabel="none",
                rows=[{"rowIndex": 2, "y": 20.0, "velocityY": 4.0, "role": "background"}],
            )
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("correction_applied false", result["reasons"])
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][6], [20.0])
        self.assertEqual(result["preservedResults"][7], [0.0])
        self.assertIn("rows were not shifted", result["reasons"])

    def test_documented_readout_does_not_permit_a_labelled_warp(self):
        result = assess(document(readoutSource="documented"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNKNOWN_READOUT_WARP, result["rejectedClaims"])
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][5], result["preservedResults"][6])
        self.assertEqual(result["preservedResults"][7], [0.0, 0.0, 0.0])

    def test_zero_readout_does_not_shift_rows(self):
        result = assess(document(readoutSecondsPerRow=0.0))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][7], [0.0, 0.0, 0.0])

    def test_global_shutter_claim_is_rejected(self):
        result = assess(document(claimsGlobalShutterRestored=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GLOBAL_SHUTTER_CLAIM, result["rejectedClaims"])
        self.assertIn("p118-pan-lines", result["preservedResults"])
        self.assertEqual(result["preservedResults"][6], [10.0, 24.0, 7.0])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_global_camera_shear_does_not_warp_the_person(self):
        result = assess(document(warpLabel="global_camera_shear"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNJUSTIFIED_GLOBAL, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][5], [10.0, 20.0, 8.0])
        self.assertEqual(result["preservedResults"][6], [10.0, 24.0, 8.0])
        self.assertEqual(result["preservedResults"][7], [0.0, 4.0, 0.0])
        self.assertIn("residualErrorPixels=3", result["preservedResults"])
        self.assertIn("maxRowShiftPixels=4", result["preservedResults"])
        self.assertNotEqual(result["preservedResults"][6][2], 10.0)

    def test_rigid_global_shear_matches_the_row_formula(self):
        rows = [
            {"rowIndex": 0, "y": 10.0, "velocityY": 4.0, "role": "background"},
            {"rowIndex": 2, "y": 20.0, "velocityY": 4.0, "role": "foreground"},
        ]
        result = assess(document(warpLabel="global_camera_shear", rows=rows))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][6], [10.0, 24.0])
        self.assertIn("residualErrorPixels=0", result["preservedResults"])
        self.assertIn("correction_applied true", result["preservedResults"])

    def test_optical_flow_does_not_apply_sensor_timing_shifts(self):
        result = assess(document(warpLabel="optical_flow"))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][6], [10.0, 20.0, 8.0])
        self.assertEqual(result["preservedResults"][7], [0.0, 0.0, 0.0])
        self.assertIn("optical-flow approximation is separate from sensor-timing correction", result["reasons"])

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p118-pan-lines", result["preservedResults"])
        self.assertEqual(result["preservedResults"][6], [10.0, 24.0, 7.0])

    def test_background_that_breaks_the_global_model_is_not_sheared(self):
        rows = [
            {"rowIndex": 2, "y": 20.0, "velocityY": 9.0, "role": "background"},
            {"rowIndex": 1, "y": 8.0, "velocityY": -2.0, "role": "foreground"},
        ]
        result = assess(document(warpLabel="global_camera_shear", rows=rows))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.BACKGROUND_VIOLATION, result["rejectedClaims"])
        self.assertIn(_MODULE.UNJUSTIFIED_GLOBAL, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][6], [20.0, 8.0])
        self.assertEqual(result["preservedResults"][7], [0.0, 0.0])

    def test_evaluate_uses_the_same_row_shift(self):
        payload = document()
        payload.pop("schemaVersion")
        payload.pop("phase")
        payload.pop("implementationBaseRevision")
        payload["caseId"] = "P118"
        payload["evidenceId"] = "p118-evaluate"
        result = evaluate(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P118")
        self.assertEqual(result["preservedResults"][6], [10.0, 24.0, 7.0])
        self.assertIn("p118-evaluate", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(readoutSecondsPerRow=float("nan")))
        with self.assertRaises(ValueError):
            assess(document(readoutSecondsPerRow=-0.1))
        with self.assertRaises(ValueError):
            assess(document(rows=[{"rowIndex": 1, "y": True, "velocityY": 1.0, "role": "background"}]))
        with self.assertRaises(ValueError):
            assess(document(rows=[]))
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            _MODULE.row_time_offset(-1, 0.5)
        self.assertTrue(math.isfinite(_MODULE.corrected_row_coordinate(1.0, 2.0, 3.0)))
