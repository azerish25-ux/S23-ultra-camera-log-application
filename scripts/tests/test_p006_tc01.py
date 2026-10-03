"""TC-P006-01 unsupported certainty decision gate."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gates"))
import p006_tc01 as gate


RESULT_KEYS = ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"]


class UnsupportedCertaintyTests(unittest.TestCase):
    def payload(self, **overrides) -> dict:
        experiment = {
            "irreversible": False,
            "blockedStreamIdentified": False,
            "recoveryProcedureVerified": False,
            "authorizedByEnthusiasmOnly": False,
        }
        experiment.update(overrides.pop("experiment", {}))
        data = {
            "caseId": "TC-P006-01",
            "unsupportedPhysicalClaim": False,
            "claimText": "Application-level capability probe completed on the host.",
            "softwareResult": "Non-destructive capability inventory remains available.",
            "openQuestion": "Which blocked stream, if any, justifies a firmware experiment?",
            "evidenceKind": "host",
            "experiment": experiment,
        }
        data.update(overrides)
        return data

    def assert_shape(self, result: dict, decision: str) -> None:
        self.assertEqual(RESULT_KEYS, list(result))
        self.assertEqual("TC-P006-01", result["caseId"])
        self.assertEqual(decision, result["decision"])
        self.assertNotEqual("established", result["decision"])
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        if decision == "allowed":
            self.assertEqual([], result["reasons"])
        else:
            self.assertTrue(result["reasons"])
            self.assertNotEqual("allowed", result["decision"])

    def test_baseline_defers_experiment_without_blocked_stream_or_recovery(self):
        result = gate.evaluate(self.payload())
        self.assert_shape(result, "deferred")
        text = " ".join(result["reasons"])
        self.assertIn("No blocked stream has been identified.", result["reasons"])
        self.assertIn("Recovery procedure has not been verified.", result["reasons"])
        self.assertIn("Non-destructive capability and application-level investigations remain available.", result["reasons"])
        self.assertNotIn("allowed", text)
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["preservedResults"])
        self.assertEqual([], result["openQuestions"])

    def test_adversarial_operation_rejects_unsupported_physical_claim(self):
        claim = "Physical S23 firmware behavior was measured and accepted."
        software = "Host software experiment enumerated camera routes without flashing."
        question = "What physical stream, if any, is actually blocked?"
        result = gate.evaluate(self.payload(
            unsupportedPhysicalClaim=True,
            claimText=claim,
            softwareResult=software,
            openQuestion=question,
        ))
        self.assert_shape(result, "deferred")
        self.assertEqual([claim], result["rejectedClaims"])
        self.assertEqual([software], result["preservedResults"])
        self.assertEqual([question], result["openQuestions"])
        self.assertIn("Unsupported physical claim is rejected; the narrower software result is preserved.", result["reasons"])
        self.assertNotIn(result["decision"], {"allowed", "established"})

    def test_false_pass_control_rejects_established_untested_physical_behavior(self):
        claim = "Untested physical firmware behavior is established."
        software = "Host software capability probe enumerated camera routes."
        question = "Does a blocked stream exist on the physical S23?"
        result = gate.evaluate(self.payload(
            unsupportedPhysicalClaim=True,
            claimText=claim,
            softwareResult=software,
            openQuestion=question,
            evidenceKind="host",
            experiment={
                "irreversible": False,
                "blockedStreamIdentified": True,
                "recoveryProcedureVerified": True,
                "authorizedByEnthusiasmOnly": False,
            },
        ))
        self.assert_shape(result, "deferred")
        self.assertNotIn(result["decision"], {"allowed", "established"})
        self.assertEqual([claim], result["rejectedClaims"])
        self.assertEqual([software], result["preservedResults"])
        self.assertEqual([question], result["openQuestions"])

    def _repeat(self, evidence_kind: str) -> None:
        baseline = gate.evaluate(self.payload(evidenceKind=evidence_kind))
        self.assert_shape(baseline, "deferred")
        self.assertIn(
            f"Evidence kind {evidence_kind} cannot change a deferred decision into allowed.",
            baseline["reasons"],
        )
        self.assertNotEqual("allowed", baseline["decision"])
        claim = "Untested physical behavior is established by this " + evidence_kind + " result."
        software = "Narrower software result from " + evidence_kind + " evidence."
        question = "What does the physical device do when this probe is unavailable?"
        attacked = gate.evaluate(self.payload(
            evidenceKind=evidence_kind,
            unsupportedPhysicalClaim=True,
            claimText=claim,
            softwareResult=software,
            openQuestion=question,
        ))
        self.assert_shape(attacked, "deferred")
        self.assertNotIn(attacked["decision"], {"allowed", "established"})
        self.assertEqual([claim], attacked["rejectedClaims"])
        self.assertEqual([software], attacked["preservedResults"])
        self.assertEqual([question], attacked["openQuestions"])

    def test_repetition_emulator(self):
        self._repeat("emulator")

    def test_repetition_simulated_fixture(self):
        self._repeat("simulated")

    def test_repetition_unavailable_probe(self):
        self._repeat("unavailable_probe")

    def test_enthusiasm_is_not_authorization_to_flash(self):
        result = gate.evaluate(self.payload(experiment={
            "irreversible": False,
            "blockedStreamIdentified": True,
            "recoveryProcedureVerified": True,
            "authorizedByEnthusiasmOnly": True,
        }))
        self.assert_shape(result, "deferred")
        self.assertIn("User enthusiasm is not authorization to flash.", result["reasons"])

    def test_irreversible_experiment_is_deferred_even_with_recovery(self):
        result = gate.evaluate(self.payload(experiment={
            "irreversible": True,
            "blockedStreamIdentified": True,
            "recoveryProcedureVerified": True,
            "authorizedByEnthusiasmOnly": False,
        }))
        self.assert_shape(result, "deferred")
        self.assertIn("Irreversible firmware experiment is deferred.", result["reasons"])

    def test_qualified_reversible_experiment_without_unsupported_claim_is_allowed(self):
        result = gate.evaluate(self.payload(
            unsupportedPhysicalClaim=False,
            evidenceKind="host",
            experiment={
                "irreversible": False,
                "blockedStreamIdentified": True,
                "recoveryProcedureVerified": True,
                "authorizedByEnthusiasmOnly": False,
            },
        ))
        self.assert_shape(result, "allowed")
        self.assertEqual([], result["reasons"])
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["preservedResults"])
        self.assertEqual([], result["openQuestions"])

    def test_non_dict_payload_and_case_id_mismatch_raise(self):
        with self.assertRaises(ValueError):
            gate.evaluate(["not", "a", "dict"])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(caseId="TC-P006-02"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(evidenceKind="phone"))
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload(experiment={
                "irreversible": 1,
                "blockedStreamIdentified": True,
                "recoveryProcedureVerified": True,
                "authorizedByEnthusiasmOnly": False,
            }))


if __name__ == "__main__":
    unittest.main()
