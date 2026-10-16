"""Host checks for P116. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p116_evaluate_interpolation_without_hidden_hallucination",
    Path(__file__).resolve().parents[1] / "gates" / "p116_evaluate_interpolation_without_hidden_hallucination.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE
HIDDEN = _MODULE.HIDDEN_HALLUCINATION
EXTRAPOLATION = _MODULE.EXTRAPOLATION
VALUE_MISMATCH = _MODULE.VALUE_MISMATCH

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P116",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p116-wedge",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "captured": [
            {"time": 1.0, "value": 4.0, "origin": "captured"},
            {"time": 5.0, "value": 12.0, "origin": "captured"},
        ],
        "estimated": [
            {"time": 2.0, "value": 6.0, "origin": "estimated"},
        ],
        "withheldMidpoint": None,
    }
    value.update(overrides)
    return value


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class P116Tests(unittest.TestCase):
    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P116")
        self.assertEqual(_MODULE.WORKSTREAM, 15)
        self.assertEqual(
            _MODULE.MUTANT,
            "Label synthesized intermediate frames as additional native captured frames.",
        )

    def test_linear_interpolation_is_recorded_and_tagged_estimated(self):
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p116-wedge", result["preservedResults"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])
        self.assertIn("origin=estimated t=2 value=6", result["preservedResults"])
        self.assertIn("interpolationFraction=1/3=0.3333333333333333", blob(result))
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("withheldMidpointResidual=not-provided", result["reasons"])

    def test_published_fixture_reports_residual_without_relabelling(self):
        payload = json.loads(
            (ROOT / "docs" / "P116_EVALUATE_INTERPOLATION_WITHOUT_HIDDEN_HALLUCINATION.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p116-interpolation", result["preservedResults"])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])
        self.assertIn("origin=estimated t=2 value=4", result["preservedResults"])
        self.assertIn("interpolationFraction=2/5=0.4", blob(result))
        self.assertIn("withheldMidpointResidual=1", blob(result))
        self.assertIn("residual does not relabel estimated samples as captured", result["reasons"])
        self.assertFalse(any(item.startswith("origin=captured") for item in result["preservedResults"]))

    def test_large_residual_stays_estimated(self):
        result = assess(document(
            captured=[
                {"time": 0.0, "value": 0.0, "origin": "captured"},
                {"time": 1.0, "value": 0.0, "origin": "captured"},
            ],
            estimated=[{"time": 0.5, "value": 0.0, "origin": "estimated"}],
            withheldMidpoint={"time": 0.5, "value": 10.0},
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("origin=estimated t=0.5 value=0", result["preservedResults"])
        self.assertIn("withheldMidpointResidual=10", blob(result))
        self.assertIn("residual does not relabel estimated samples as captured", result["reasons"])

    def test_hidden_hallucination_is_rejected_and_retagged(self):
        result = assess(document(
            estimated=[{"time": 2.0, "value": 6.0, "origin": "captured"}],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(HIDDEN, result["rejectedClaims"])
        self.assertIn("p116-wedge", result["preservedResults"])
        self.assertIn("origin=estimated t=2 value=6", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p116-wedge", result["preservedResults"])
        self.assertIn("origin=estimated t=2 value=6", result["preservedResults"])

    def test_extrapolation_is_rejected_without_invented_samples(self):
        result = assess(document(
            captured=[
                {"time": 0.0, "value": 0.0, "origin": "captured"},
                {"time": 1.0, "value": 10.0, "origin": "captured"},
            ],
            estimated=[
                {"time": -0.5, "value": 0.0, "origin": "estimated"},
                {"time": 0.5, "value": 5.0, "origin": "estimated"},
                {"time": 1.5, "value": 20.0, "origin": "estimated"},
            ],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(EXTRAPOLATION, result["rejectedClaims"])
        self.assertIn("interpolationFraction=3/5=0.6", blob(result))
        tags = [item for item in result["preservedResults"] if item.startswith("origin=estimated")]
        self.assertEqual(tags, ["origin=estimated t=0.5 value=5"])
        self.assertNotIn("origin=estimated t=-0.5", " ".join(tags))
        self.assertNotIn("origin=estimated t=1.5", " ".join(tags))

    def test_nonlinear_claim_is_rejected_but_tag_uses_the_linear_value(self):
        result = assess(document(
            estimated=[{"time": 2.0, "value": 99.0, "origin": "estimated"}],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(VALUE_MISMATCH, result["rejectedClaims"])
        self.assertIn("origin=estimated t=2 value=6", result["preservedResults"])

    def test_non_finite_sample_raises(self):
        with self.assertRaises(ValueError):
            assess(document(
                captured=[
                    {"time": 0.0, "value": 0.0, "origin": "captured"},
                    {"time": 1.0, "value": float("nan"), "origin": "captured"},
                ],
            ))

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(withheldMidpoint={"time": -5.0, "value": 1.0}))

    def test_handoff_points_at_p117(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P116-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P116")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P117")
