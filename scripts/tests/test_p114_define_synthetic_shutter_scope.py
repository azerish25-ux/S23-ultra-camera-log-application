"""Host checks for P114. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_define_synthetic_shutter_scope",
    Path(__file__).resolve().parents[1] / "gates" / "p114_define_synthetic_shutter_scope.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P114",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p114-scope",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": [
            {"origin": "captured", "weight": 0.5},
            {"origin": "captured", "weight": 0.5},
        ],
    }
    value.update(overrides)
    return value


class P114Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-scope"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P114")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])

    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P114")
        self.assertEqual(
            _MODULE.GOAL,
            "Make deferred motion rendering an explicit optional operation with clear source requirements.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Claim that any video can be converted exactly to any shutter angle.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Synthetic-shutter eligibility policy and limitation tests")
        self.assertEqual(_MODULE.WEIGHT_TOLERANCE, 1e-6)
        self.assertIn("contains_estimated", _MODULE.DISCLOSURE_RULE)
        self.assertIn("hidden hallucination", _MODULE.DISCLOSURE_RULE)

    def test_captured_only_scope_is_recorded_not_qualified(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("not labelled as a longer sensor exposure" in item for item in result["reasons"]))
        self.assertTrue(any("180.0 degrees at 24.0 fps" in item for item in result["reasons"]))

    def test_weight_within_tolerance_is_recorded_and_beyond_is_rejected(self):
        within = assess(document(frames=[{"origin": "captured", "weight": 1.0 + 1e-6}]))
        self.assertEqual(within["decision"], "recorded")
        outside = assess(document(frames=[{"origin": "captured", "weight": 1.0 + 5e-6}]))
        self.assert_contract(outside)
        self.assertEqual(outside["decision"], "rejected")
        self.assertIn("unnormalized-temporal-weights", outside["rejectedClaims"])

    def test_disclosed_estimated_frames_are_recorded(self):
        result = assess(document(
            contains_estimated=True,
            disclosed=True,
            frames=[{"origin": "estimated", "weight": 1.0}],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(any("estimated frames are disclosed" in item for item in result["reasons"]))

    def test_hidden_estimated_frames_are_rejected(self):
        result = assess(document(
            contains_estimated=True,
            disclosed=False,
            frames=[{"origin": "estimated", "weight": 1.0}],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-hallucination", result["rejectedClaims"])

    def test_estimated_origin_requires_contains_estimated(self):
        result = assess(document(
            contains_estimated=False,
            disclosed=True,
            frames=[{"origin": "estimated", "weight": 1.0}],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("estimated-origin-requires-contains-estimated", result["rejectedClaims"])
        self.assertIn(_MODULE.DISCLOSURE_RULE, result["reasons"])

    def test_captured_only_must_not_be_labelled_as_a_longer_sensor_exposure(self):
        result = assess(document(labelled_as_longer_sensor_exposure=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("labelled-as-longer-sensor-exposure", result["rejectedClaims"])

    def test_missing_angle_or_fps_is_rejected(self):
        missing_angle = assess(document(shutter_angle_degrees=None))
        self.assertEqual(missing_angle["decision"], "rejected")
        self.assertIn("missing-shutter-angle", missing_angle["rejectedClaims"])
        self.assertIn("p114-scope", missing_angle["preservedResults"])
        missing_fps = assess(document(fps=None))
        self.assertEqual(missing_fps["decision"], "rejected")
        self.assertIn("missing-fps", missing_fps["rejectedClaims"])

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])

    def test_authored_fixture_is_recorded(self):
        path = Path(__file__).resolve().parents[2] / "docs" / "P114_DEFINE_SYNTHETIC_SHUTTER_SCOPE.json"
        result = assess(json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("p114-scope", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(frames=[{"origin": "invented", "weight": 1.0}]))
        with self.assertRaises(ValueError):
            assess(document(frames=[{"origin": "captured", "weight": float("nan")}]))
        with self.assertRaises(ValueError):
            assess(document(frames=[{"origin": "captured", "weight": True}]))
        with self.assertRaises(ValueError):
            assess(document(shutter_angle_degrees=0))
        with self.assertRaises(ValueError):
            assess(document(fps=-24))
        with self.assertRaises(ValueError):
            assess(document(contains_estimated=1))
