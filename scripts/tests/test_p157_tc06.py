"""Tests for TC-P157-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p157_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p157_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload()
    base.update({
        "repeat": "moving subjects",
        "exposures": [
            {"id": "exp-a", "source": True},
            {"id": "exp-b", "source": True},
        ],
        "merged": True,
        "presentedAsSingleUnchangedExposure": False,
        "labelledComputational": True,
        "motionArtifactsMeasured": True,
        "retainedInformationMeasured": True,
        "provenanceIds": ["exp-a", "exp-b"],
        "artifactChecks": {
            "movingSubjects": True,
            "clippedChannels": True,
            "alignmentFailures": True,
            "temporalGhosts": True,
        },
    })
    base.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        base["checksum"] = _GATE.protocol_checksum(base["experiments"])
    return base


class TCP15706(unittest.TestCase):
    def assert_contract(self, result, evidence="p157-instrumented-experiment-design"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P157-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_labelled_merge_with_provenance_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["sourceIds"], ["exp-a", "exp-b"])
        self.assertEqual(_MODULE.CASE["name"], "Computational capture overclaim")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "merge-erased-source-sampling-provenance")

    def test_presenting_the_merge_as_one_unchanged_exposure_is_rejected(self):
        result = evaluate(payload(presentedAsSingleUnchangedExposure=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_dropping_a_source_id_erases_provenance(self):
        result = evaluate(payload(provenanceIds=["exp-a"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_unlabelled_merge_is_rejected(self):
        result = evaluate(payload(labelledComputational=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLABELLED_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_missing_separate_measurements_are_rejected(self):
        result = evaluate(payload(motionArtifactsMeasured=False, retainedInformationMeasured=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MEASUREMENT_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p157-tc06-ghosts"
        result = evaluate(payload(evidenceId=evidence, repeat="temporal ghosts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(exposures=[{"id": "only", "source": True}], merged=True))
