"""Host checks for the P008 agent protocol. Not a physical S23 qualification.

TC-P008-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p008_protocol import HANDOFF_FIELDS, assess_completion, validate_handoff, validate_protocol


REMOTE = "fffd5c9a63cb732e103052acae29ae0c251585cc"


def load(name: str) -> dict:
    return json.loads((ROOT / "docs" / name).read_text(encoding="utf-8"))


def handoff(**overrides) -> dict:
    value = {
        "phase": "P008",
        "caseIds": ["TC-P008-01"],
        "changedFiles": ["docs/AGENT_PROTOCOL.json"],
        "commit": REMOTE,
        "testsRun": ["python3 -m unittest discover -s scripts/tests -p test_p008_protocol.py -v"],
        "failures": [],
        "unverified": ["TC-P008-01"],
        "nextPhase": "P009",
    }
    value.update(overrides)
    return value


def report(**overrides) -> dict:
    value = {
        "hostGate": "passed",
        "physicalGate": "passed",
        "localBuildSucceeded": True,
        "markAllPhasesComplete": False,
        "remoteCommit": REMOTE,
        "remoteHeadVerified": True,
        "accessAbsent": False,
    }
    value.update(overrides)
    return value


class P008ProtocolTests(unittest.TestCase):
    def test_documents_validate(self) -> None:
        protocol = load("AGENT_PROTOCOL.json")
        schema = load("HANDOFF_SCHEMA.json")
        self.assertIsNone(validate_protocol(protocol))
        self.assertEqual(protocol["schemaVersion"], 1)
        self.assertEqual(protocol["phase"], "P008")
        self.assertEqual(protocol["protocolId"], "s23-agent-protocol")
        self.assertEqual(protocol["implementationBaseRevision"], REMOTE)
        self.assertEqual(protocol["publication"]["branch"], "main")
        self.assertIs(protocol["publication"]["fastForwardOnly"], True)
        self.assertIs(protocol["publication"]["verifyRemoteHead"], True)
        self.assertIs(protocol["publication"]["blockedWithoutAccess"], True)
        self.assertEqual(schema["schemaVersion"], 1)
        self.assertEqual(schema["requiredFields"], list(HANDOFF_FIELDS))

    def test_protocol_rejects_a_step_that_skips_the_operating_order(self) -> None:
        protocol = load("AGENT_PROTOCOL.json")
        broken = copy.deepcopy(protocol)
        broken["steps"] = ["Select the next dependency-ready phase only"]
        with self.assertRaises(ValueError):
            validate_protocol(broken)
        broken = copy.deepcopy(protocol)
        broken["publication"]["fastForwardOnly"] = False
        with self.assertRaises(ValueError):
            validate_protocol(broken)

    def test_handoff_accepts_a_commit_and_a_blocked_null(self) -> None:
        self.assertIsNone(validate_handoff(handoff()))
        self.assertIsNone(validate_handoff(handoff(commit=None, nextPhase="blocked", failures=["not pushed"])))
        self.assertIsNone(validate_handoff(handoff(commit=REMOTE, nextPhase="blocked")))

    def test_handoff_rejects_inexact_or_illegal_fields(self) -> None:
        extra = handoff()
        extra["decision"] = "complete"
        missing = handoff()
        del missing["unverified"]
        empty_tests = handoff(testsRun=[])
        null_commit = handoff(commit=None, nextPhase="P009")
        bad_commit = handoff(commit="abc")
        bad_next = handoff(nextPhase="done")
        unverified_scalar = handoff()
        unverified_scalar["unverified"] = "TC-P008-01"
        cases = (extra, missing, empty_tests, null_commit, bad_commit, bad_next, unverified_scalar)
        for sample in cases:
            with self.subTest(sample=sorted(sample)):
                with self.assertRaises(ValueError):
                    validate_handoff(sample)

    def test_mutant_local_build_does_not_complete_the_programme(self) -> None:
        """Deliberate mutation: mark every phase complete because the build succeeded.

        Host gate passed, physical gate pending, concurrent remote commit preserved.
        """
        mutant = report(
            physicalGate="pending",
            localBuildSucceeded=True,
            markAllPhasesComplete=True,
            remoteCommit=REMOTE,
            remoteHeadVerified=True,
            accessAbsent=False,
        )
        result = assess_completion(mutant)
        self.assertIn(result["decision"], {"software_verified_only", "blocked"})
        self.assertNotEqual(result["decision"], "complete")
        self.assertEqual(result["preservedResults"]["remoteCommit"], REMOTE)
        self.assertIn("local-build-completes-programme", result["rejectedClaims"])
        self.assertTrue(result["openQuestions"])
        self.assertEqual(set(result), {"decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"})

    def test_unverified_remote_head_on_the_mutant_is_not_complete(self) -> None:
        result = assess_completion(report(
            physicalGate="pending",
            localBuildSucceeded=True,
            markAllPhasesComplete=True,
            remoteCommit=REMOTE,
            remoteHeadVerified=False,
        ))
        self.assertIn(result["decision"], {"software_verified_only", "blocked"})
        self.assertNotEqual(result["decision"], "complete")
        self.assertEqual(result["preservedResults"]["remoteCommit"], REMOTE)

    def test_access_absent_blocks_and_preserves_the_remote_commit(self) -> None:
        result = assess_completion(report(accessAbsent=True, remoteHeadVerified=False))
        self.assertEqual(result["decision"], "blocked")
        self.assertTrue(any("no push access" in reason for reason in result["reasons"]))
        self.assertEqual(result["preservedResults"]["remoteCommit"], REMOTE)
        self.assertNotEqual(result["decision"], "complete")

    def test_unverified_remote_head_blocks_a_push_that_would_otherwise_complete(self) -> None:
        result = assess_completion(report(remoteHeadVerified=False, physicalGate="passed", markAllPhasesComplete=False))
        self.assertEqual(result["decision"], "blocked")
        self.assertTrue(any("remote head" in reason for reason in result["reasons"]))
        self.assertEqual(result["preservedResults"]["remoteCommit"], REMOTE)

    def test_verified_gates_can_complete_without_inventing_extra_phases(self) -> None:
        result = assess_completion(report())
        self.assertEqual(result["decision"], "complete")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"]["remoteCommit"], REMOTE)
        invented = assess_completion(report(markAllPhasesComplete=True))
        self.assertNotEqual(invented["decision"], "complete")
        self.assertIn("local-build-completes-programme", invented["rejectedClaims"])

    def test_host_pass_with_pending_physical_gate_is_software_verified_only(self) -> None:
        result = assess_completion(report(
            physicalGate="pending",
            localBuildSucceeded=False,
            markAllPhasesComplete=False,
            remoteCommit=REMOTE,
        ))
        self.assertEqual(result["decision"], "software_verified_only")
        self.assertEqual(result["preservedResults"]["remoteCommit"], REMOTE)
        self.assertEqual(result["preservedResults"]["hostGate"], "passed")

    def test_local_build_without_a_host_pass_stays_blocked(self) -> None:
        result = assess_completion(report(
            hostGate="failed",
            physicalGate="pending",
            localBuildSucceeded=True,
            markAllPhasesComplete=False,
            remoteCommit=None,
        ))
        self.assertEqual(result["decision"], "blocked")
        self.assertNotIn("remoteCommit", result["preservedResults"])

    def test_empty_remote_commit_is_not_preserved(self) -> None:
        result = assess_completion(report(remoteCommit=""))
        self.assertNotIn("remoteCommit", result["preservedResults"])
        self.assertEqual(result["decision"], "complete")
        absent = assess_completion(report(remoteCommit=None, remoteHeadVerified=False))
        self.assertNotIn("remoteCommit", absent["preservedResults"])
        self.assertEqual(absent["decision"], "blocked")


if __name__ == "__main__":
    unittest.main()
