"""Host checks for P124. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parents[1] / "gates" / "p124_checkpoint_temporal_rendering_safely.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate
resume_index = _MODULE.resume_index
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SOURCE = "0838cbd982edbffeb5432f911a7c53ed2e7197993fda8ab5d62c004ca9a5caab"
RECIPE = "eadc91002f653754d1de6d142ef034fb6acb64da1d9e4aa54a126b0beb5fbbc5"
PARTIAL_0 = "5660c35819fad7a3167bf23b494e3a31b9e5d27948025375326af78b460ca88f"
PARTIAL_2 = "4f6d1d8dd38426fb969e414e99685280fee16cd4e27b619f6b8ccd9e622f45d0"
MODEL_OLD = "bfc843c4088b7abf5bd23377209d0953b8285a46abd010c882c5047705e0ea68"
MODEL_NEW = "55d940316859bc00bcdfc4d09ebae9de5e3743334d75c180590274dcf8c28b5b"
GRAPH = "d9bb277c5d65019190317c8d355a0778b9c05b39432c5375fb7bf5abefdab3a9"
PROFILE = "4ef30bc66bf4841d8892adbb509b904dfff461fb1664fa39ccd3b1737c54dabc"
ALGORITHM = "22b35b01d9cff17c6de38a8c8a5794987755c7bc9067d1c0af54964f6106e035"
OTHER = "42da64428d7b7bd8d5f57fa2c1645c3054795a07f3ec2a60b8702282bd994753"


def checkpoint(frame_index, partial, missing, recipe=RECIPE, source=SOURCE):
    return {
        "frame_index": frame_index,
        "recipe_sha256": recipe,
        "partial_output_sha256": partial,
        "source_sha256": source,
        "missing_frames": missing,
    }


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P124",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p124-model-replaced",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "job_id": "job-stopped",
        "new_job_id": "job-after-model-replacement",
        "calls_resume": False,
        "source_sha256": SOURCE,
        "observed_source_sha256": SOURCE,
        "recipe_sha256": RECIPE,
        "model_sha256": MODEL_OLD,
        "observed_model_sha256": MODEL_NEW,
        "graph_sha256": GRAPH,
        "observed_graph_sha256": GRAPH,
        "profile_sha256": PROFILE,
        "observed_profile_sha256": PROFILE,
        "algorithm_sha256": ALGORITHM,
        "observed_algorithm_sha256": ALGORITHM,
        "checkpoints": [
            checkpoint(0, PARTIAL_0, []),
            checkpoint(2, PARTIAL_2, [1]),
        ],
        "resume_frame": 0,
        "assembled_frames": [],
        "intended_frames": [],
    }
    value.update(overrides)
    return value


def same_model_resume(**overrides):
    base = {
        "evidenceId": "p124-resume",
        "new_job_id": None,
        "calls_resume": True,
        "observed_model_sha256": MODEL_OLD,
        "resume_frame": 3,
        "assembled_frames": [0, 2],
        "intended_frames": [0, 2],
    }
    base.update(overrides)
    return document(**base)


class P124Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-model-replaced"):
        self.assertEqual(tuple(result), KEYS)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("resumeIndex=3", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P124")
        self.assertEqual(_MODULE.TITLE, "Checkpoint temporal rendering safely")
        self.assertEqual(_MODULE.WORKSTREAM, 16)
        self.assertEqual(_MODULE.DEPENDENCIES, ("P123",))
        self.assertEqual(
            _MODULE.GOAL,
            "Resume expensive work without changing the visual result at the restart boundary.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A stopped render resumed after the depth model file has been replaced with a different version.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Resume manifest and uninterrupted-equivalence tests")
        self.assertIn("each output frame exactly once", _MODULE.METHOD)
        self.assertEqual(_MODULE.RESUME_RULE, "resume starts at frame_index+1")
        self.assertEqual(resume_index(0), 1)
        self.assertEqual(resume_index(2), 3)

    def test_resume_index_rejects_invalid_frame_index(self):
        with self.assertRaises(ValueError):
            resume_index(-1)
        with self.assertRaises(ValueError):
            resume_index(True)

    def test_replaced_model_opens_a_new_job_instead_of_resuming_at_zero(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P124")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        self.assertIn("mixed-model output was not silently assembled", result["reasons"])
        self.assertIn("newJobId=job-after-model-replacement", result["preservedResults"])
        self.assertIn("resume starts at frame_index+1", result["reasons"])

    def test_fixture_file_matches_the_new_job_oracle(self):
        payload = json.loads(
            (ROOT / "docs" / "P124_CHECKPOINT_TEMPORAL_RENDERING_SAFELY.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p124-model-replaced", result["preservedResults"])
        self.assertIn("resumeIndex=3", result["preservedResults"])
        handoff = json.loads((ROOT / "docs" / "evidence" / "P124-handoff.json").read_text())
        self.assertEqual(handoff["nextPhase"], "P125")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertEqual(handoff["phase"], "P124")

    def test_same_model_resume_starts_at_frame_index_plus_one(self):
        result = assess(same_model_resume())
        self.assert_contract(result, "p124-resume")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("final assembly contains each output frame exactly once", result["reasons"])

    def test_resume_frame_zero_while_checkpoint_is_later_is_rejected(self):
        result = assess(same_model_resume(resume_frame=0))
        self.assert_contract(result, "p124-resume")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("resume-restarted-at-zero", result["rejectedClaims"])
        self.assertIn("resume-not-at-frame-index-plus-one", result["rejectedClaims"])

    def test_zero_resume_frame_is_not_a_resume_when_the_document_does_not_call_it(self):
        result = assess(document())
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn("resume-restarted-at-zero", result["rejectedClaims"])

    def test_silent_gap_is_rejected_and_a_listed_gap_is_not(self):
        silent = assess(same_model_resume(
            checkpoints=[checkpoint(0, PARTIAL_0, []), checkpoint(2, PARTIAL_2, [])],
        ))
        self.assertEqual(silent["decision"], "rejected")
        self.assertIn("silent-gap", silent["rejectedClaims"])
        self.assertIn("p124-resume", silent["preservedResults"])
        listed = assess(same_model_resume())
        self.assertEqual(listed["decision"], "recorded")

    def test_checkpoint_frame_index_must_increase(self):
        result = assess(same_model_resume(
            checkpoints=[checkpoint(2, PARTIAL_2, [0, 1]), checkpoint(2, PARTIAL_0, [])],
            resume_frame=3,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("checkpoint-frame-not-increasing", result["rejectedClaims"])

    def test_mid_job_recipe_change_without_a_new_job_is_rejected(self):
        result = assess(same_model_resume(
            checkpoints=[checkpoint(0, PARTIAL_0, []), checkpoint(2, PARTIAL_2, [1], recipe=OTHER)],
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("mid-job-recipe-change", result["rejectedClaims"])
        self.assertIn("resume-binds-changed-recipe", result["rejectedClaims"])
        self.assertIn("p124-resume", result["preservedResults"])

    def test_recipe_change_with_a_new_job_does_not_resume(self):
        result = assess(document(
            observed_model_sha256=MODEL_OLD,
            calls_resume=False,
            resume_frame=0,
            checkpoints=[checkpoint(0, PARTIAL_0, []), checkpoint(2, PARTIAL_2, [1], recipe=OTHER)],
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("recipe change created a new job job-after-model-replacement", result["reasons"])

    def test_empty_partial_and_source_mismatch_are_rejected(self):
        empty = assess(same_model_resume(
            checkpoints=[checkpoint(0, "", []), checkpoint(2, PARTIAL_2, [1])],
        ))
        self.assertEqual(empty["decision"], "rejected")
        self.assertIn("empty-partial-output-hash", empty["rejectedClaims"])
        self.assertIn("p124-resume", empty["preservedResults"])
        mismatched = assess(same_model_resume(
            checkpoints=[checkpoint(0, PARTIAL_0, [], source=OTHER), checkpoint(2, PARTIAL_2, [1])],
        ))
        self.assertEqual(mismatched["decision"], "rejected")
        self.assertIn("source-hash-mismatch", mismatched["rejectedClaims"])

    def test_mixed_model_resume_is_rejected(self):
        result = assess(document(calls_resume=True, resume_frame=3, new_job_id=None,
                                 assembled_frames=[0, 2], intended_frames=[0, 2]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("identity-mismatch-model", result["rejectedClaims"])
        self.assertIn("p124-model-replaced", result["preservedResults"])

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(same_model_resume(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p124-resume", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_duplicated_assembly_fails_cadence(self):
        result = assess(same_model_resume(assembled_frames=[0, 2, 2]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicated-overlap-frame", result["rejectedClaims"])
        self.assertIn("cadence-integrity", result["rejectedClaims"])

    def test_evaluate_uses_the_same_resume_index(self):
        payload = same_model_resume()
        payload.pop("schemaVersion")
        payload.pop("phase")
        payload.pop("implementationBaseRevision")
        payload["caseId"] = "P124-evaluate"
        result = evaluate(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P124-evaluate")
        self.assertIn("resumeIndex=3", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            assess(document(checkpoints=[checkpoint(-1, PARTIAL_0, [])]))
        with self.assertRaises(ValueError):
            assess(document(resume_frame=-1))
