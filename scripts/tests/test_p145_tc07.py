"""Tests for TC-P145-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p145_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p145_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def features():
    return [
        {"id": "source-mode", "state": "implemented"},
        {"id": "live-depth", "state": "experimental"},
        {"id": "deferred-optics", "state": "roadmap"},
        {"id": "calibration", "state": "experimental"},
    ]


def notes(**overrides):
    base = {
        "implemented": ["source-mode"],
        "experimental": ["live-depth", "calibration"],
        "physicallyQualified": [],
    }
    base.update(overrides)
    return base


def payload(**overrides):
    layers = overrides.pop("layers", None)
    base = {
        "evidenceId": "p145-tc07",
        "repeat": "source-modes",
        "features": features(),
        "notes": notes(),
        "claimsNativeResolution": False,
        "claimsCameraEquivalence": False,
        "scope": "source-modes",
    }
    base.update(_GATE.layer_fields(layers))
    base.update(overrides)
    return base


class TCP14507(unittest.TestCase):
    def assert_contract(self, result, evidence="p145-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P145-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_case_text_matches_the_spec(self):
        self.assertEqual(_MODULE.CASE["name"], "Release claim exceeds evidence")
        self.assertEqual(
            _MODULE.CASE["negative"],
            "Copying the aspirational roadmap into the implemented list must fail.",
        )

    def test_mixed_scopes_are_recorded_without_physical_qualification(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["physicalStatus"], "unavailable")
        self.assertEqual(result["preservedResults"][2]["notes"]["physicallyQualified"], [])
        self.assertNotIn("deferred-optics", result["preservedResults"][2]["notes"]["implemented"])

    def test_roadmap_copied_into_implemented_is_rejected(self):
        result = evaluate(payload(
            notes=notes(implemented=["source-mode", "deferred-optics"]),
            scope="deferred-optics",
            repeat="deferred-optics",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.SCOPE_MISSTATED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_native_resolution_and_camera_equivalence_are_rejected(self):
        result = evaluate(payload(
            claimsNativeResolution=True,
            claimsCameraEquivalence=True,
            scope="live-depth",
            repeat="live-depth",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NATIVE_RESOLUTION, result["rejectedClaims"])
        self.assertIn(_MODULE.CAMERA_EQUIVALENCE, result["rejectedClaims"])

    def test_physical_qualification_without_a_passing_physical_layer_is_rejected(self):
        stated = features()
        stated.append({"id": "calibration-rig", "state": "physically-qualified"})
        result = evaluate(payload(
            features=stated,
            notes=notes(physicallyQualified=["calibration-rig"]),
            scope="calibration-status",
            repeat="calibration-status",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SCOPE_MISSTATED, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["physicalStatus"], "unavailable")

    def test_downgraded_physical_claim_is_recorded_as_experimental(self):
        stated = features()
        stated.append({"id": "calibration-rig", "state": "physically-qualified"})
        result = evaluate(payload(
            features=stated,
            notes=notes(experimental=["live-depth", "calibration", "calibration-rig"]),
            scope="calibration-status",
            repeat="calibration-status",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("calibration-rig", result["preservedResults"][2]["notes"]["experimental"])
        self.assertEqual(result["preservedResults"][2]["notes"]["physicallyQualified"], [])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p145-tc07-live-depth"
        result = evaluate(payload(evidenceId=evidence, scope="live-depth", repeat="live-depth"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(scope="imax"))
        with self.assertRaises(ValueError):
            evaluate(payload(notes=notes(implemented=["not-a-feature"])))
