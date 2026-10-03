"""TC-P008-01 unsupported certainty: host verified, physical gate pending."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gates"))
import p008_tc01 as gate


RESULT_KEYS = [
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
]
REMOTE = "c0ffee" * 6 + "aa11"
SOFTWARE = "Host suite verified the execution-protocol checker."
CLAIM = "Physical S23 capture behavior is established."
QUESTION = "What does the physical device gate still need to show?"


class UnsupportedCertaintyTests(unittest.TestCase):
    def payload(self, **overrides) -> dict:
        data = {
            "caseId": "TC-P008-01",
            "hostGate": "passed",
            "physicalGate": "pending",
            "localBuildSucceeded": False,
            "markAllPhasesComplete": False,
            "unsupportedPhysicalClaim": False,
            "claimText": CLAIM,
            "softwareResult": SOFTWARE,
            "openQuestion": QUESTION,
            "evidenceKind": "host",
            "remoteCommit": REMOTE,
        }
        data.update(overrides)
        return data

    def assert_shape(self, result: dict, decision: str) -> None:
        self.assertEqual(RESULT_KEYS, list(result))
        self.assertEqual("TC-P008-01", result["caseId"])
        self.assertEqual(decision, result["decision"])
        self.assertNotIn(result["decision"], {"established", "allowed"})
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertTrue(result["reasons"])
        self.assertEqual([SOFTWARE, REMOTE], result["preservedResults"])
        self.assertIn(REMOTE, result["preservedResults"])
        self.assertIn(SOFTWARE, result["preservedResults"])

    def test_baseline_host_passed_physical_pending_is_software_verified_only(self):
        result = gate.evaluate(self.payload())
        self.assert_shape(result, "software_verified_only")
        self.assertNotEqual("complete", result["decision"])
        self.assertEqual(["physical device gate pending"], result["openQuestions"])
        self.assertEqual([], result["rejectedClaims"])
        self.assertIn("software-verified only", " ".join(result["reasons"]))
        self.assertIn("Physical device gate is pending.", result["reasons"])

    def test_mutation_local_build_and_mark_all_do_not_complete(self):
        for local_build, mark_all in ((True, False), (False, True), (True, True)):
            result = gate.evaluate(self.payload(
                localBuildSucceeded=local_build,
                markAllPhasesComplete=mark_all,
            ))
            self.assert_shape(result, "software_verified_only")
            self.assertNotEqual("complete", result["decision"])
            self.assertIn(REMOTE, result["preservedResults"])
            if local_build:
                self.assertIn("Local build success must not mark phases complete.", result["reasons"])
            if mark_all:
                self.assertIn(
                    "Marking every phase complete because the local build succeeded is rejected.",
                    result["reasons"],
                )

    def test_host_failed_is_blocked_when_physical_is_not_passed(self):
        for physical in ("pending", "failed"):
            result = gate.evaluate(self.payload(hostGate="failed", physicalGate=physical))
            self.assert_shape(result, "blocked")
            self.assertNotEqual("complete", result["decision"])
            if physical == "pending":
                self.assertIn("physical device gate pending", result["openQuestions"])
            else:
                self.assertNotIn("physical device gate pending", result["openQuestions"])
                self.assertEqual([], result["openQuestions"])

    def test_host_passed_physical_failed_stays_software_verified_only(self):
        result = gate.evaluate(self.payload(physicalGate="failed"))
        self.assert_shape(result, "software_verified_only")
        self.assertEqual([], result["openQuestions"])
        self.assertIn("Physical device gate failed.", result["reasons"])
        self.assertNotEqual("complete", result["decision"])

    def test_unsupported_physical_claim_is_rejected_and_not_established(self):
        result = gate.evaluate(self.payload(
            unsupportedPhysicalClaim=True,
            claimText=CLAIM,
            softwareResult=SOFTWARE,
            openQuestion=QUESTION,
        ))
        self.assert_shape(result, "software_verified_only")
        self.assertEqual([CLAIM], result["rejectedClaims"])
        self.assertEqual(["physical device gate pending", QUESTION], result["openQuestions"])
        self.assertNotIn(result["decision"], {"established", "complete"})
        self.assertIn(
            "Unsupported physical claim is rejected; the narrower software result is preserved.",
            result["reasons"],
        )

    def test_unsupported_claim_cannot_complete_even_if_gates_passed(self):
        result = gate.evaluate(self.payload(
            hostGate="passed",
            physicalGate="passed",
            unsupportedPhysicalClaim=True,
            markAllPhasesComplete=False,
            localBuildSucceeded=False,
            evidenceKind="host",
        ))
        self.assert_shape(result, "software_verified_only")
        self.assertEqual([CLAIM], result["rejectedClaims"])
        self.assertEqual([QUESTION], result["openQuestions"])
        self.assertNotIn(result["decision"], {"established", "complete"})

    def test_weak_evidence_cannot_set_complete(self):
        for kind in ("emulator", "simulated", "unavailable_probe"):
            result = gate.evaluate(self.payload(
                physicalGate="passed",
                hostGate="passed",
                evidenceKind=kind,
                localBuildSucceeded=False,
                markAllPhasesComplete=False,
                unsupportedPhysicalClaim=False,
            ))
            self.assert_shape(result, "software_verified_only")
            self.assertNotEqual("complete", result["decision"])
            self.assertIn(
                f"Evidence kind {kind} cannot set decision complete.",
                result["reasons"],
            )
            self.assertEqual([], result["rejectedClaims"])

    def test_complete_only_when_both_gates_pass_without_mutation(self):
        result = gate.evaluate(self.payload(
            hostGate="passed",
            physicalGate="passed",
            localBuildSucceeded=False,
            markAllPhasesComplete=False,
            unsupportedPhysicalClaim=False,
            evidenceKind="host",
        ))
        self.assert_shape(result, "complete")
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])
        self.assertNotIn("physical device gate pending", result["openQuestions"])

    def test_local_build_success_does_not_by_itself_yield_or_block_completion(self):
        pending = gate.evaluate(self.payload(
            physicalGate="pending",
            localBuildSucceeded=True,
            markAllPhasesComplete=False,
        ))
        self.assert_shape(pending, "software_verified_only")
        self.assertNotEqual("complete", pending["decision"])

        done = gate.evaluate(self.payload(
            hostGate="passed",
            physicalGate="passed",
            localBuildSucceeded=True,
            markAllPhasesComplete=False,
            unsupportedPhysicalClaim=False,
            evidenceKind="host",
        ))
        self.assert_shape(done, "complete")
        self.assertIn("Local build success must not mark phases complete.", done["reasons"])

    def test_mark_all_blocks_complete_even_when_gates_passed(self):
        result = gate.evaluate(self.payload(
            hostGate="passed",
            physicalGate="passed",
            localBuildSucceeded=True,
            markAllPhasesComplete=True,
            unsupportedPhysicalClaim=False,
            evidenceKind="host",
        ))
        self.assert_shape(result, "software_verified_only")
        self.assertNotEqual("complete", result["decision"])
        self.assertNotEqual("established", result["decision"])

    def test_remote_commit_survives_every_gate_combination(self):
        for host in ("passed", "failed"):
            for physical in ("pending", "passed", "failed"):
                for kind in ("host", "emulator", "simulated", "unavailable_probe"):
                    result = gate.evaluate(self.payload(
                        hostGate=host,
                        physicalGate=physical,
                        evidenceKind=kind,
                        localBuildSucceeded=True,
                        markAllPhasesComplete=True,
                        unsupportedPhysicalClaim=True,
                    ))
                    self.assertIn(REMOTE, result["preservedResults"])
                    self.assertIn(SOFTWARE, result["preservedResults"])
                    self.assertNotEqual("complete", result["decision"])
                    self.assertNotEqual("established", result["decision"])
                    if physical == "pending":
                        self.assertIn("physical device gate pending", result["openQuestions"])
                    if physical != "passed":
                        expected = "software_verified_only" if host == "passed" else "blocked"
                        self.assertEqual(expected, result["decision"])

    def test_bad_payload_and_case_id_raise(self):
        for payload in (None, [], "TC-P008-01", 3):
            with self.assertRaises(ValueError):
                gate.evaluate(payload)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(caseId="TC-P008-02"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(caseId=""))
        missing = self.payload()
        del missing["remoteCommit"]
        with self.assertRaises(ValueError):
            gate.evaluate(missing)
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(hostGate="pending"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(physicalGate="skipped"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(evidenceKind="phone"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(localBuildSucceeded=1))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(markAllPhasesComplete="true"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(unsupportedPhysicalClaim=0))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(remoteCommit="   "))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(softwareResult=""))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(claimText=None))


if __name__ == "__main__":
    unittest.main()
