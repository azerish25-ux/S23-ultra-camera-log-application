"""TC-P006-03 missing provenance: baseline, adversarial, false-pass, repetition."""

import sys
import unittest

sys.path.insert(0, "/workspace/s23/scripts/gates")

import p006_tc03

CASE_ID = "TC-P006-03"
KINDS = ("model", "stock_profile", "movie_reference", "generated_screenshot", "other")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _provenance(**overrides):
    record = {
        "origin": "studio-archive",
        "owner": "s23-research",
        "acquiredAt": "2026-01-15T00:00:00Z",
        "permittedUse": "private-comparison",
    }
    record.update(overrides)
    return record


_UNSET = object()


def _fixture(fixture_id, kind="model", provenance=_UNSET, visual_result="frame"):
    if provenance is _UNSET:
        provenance = _provenance()
    return {
        "id": fixture_id,
        "kind": kind,
        "provenance": provenance,
        "visualResult": visual_result,
    }


def _payload(fixtures, claim_ids, case_id=CASE_ID):
    return {
        "caseId": case_id,
        "fixtures": fixtures,
        "claimFixtureIds": claim_ids,
    }


class P006Tc03Tests(unittest.TestCase):
    def test_payload_must_be_dict(self):
        for payload in (None, [], "TC-P006-03", 3):
            with self.assertRaises(ValueError):
                p006_tc03.evaluate(payload)

    def test_case_id_mismatch(self):
        payload = _payload([], [])
        payload["caseId"] = "TC-P006-04"
        with self.assertRaises(ValueError):
            p006_tc03.evaluate(payload)
        del payload["caseId"]
        with self.assertRaises(ValueError):
            p006_tc03.evaluate(payload)

    def test_baseline_firmware_experiment_remains_deferred(self):
        result = p006_tc03.evaluate(_payload([], []))
        self.assertEqual(CASE_ID, result["caseId"])
        self.assertEqual("accepted", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertNotIn(result["decision"], ("reproducible", "allowed"))
        text = " ".join(result["reasons"]).lower()
        self.assertIn("deferred", text)
        self.assertIn("blocked stream", text)
        self.assertIn("recovery", text)
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["preservedResults"])
        self.assertEqual([], result["openQuestions"])
        self._assert_schema(result)

    def test_baseline_complete_provenance_does_not_allow_firmware(self):
        fixtures = [
            _fixture("software-probe", kind="model", visual_result="clean software result"),
        ]
        result = p006_tc03.evaluate(_payload(fixtures, ["software-probe"]))
        self.assertEqual("accepted", result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        self.assertEqual(["software-probe"], result["preservedResults"])
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])
        self.assertIn("deferred", " ".join(result["reasons"]).lower())
        self._assert_schema(result)

    def test_adversarial_missing_provenance_excludes_and_preserves_complete(self):
        fixtures = [
            _fixture("kept", kind="model", visual_result="ordinary"),
            _fixture(
                "stripped",
                kind="movie_reference",
                provenance=None,
                visual_result="attractive cinematic still",
            ),
        ]
        result = p006_tc03.evaluate(_payload(fixtures, ["kept", "stripped"]))
        self.assertEqual("excluded", result["decision"])
        self.assertEqual(["stripped"], result["rejectedClaims"])
        self.assertEqual(["kept"], result["preservedResults"])
        self.assertEqual([], result["openQuestions"])
        self.assertNotIn(result["decision"], ("reproducible", "allowed"))
        self._assert_schema(result)

    def test_false_pass_visual_result_alone_is_not_reproducible_or_allowed(self):
        for visual in ("reproducible", "allowed", "passing gate", "convincing identity-free frame"):
            fixtures = [
                _fixture(
                    "pretty",
                    kind="generated_screenshot",
                    provenance=None,
                    visual_result=visual,
                )
            ]
            result = p006_tc03.evaluate(_payload(fixtures, ["pretty"]))
            self.assertEqual("excluded", result["decision"])
            self.assertNotIn(result["decision"], ("reproducible", "allowed"))
            self.assertEqual(["pretty"], result["rejectedClaims"])
            self.assertEqual([], result["preservedResults"])
            joined = " ".join(result["reasons"]).lower()
            self.assertIn("visual", joined)
            self.assertTrue(result["reasons"])

    def test_repetition_same_behavior_for_each_kind(self):
        outcomes = []
        for kind in KINDS:
            fixtures = [
                _fixture("good", kind=kind, visual_result=f"{kind} intact"),
                _fixture(
                    "bad",
                    kind=kind,
                    provenance=None,
                    visual_result=f"{kind} looks reproducible",
                ),
            ]
            result = p006_tc03.evaluate(_payload(fixtures, ["good", "bad"]))
            outcomes.append(
                (
                    result["decision"],
                    tuple(result["rejectedClaims"]),
                    tuple(result["preservedResults"]),
                    tuple(result["openQuestions"]),
                )
            )
            self.assertEqual("excluded", result["decision"])
            self.assertNotIn(result["decision"], ("reproducible", "allowed"))
        self.assertEqual(1, len(set(outcomes)))

    def test_every_claimed_fixture_with_complete_provenance_is_accepted(self):
        fixtures = [
            _fixture(kind, kind=kind, visual_result="recorded")
            for kind in ("model", "stock_profile", "movie_reference", "generated_screenshot")
        ]
        claim_ids = [item["id"] for item in fixtures]
        result = p006_tc03.evaluate(_payload(fixtures, claim_ids))
        self.assertEqual("accepted", result["decision"])
        self.assertEqual(claim_ids, result["preservedResults"])
        self.assertEqual([], result["rejectedClaims"])
        self.assertEqual([], result["openQuestions"])

    def test_incomplete_provenance_fields_are_excluded(self):
        for field in ("origin", "owner", "acquiredAt", "permittedUse"):
            incomplete = _provenance()
            del incomplete[field]
            result = p006_tc03.evaluate(
                _payload(
                    [_fixture("partial", provenance=incomplete, visual_result="sharp")],
                    ["partial"],
                )
            )
            self.assertEqual("excluded", result["decision"], field)
            self.assertEqual(["partial"], result["rejectedClaims"])
            self.assertEqual([], result["preservedResults"])

            blank = _provenance(**{field: "   "})
            result = p006_tc03.evaluate(
                _payload(
                    [_fixture("blank", provenance=blank, visual_result="allowed")],
                    ["blank"],
                )
            )
            self.assertEqual("excluded", result["decision"], field)
            self.assertNotEqual("allowed", result["decision"])

            wrong_type = _provenance(**{field: 1})
            result = p006_tc03.evaluate(
                _payload(
                    [_fixture("typed", provenance=wrong_type)],
                    ["typed"],
                )
            )
            self.assertEqual("excluded", result["decision"], field)

    def test_missing_fixture_id_is_an_open_question(self):
        fixtures = [_fixture("present")]
        result = p006_tc03.evaluate(_payload(fixtures, ["present", "ghost"]))
        self.assertEqual("excluded", result["decision"])
        self.assertEqual(["ghost"], result["openQuestions"])
        self.assertIn("ghost", result["openQuestions"])
        self.assertEqual(["present"], result["preservedResults"])
        self.assertEqual([], result["rejectedClaims"])
        self.assertTrue(any("ghost" in reason for reason in result["reasons"]))

    def test_missing_id_and_incomplete_provenance_together(self):
        fixtures = [
            _fixture("whole"),
            _fixture("bare", provenance={}),
        ]
        result = p006_tc03.evaluate(
            _payload(fixtures, ["absent", "bare", "whole", "bare"])
        )
        self.assertEqual("excluded", result["decision"])
        self.assertEqual(["absent"], result["openQuestions"])
        self.assertEqual(["bare"], result["rejectedClaims"])
        self.assertEqual(["whole"], result["preservedResults"])

    def test_unclaimed_fixture_without_provenance_is_excluded(self):
        fixtures = [
            _fixture("claimed", kind="stock_profile"),
            _fixture("unclaimed", kind="model", provenance=None, visual_result="reproducible"),
        ]
        result = p006_tc03.evaluate(_payload(fixtures, ["claimed"]))
        self.assertEqual("excluded", result["decision"])
        self.assertEqual(["claimed"], result["preservedResults"])
        self.assertEqual(["unclaimed"], result["rejectedClaims"])
        self.assertNotIn(result["decision"], ("accepted", "reproducible", "allowed"))

    def test_duplicate_fixture_id_raises(self):
        fixtures = [
            _fixture("same"),
            _fixture("same", provenance=None),
        ]
        with self.assertRaises(ValueError):
            p006_tc03.evaluate(_payload(fixtures, ["same"]))

    def test_none_and_omitted_provenance_are_excluded(self):
        omitted = {
            "id": "omitted",
            "kind": "other",
            "visualResult": "reproducible",
        }
        result = p006_tc03.evaluate(_payload([omitted], ["omitted"]))
        self.assertEqual("excluded", result["decision"])
        self.assertEqual(["omitted"], result["rejectedClaims"])
        self.assertNotIn(result["decision"], ("reproducible", "allowed"))

    def test_duplicate_claim_ids_are_reported_once(self):
        fixtures = [
            _fixture("good"),
            _fixture("bad", provenance=None, visual_result="allowed"),
        ]
        result = p006_tc03.evaluate(_payload(fixtures, ["bad", "good", "bad", "good"]))
        self.assertEqual(["bad"], result["rejectedClaims"])
        self.assertEqual(["good"], result["preservedResults"])
        self.assertEqual("excluded", result["decision"])

    def test_reasons_are_non_empty_strings_and_decision_is_not_allowed(self):
        payloads = [
            _payload([], []),
            _payload([_fixture("only")], ["only"]),
            _payload([_fixture("x", provenance=None, visual_result="reproducible")], ["x"]),
            _payload([_fixture("y")], ["missing"]),
        ]
        for payload in payloads:
            result = p006_tc03.evaluate(payload)
            self.assertNotEqual("allowed", result["decision"])
            self.assertTrue(result["reasons"])
            self._assert_schema(result)

    def _assert_schema(self, result):
        self.assertEqual(list(_RESULT_KEYS), list(result.keys()))
        self.assertIsInstance(result["caseId"], str)
        self.assertIsInstance(result["decision"], str)
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        if result["decision"] != "allowed":
            self.assertTrue(result["reasons"])


if __name__ == "__main__":
    unittest.main()
