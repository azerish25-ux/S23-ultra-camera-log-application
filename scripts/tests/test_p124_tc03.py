"""Tests for TC-P124-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p124_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SOURCE = "0838cbd982edbffeb5432f911a7c53ed2e7197993fda8ab5d62c004ca9a5caab"
RECIPE = "eadc91002f653754d1de6d142ef034fb6acb64da1d9e4aa54a126b0beb5fbbc5"
PARTIAL = "5660c35819fad7a3167bf23b494e3a31b9e5d27948025375326af78b460ca88f"
MODEL = "bfc843c4088b7abf5bd23377209d0953b8285a46abd010c882c5047705e0ea68"
MODEL_NEW = "55d940316859bc00bcdfc4d09ebae9de5e3743334d75c180590274dcf8c28b5b"
GRAPH = "d9bb277c5d65019190317c8d355a0778b9c05b39432c5375fb7bf5abefdab3a9"
PROFILE = "4ef30bc66bf4841d8892adbb509b904dfff461fb1664fa39ccd3b1737c54dabc"
ALGORITHM = "22b35b01d9cff17c6de38a8c8a5794987755c7bc9067d1c0af54964f6106e035"


def payload(**overrides):
    base = {
        "evidenceId": "p124-evidence",
        "repeat": "Repeat",
        "filename": "chunk-0004.bin",
        "frameNumber": 4,
        "validationMode": "hashes",
        "changedField": "none",
        "callsResume": True,
        "jobId": "job-stopped",
        "newJobId": None,
        "frameIndex": 4,
        "recipeSha256": RECIPE,
        "partialOutputSha256": PARTIAL,
        "sourceSha256": SOURCE,
        "observedSourceSha256": SOURCE,
        "modelSha256": MODEL,
        "observedModelSha256": MODEL,
        "graphSha256": GRAPH,
        "observedGraphSha256": GRAPH,
        "profileSha256": PROFILE,
        "observedProfileSha256": PROFILE,
        "algorithmSha256": ALGORITHM,
        "observedAlgorithmSha256": ALGORITHM,
        "resumeFrame": 5,
    }
    base.update(overrides)
    return base


class TCP12403(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P124-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("resumeIndex=5", " ".join(result["reasons"] + result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_hash_validated_resume_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("filename=chunk-0004.bin", result["preservedResults"])

    def test_filename_and_frame_number_alone_are_rejected(self):
        result = evaluate(payload(validationMode="filename-and-frame"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FILENAME_ONLY, result["rejectedClaims"])
        self.assertIn("p124-evidence", result["preservedResults"])

    def test_each_replaced_identity_is_rejected_without_a_new_job(self):
        replacements = {
            "source": "observedSourceSha256",
            "model": "observedModelSha256",
            "profile": "observedProfileSha256",
            "graph": "observedGraphSha256",
            "algorithm": "observedAlgorithmSha256",
        }
        for field, key in replacements.items():
            result = evaluate(payload(changedField=field, **{key: MODEL_NEW}))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "rejected", field)
            self.assertIn("identity-mismatch-" + field, result["rejectedClaims"])

    def test_model_replacement_can_start_a_distinct_job(self):
        result = evaluate(payload(
            changedField="model",
            observedModelSha256=MODEL_NEW,
            callsResume=False,
            newJobId="job-after-model-replacement",
            resumeFrame=0,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn("filename-and-frame-number-only", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p124-graph"
        result = evaluate(payload(evidenceId=evidence, repeat="graph"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
