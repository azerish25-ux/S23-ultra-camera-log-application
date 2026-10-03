"""TC-P008-03 missing provenance, repeated across the four fixture kinds."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gates.p008_tc03 import evaluate

KINDS = ("model", "stock_profile", "movie_reference", "generated_screenshot")
KEYS = {"caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"}
FORBIDDEN = {"reproducible", "complete", "allowed"}


def fixture(fixture_id: str, kind: str, provenance, visual_result: str = "attractive") -> dict:
    return {"id": fixture_id, "kind": kind, "provenance": provenance, "visualResult": visual_result}


def payload(fixtures: list[dict], claims: list[str], remote: str = "abc123remote", gate: str | None = "pending") -> dict:
    body = {"fixtures": fixtures, "claimFixtureIds": claims, "remoteCommit": remote}
    if gate is not None:
        body["physicalGate"] = gate
    return body


class MissingProvenanceGate(unittest.TestCase):
    def assert_contract(self, result: dict) -> None:
        self.assertEqual(set(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P008-03")
        self.assertIsInstance(result["reasons"], list)
        self.assertIsInstance(result["rejectedClaims"], list)
        self.assertIsInstance(result["preservedResults"], list)
        self.assertIsInstance(result["openQuestions"], list)
        self.assertNotIn(result["decision"], FORBIDDEN)
        if result["decision"] != "allowed":
            self.assertTrue(result["reasons"])
            self.assertTrue(all(isinstance(reason, str) and reason for reason in result["reasons"]))

    def test_each_kind_without_provenance_is_excluded(self) -> None:
        for kind in KINDS:
            for visual in ("reproducible", "complete", "attractive"):
                with self.subTest(kind=kind, visual=visual):
                    claimed = f"{kind}-claimed"
                    kept = f"{kind}-kept"
                    remote = f"remote-{kind}"
                    result = evaluate(payload([
                        fixture(claimed, kind, None, visual),
                        fixture(kept, kind, {"origin": "lab", "owner": "s23"}, "kept-visual"),
                    ], [claimed, kept], remote))
                    self.assert_contract(result)
                    self.assertEqual(result["decision"], "excluded")
                    self.assertIn(claimed, result["rejectedClaims"])
                    self.assertNotIn(kept, result["rejectedClaims"])
                    self.assertIn(remote, result["preservedResults"])
                    self.assertIn(kept, result["preservedResults"])
                    self.assertNotIn(claimed, result["preservedResults"])
                    self.assertEqual(result["openQuestions"], ["physical device gate pending"])
                    self.assertNotIn(result["decision"], {"reproducible", "complete"})

    def test_absent_provenance_key_is_missing(self) -> None:
        body = payload([
            {"id": "shot", "kind": "generated_screenshot", "visualResult": "complete"},
            fixture("model-ok", "model", "owned-record"),
        ], ["shot"])
        result = evaluate(body)
        self.assertEqual(result["decision"], "excluded")
        self.assertEqual(result["rejectedClaims"], ["shot"])
        self.assertEqual(result["preservedResults"], ["abc123remote", "model-ok"])

    def test_pending_gate_with_provenance_is_host_verified_not_complete(self) -> None:
        fixtures = [fixture(kind, kind, {"owner": kind}, "complete") for kind in KINDS]
        result = evaluate(payload(fixtures, [item["id"] for item in fixtures], "remote-head"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "host-verified")
        self.assertNotEqual(result["decision"], "complete")
        self.assertNotEqual(result["decision"], "accepted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], ["physical device gate pending"])
        self.assertEqual(result["preservedResults"], ["remote-head", *KINDS])

    def test_default_physical_gate_is_pending(self) -> None:
        result = evaluate(payload([fixture("model-a", "model", {"owner": "lab"})], ["model-a"], gate=None))
        self.assertEqual(result["decision"], "host-verified")
        self.assertEqual(result["openQuestions"], ["physical device gate pending"])
        self.assertIn("abc123remote", result["preservedResults"])

    def test_all_claimed_kinds_with_provenance_and_passed_gate_are_accepted(self) -> None:
        fixtures = [fixture(kind, kind, {"origin": "set", "owner": "archive"}) for kind in KINDS]
        result = evaluate(payload(fixtures, list(KINDS), "commit-kept", "passed"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "accepted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(result["preservedResults"], ["commit-kept", *KINDS])
        self.assertNotEqual(result["decision"], "complete")

    def test_passed_gate_still_excludes_missing_provenance(self) -> None:
        result = evaluate(payload([
            fixture("movie", "movie_reference", None, "reproducible"),
            fixture("stock", "stock_profile", {"owner": "vendor"}),
        ], ["movie", "stock"], "remote-ok", "passed"))
        self.assertEqual(result["decision"], "excluded")
        self.assertEqual(result["rejectedClaims"], ["movie"])
        self.assertEqual(result["preservedResults"], ["remote-ok", "stock"])
        self.assertEqual(result["openQuestions"], [])

    def test_unclaimed_missing_provenance_does_not_exclude(self) -> None:
        result = evaluate(payload([
            fixture("used", "model", {"owner": "lab"}, "complete"),
            fixture("unused", "generated_screenshot", None, "reproducible"),
        ], ["used"], "remote-keep", "passed"))
        self.assertEqual(result["decision"], "accepted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], ["remote-keep", "used"])
        self.assertNotIn("unused", result["preservedResults"])

    def test_build_success_does_not_complete_a_pending_gate(self) -> None:
        body = payload([fixture("model-a", "model", {"owner": "lab"}, "complete")], ["model-a"])
        body["localBuildSucceeded"] = True
        result = evaluate(body)
        self.assertEqual(result["decision"], "host-verified")
        self.assertNotIn(result["decision"], {"complete", "allowed", "reproducible"})
        self.assertIn("abc123remote", result["preservedResults"])

    def test_empty_provenance_values_are_missing(self) -> None:
        for provenance in ("", "   ", {}, []):
            with self.subTest(provenance=provenance):
                result = evaluate(payload([
                    fixture("blank", "stock_profile", provenance, "complete"),
                ], ["blank"], "remote-blank", "passed"))
                self.assertEqual(result["decision"], "excluded")
                self.assertEqual(result["rejectedClaims"], ["blank"])
                self.assertEqual(result["preservedResults"], ["remote-blank"])

    def test_multiple_claimed_gaps_preserve_claim_order(self) -> None:
        result = evaluate(payload([
            fixture("m", "model", None),
            fixture("s", "stock_profile", {"owner": "lib"}),
            fixture("r", "movie_reference", None),
            fixture("g", "generated_screenshot", {"owner": "render"}),
        ], ["r", "m", "s"], "sha", "pending"))
        self.assertEqual(result["rejectedClaims"], ["r", "m"])
        self.assertEqual(result["preservedResults"], ["sha", "s", "g"])
        self.assertEqual(result["decision"], "excluded")

    def test_invalid_payloads_raise(self) -> None:
        valid = payload([fixture("m", "model", {"owner": "lab"})], ["m"])
        with self.assertRaises(ValueError):
            evaluate([])  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            evaluate({"claimFixtureIds": [], "remoteCommit": "x"})
        with self.assertRaises(ValueError):
            evaluate({"fixtures": [], "remoteCommit": "x"})
        with self.assertRaises(ValueError):
            evaluate({"fixtures": [], "claimFixtureIds": [], "remoteCommit": "  "})
        bad_kind = payload([fixture("m", "model", None)], ["m"])
        bad_kind["fixtures"][0]["kind"] = "photo"
        with self.assertRaises(ValueError):
            evaluate(bad_kind)
        unknown = payload([fixture("m", "model", {"owner": "lab"})], ["missing"])
        with self.assertRaises(ValueError):
            evaluate(unknown)
        duplicate = payload([
            fixture("m", "model", {"owner": "lab"}),
            fixture("m", "stock_profile", {"owner": "lab"}),
        ], ["m"])
        with self.assertRaises(ValueError):
            evaluate(duplicate)
        bad_gate = payload([fixture("m", "model", {"owner": "lab"})], ["m"], gate="failed")
        with self.assertRaises(ValueError):
            evaluate(bad_gate)
        claims = payload([fixture("m", "model", {"owner": "lab"})], ["m", "m"])
        with self.assertRaises(ValueError):
            evaluate(claims)
        self.assertEqual(evaluate(valid)["decision"], "host-verified")

    def test_payload_is_not_mutated(self) -> None:
        body = payload([fixture("m", "model", None, "reproducible")], ["m"], "remote")
        snapshot = repr(body)
        evaluate(body)
        self.assertEqual(repr(body), snapshot)


if __name__ == "__main__":
    unittest.main()
