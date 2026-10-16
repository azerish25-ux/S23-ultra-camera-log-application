"""Host checks for P128. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_validate_long_form_development_end_to_end",
    Path(__file__).resolve().parents[1] / "gates" / "p128_validate_long_form_development_end_to_end.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P128",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p128-wedge",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
        "expected_frames": 6,
        "accounted_frames": [0, 1, 2, 3, 4, 5],
        "checkpoint_frames": [0, 2, 5],
        "audio_duration": 0.25,
        "video_duration": 0.25,
        "audio_absent": False,
        "spot_check_only": False,
    }
    value.update(overrides)
    return value


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class P128Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-wedge"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P128")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("synthetic-host-fixture", result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("accountingRule=" + _MODULE.ACCOUNTING_RULE, blob(result))
        self.assertIn("physical-playback-not-certified", result["preservedResults"])
        self.assertIn("this does not certify physical playback", result["reasons"])
        self.assertTrue(result["reasons"])

    def test_constants_match_the_phase_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "3fbad4bc0e0336e273d2723ec873f001e8865323")
        self.assertEqual(_MODULE.PHASE, "P128")
        self.assertEqual(_MODULE.WORKSTREAM, 16)
        self.assertEqual(_MODULE.TITLE, "Validate long-form development end to end")
        self.assertEqual(
            _MODULE.GOAL,
            "Prove that the deferred workflow survives realistic interruptions and large media.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Run complete import, recipe edit, render, cancel, resume, verify, publish, and re-open workflows. "
            "Use rotated, variable-rate, audio-bearing, high-resolution, and corrupt-edge fixtures. "
            "Record limitations separately for software and physical-device execution.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A multi-minute clip with audio, orientation metadata, temporal effects, "
            "and one process termination during rendering.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The final accepted result has correct timing, orientation, audio, provenance, "
            "and no duplicated checkpoint boundary frames.",
        )
        self.assertEqual(_MODULE.MUTANT, "Validate only short silent landscape clips.")
        self.assertEqual(_MODULE.DELIVERABLE, "End-to-end deferred-development acceptance report")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P127",))
        self.assertEqual(_MODULE.AUDIO_VIDEO_LIMIT, 0.04)
        self.assertEqual([case["id"] for case in _MODULE.CASES], [f"TC-P128-0{index}" for index in range(1, 9)])

    def test_complete_account_is_recorded_not_qualified(self):
        result = assess(document())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frameAccount=6/6", result["preservedResults"])
        self.assertIn("checkpointChain=0<2<5", result["preservedResults"])
        self.assertIn("audioVideoDelta=0", result["preservedResults"])
        self.assertIn("complete honest account recorded", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn("a complete frame account does not certify physical playback", result["openQuestions"])

    def test_published_fixture_records_the_six_frame_account(self):
        payload = json.loads(
            (ROOT / "docs" / "P128_VALIDATE_LONG_FORM_DEVELOPMENT_END_TO_END.json").read_text()
        )
        result = assess(payload)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p128-long-form", result["preservedResults"])
        self.assertIn("frameAccount=6/6", result["preservedResults"])
        self.assertIn("checkpointChain=0<2<5", blob(result))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_unordered_complete_indexes_are_recorded(self):
        result = assess(document(accounted_frames=[5, 4, 3, 2, 1, 0], checkpoint_frames=[5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("frameAccount=6/6", result["preservedResults"])
        self.assertIn("checkpointChain=5", result["preservedResults"])

    def test_checkpoint_gap_is_allowed_when_strictly_increasing(self):
        result = assess(document(checkpoint_frames=[0, 5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("checkpointChain=0<5", result["preservedResults"])

    def test_missing_index_is_rejected_and_evidence_remains(self):
        result = assess(document(accounted_frames=[0, 1, 2, 4, 5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_FRAME, result["rejectedClaims"])
        self.assertIn("missing indexes: 3", result["reasons"])
        self.assertIn("frameAccount=5/6", result["preservedResults"])
        self.assertNotIn("complete honest account recorded", result["reasons"])

    def test_duplicate_index_is_rejected(self):
        result = assess(document(accounted_frames=[0, 1, 2, 3, 4, 5, 2]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DUPLICATE_FRAME, result["rejectedClaims"])
        self.assertIn("duplicate indexes: 2", result["reasons"])
        self.assertNotIn(_MODULE.MISSING_FRAME, result["rejectedClaims"])

    def test_missing_and_duplicate_indexes_are_both_rejected(self):
        result = assess(document(accounted_frames=[0, 1, 1, 2, 3, 4]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_FRAME, result["rejectedClaims"])
        self.assertIn(_MODULE.DUPLICATE_FRAME, result["rejectedClaims"])
        self.assertIn("missing indexes: 5", result["reasons"])
        self.assertIn("duplicate indexes: 1", result["reasons"])

    def test_out_of_range_index_is_rejected(self):
        result = assess(document(accounted_frames=[0, 1, 2, 3, 4, 5, 6]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OUT_OF_RANGE_FRAME, result["rejectedClaims"])
        self.assertIn("frameAccount=6/6", result["preservedResults"])
        self.assertNotIn(_MODULE.MISSING_FRAME, result["rejectedClaims"])

    def test_checkpoint_that_is_not_strictly_increasing_breaks(self):
        result = assess(document(checkpoint_frames=[0, 2, 2]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CHECKPOINT_BREAK, result["rejectedClaims"])
        self.assertIn("checkpoint chain is not strictly increasing", result["reasons"])

    def test_decreasing_checkpoint_chain_breaks(self):
        result = assess(document(checkpoint_frames=[5, 0]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CHECKPOINT_BREAK, result["rejectedClaims"])

    def test_last_checkpoint_past_the_final_frame_breaks(self):
        result = assess(document(checkpoint_frames=[0, 6]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CHECKPOINT_BREAK, result["rejectedClaims"])
        self.assertIn("last checkpoint is greater than expected_frames-1", result["reasons"])

    def test_empty_checkpoint_chain_breaks(self):
        result = assess(document(checkpoint_frames=[]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CHECKPOINT_BREAK, result["rejectedClaims"])
        self.assertIn("checkpointChain=empty", result["preservedResults"])

    def test_negative_checkpoint_breaks(self):
        result = assess(document(checkpoint_frames=[-1, 5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CHECKPOINT_BREAK, result["rejectedClaims"])
        self.assertIn("checkpoint index is negative", result["reasons"])

    def test_audio_delta_at_the_limit_is_recorded(self):
        result = assess(document(audio_duration=0.0, video_duration=0.04))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("audioVideoDelta=0.04", result["preservedResults"])
        self.assertIn("audio and video durations agree within 0.04", result["reasons"])

    def test_audio_delta_above_the_limit_is_rejected(self):
        result = assess(document(audio_duration=0.0, video_duration=0.05))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.AUDIO_MISMATCH, result["rejectedClaims"])
        self.assertIn("abs(audio_duration-video_duration)=0.05 > 0.04", result["reasons"])

    def test_audio_absent_allows_a_large_duration_delta(self):
        result = assess(document(audio_duration=1, video_duration=5, audio_absent=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("audioVideoDelta=4", result["preservedResults"])
        self.assertIn("audio duration check skipped because audio_absent is true", result["reasons"])

    def test_spot_check_only_rejects_a_complete_looking_account(self):
        result = assess(document(spot_check_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SPOT_CHECK, result["rejectedClaims"])
        self.assertIn("frameAccount=6/6", result["preservedResults"])
        self.assertIn("checkpointChain=0<2<5", result["preservedResults"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertNotIn("complete honest account recorded", result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_mutant_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, result["rejectedClaims"])
        self.assertIn("p128-wedge", result["preservedResults"])
        self.assertIn("frameAccount=6/6", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(expected_frames=True))
        with self.assertRaises(ValueError):
            assess(document(expected_frames=0))
        with self.assertRaises(ValueError):
            assess(document(audio_duration=float("nan")))
        with self.assertRaises(ValueError):
            assess(document(audio_duration=-0.1))
        with self.assertRaises(ValueError):
            assess(document(audio_absent=0))
        with self.assertRaises(ValueError):
            assess(document(spot_check_only="false"))
        with self.assertRaises(ValueError):
            assess(document(accounted_frames=(0, 1, 2, 3, 4, 5)))
        with self.assertRaises(ValueError):
            assess(document(accounted_frames=[0, 1, 2, 3, 4, True]))
        with self.assertRaises(ValueError):
            assess(document(extra=True))
        account = dict(document())
        del account["checkpoint_frames"]
        with self.assertRaises(ValueError):
            assess(account)

    def test_handoff_points_at_p129(self):
        handoff = json.loads((ROOT / "docs" / "evidence" / "P128-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P128")
        self.assertEqual(handoff["commit"], None)
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nextPhase"], "P129")
        self.assertEqual(handoff["caseIds"], [case["id"] for case in _MODULE.CASES])
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p128*.py' -v",
        )
        for relative in handoff["changedFiles"]:
            self.assertTrue((ROOT / relative).is_file(), relative)
