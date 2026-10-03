"""Host checks for P092. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p092_separate_metric_and_relative_focus_controls",
    Path(__file__).resolve().parents[1] / "gates" / "p092_separate_metric_and_relative_focus_controls.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P092",
        "implementationBaseRevision": "d4deac8fc82832fd23396a01065c5f0bf9da6670",
        "evidenceId": "p092-wedge",
        "samples": [0.1, 0.4, 0.9],
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
    }
    value.update(overrides)
    return value


class P092Tests(unittest.TestCase):
    def test_monotonic_wedge_is_recorded_not_qualified(self):
        result = assess(document())
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("p092-wedge", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p092-wedge", result["preservedResults"])

    def test_reversed_wedge_is_rejected(self):
        result = assess(document(samples=[0.9, 0.2, 0.3]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("nonmonotonic-or-reversed-response", result["rejectedClaims"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])

    def test_non_finite_sample_raises(self):
        with self.assertRaises(ValueError):
            assess(document(samples=[0.1, float("nan"), 0.4]))
