"""Host checks for P120. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parents[1] / "gates" / "p120_validate_combined_motion_and_optics.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
ANGLE = 172.8
FPS = 24.0


def report(**overrides):
    value = {
        "shutter_angle": ANGLE,
        "fps": FPS,
        "exposure_seconds": (ANGLE / 360.0) / FPS,
        "interpolation_fraction": 0.25,
        "estimated_disclosed": True,
        "stabilization_crop_fraction": 0.08,
        "rolling_shutter_readout": "measured",
        "correction_applied": True,
    }
    value.update(overrides)
    return value


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P120",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p120-wedge",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "combinationPassed": True,
        "comparison": "perfect-motion",
        "graphOrder": list(_MODULE.GRAPH_ORDER),
        "report": report(),
    }
    value.update(overrides)
    return value


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class P120Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-wedge"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P120")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P120")
        self.assertEqual(_MODULE.WORKSTREAM, 15)
        self.assertEqual(_MODULE.TITLE, "Validate combined motion and optics")
        self.assertEqual(
            _MODULE.GOAL,
            "Test temporal interactions between shutter simulation, stabilization, depth, and focus.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A handheld focus pull with foreground occlusion, bright bokeh, and synthetic shutter enabled.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The complete clip maintains coherent motion without doubled edges, drifting masks, or discontinuous focus.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Approve each temporal effect independently and skip their combined regression.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Motion-optics integration benchmark and release envelope")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P119",))
        self.assertEqual(_MODULE.EXPOSURE_TOLERANCE, 1e-9)
        self.assertIn("fixed graph order", _MODULE.METHOD)

    def test_consistent_report_is_recorded_not_qualified(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])
        self.assertIn("exposure_seconds=0.02=(shutter_angle/360)/fps", result["reasons"])
        self.assertIn("estimated samples disclosed", result["reasons"])
        self.assertIn("rolling-shutter correction uses a measured readout", result["reasons"])
        self.assertIn("defectOrigin=none", result["preservedResults"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("graphOrder=" + ">".join(_MODULE.GRAPH_ORDER), result["preservedResults"])

    def test_published_fixture_is_recorded(self):
        payload = json.loads(
            (ROOT / "docs" / "P120_VALIDATE_COMBINED_MOTION_AND_OPTICS.json").read_text()
        )
        result = assess(payload)
        self.assert_contract(result, "p120-combined-motion-optics")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("combined-motion-optics-host-fixture", result["preservedResults"])
        self.assertIn("exposure_seconds=0.02", result["preservedResults"])

    def test_exposure_on_the_tolerance_boundary_is_recorded(self):
        expected = _MODULE.expected_exposure(ANGLE, FPS)
        result = assess(document(report=report(exposure_seconds=expected + 1e-9)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(_MODULE.exposures_match(expected + 1e-9, expected))

    def test_exposure_beyond_tolerance_is_rejected(self):
        expected = _MODULE.expected_exposure(ANGLE, FPS)
        result = assess(document(report=report(exposure_seconds=expected + 2e-9)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EXPOSURE_MISMATCH, result["rejectedClaims"])
        self.assertIn("defectOrigin=source_blur", blob(result))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_undisclosed_interpolation_is_rejected(self):
        result = assess(document(report=report(interpolation_fraction=0.25, estimated_disclosed=False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INTERPOLATION_UNDISCLOSED, result["rejectedClaims"])
        self.assertIn("defectOrigin=flow", blob(result))

    def test_zero_interpolation_without_disclosure_is_recorded(self):
        result = assess(document(report=report(
            interpolation_fraction=0.0,
            estimated_disclosed=False,
            rolling_shutter_readout="unknown",
            correction_applied=False,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("no undisclosed interpolation", result["reasons"])
        self.assertIn("rolling-shutter correction was not applied", result["reasons"])

    def test_correction_with_unknown_readout_is_rejected(self):
        result = assess(document(report=report(
            rolling_shutter_readout="unknown",
            correction_applied=True,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNKNOWN_READOUT_CORRECTION, result["rejectedClaims"])
        self.assertIn("defectOrigin=stabilization", blob(result))

    def test_shutter_only_spot_check_claiming_pass_is_rejected(self):
        result = assess(document(
            evidenceId="p120-spot",
            combinationPassed=True,
            report={"shutter_angle": 180.0},
        ))
        self.assert_contract(result, "p120-spot")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SPOT_CHECK, result["rejectedClaims"])
        self.assertIn(_MODULE.MISSING_FIELDS, result["rejectedClaims"])
        self.assertIn("p120-spot", result["preservedResults"])
        self.assertIn("shutter_angle=180", result["preservedResults"])

    def test_missing_field_without_a_pass_claim_is_rejected(self):
        partial = report()
        del partial["exposure_seconds"]
        result = assess(document(combinationPassed=False, report=partial))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_FIELDS, result["rejectedClaims"])
        self.assertNotIn(_MODULE.SPOT_CHECK, result["rejectedClaims"])

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p120-wedge", result["preservedResults"])
        self.assertIn("exposure_seconds=0.02", result["preservedResults"])

    def test_ablation_cannot_claim_the_combination_passed(self):
        result = assess(document(comparison="flow", combinationPassed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ABLATION_TOKEN, result["rejectedClaims"])
        self.assertIn("defectOrigin=flow", blob(result))

    def test_honest_ablation_is_recorded(self):
        result = assess(document(comparison="depth", combinationPassed=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("ablation depth compared; combination not claimed", result["reasons"])

    def test_divergent_graph_order_is_rejected(self):
        result = assess(document(graphOrder=["compositing", "shutter"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.GRAPH_ORDER_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(report=report(rolling_shutter_readout="guessed")))
        with self.assertRaises(ValueError):
            assess(document(report=report(shutter_angle=True)))
        with self.assertRaises(ValueError):
            assess(document(report=report(fps=0)))
        with self.assertRaises(ValueError):
            assess(document(report=report(exposure_seconds=float("nan"))))
        with self.assertRaises(ValueError):
            assess(document(report=report(interpolation_fraction=1.5)))
        with self.assertRaises(ValueError):
            bad = document()
            bad["decision"] = "qualified"
            assess(bad)

    def test_handoff_points_at_p121(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P120-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P120")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P121")
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p120*.py' -v",
        )
        self.assertEqual(handoff["caseIds"], [f"TC-P120-0{index}" for index in range(1, 9)])
