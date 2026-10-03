"""Host tests for the TC-P007-01 provenance and certainty gate."""

import copy
import sys
import unittest

sys.path.insert(0, "/workspace/s23/scripts/gates")

from p007_tc01 import evaluate


H1 = "a" * 64
H2 = "b" * 64
H3 = "c" * 64
NAME = "Stock Neutral"


def payload(**overrides):
    base = {
        "caseId": "TC-P007-01",
        "profiles": [
            {"displayName": NAME, "sha256": H1},
            {"displayName": NAME, "sha256": H2},
        ],
        "image": {"id": "still-17", "rights": "unknown"},
        "unsupportedPhysicalClaim": False,
        "claimText": "physical sensor behavior is established",
        "softwareResult": "host fixture parser accepts both profile hashes",
        "openQuestion": "Does a physical S23 sensor match this fixture?",
        "evidenceKind": "software",
    }
    base.update(overrides)
    return base


def hashes_of(result):
    return [item for item in result["preservedResults"] if item in {H1, H2, H3}]


class Tcp00701Tests(unittest.TestCase):
    def assert_contract(self, result, decision):
        self.assertEqual(
            set(result),
            {
                "caseId",
                "decision",
                "reasons",
                "rejectedClaims",
                "preservedResults",
                "openQuestions",
            },
        )
        self.assertEqual(result["caseId"], "TC-P007-01")
        self.assertEqual(result["decision"], decision)
        self.assertNotIn(result["decision"], {"established", "allowed", "collapsed"})
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        if result["decision"] != "allowed":
            self.assertTrue(result["reasons"])

    def test_baseline_keeps_distinct_profiles_and_excludes_unknown_image(self):
        result = evaluate(payload())
        self.assert_contract(result, "excluded")
        self.assertEqual(hashes_of(result), [H1, H2])
        self.assertIn("still-17", result["rejectedClaims"])
        self.assertNotIn("still-17", result["preservedResults"])
        self.assertEqual(result["openQuestions"], [])
        self.assertNotIn(NAME, result["preservedResults"])
        text = " ".join(result["reasons"]).lower()
        self.assertIn("distinct", text)
        self.assertIn("display name", text)
        self.assertIn("public bundle", text)

    def test_same_display_name_is_not_collapsed_to_one_hash(self):
        mutant_last_write = [H2]
        result = evaluate(payload())
        self.assertEqual(hashes_of(result), [H1, H2])
        self.assertNotEqual(hashes_of(result), mutant_last_write)
        self.assertNotEqual(result["decision"], "collapsed")

    def test_reversed_profile_order_preserves_both_hashes(self):
        profiles = [
            {"displayName": NAME, "sha256": H2},
            {"displayName": NAME, "sha256": H1},
        ]
        result = evaluate(payload(profiles=profiles))
        self.assertEqual(hashes_of(result), [H2, H1])

    def test_additional_names_and_repeated_hash_stay_content_addressed(self):
        profiles = [
            {"displayName": NAME, "sha256": H1},
            {"displayName": NAME, "sha256": H2},
            {"displayName": "Other", "sha256": H3},
            {"displayName": "Alias", "sha256": H1},
        ]
        result = evaluate(payload(profiles=profiles))
        self.assertEqual(hashes_of(result), [H1, H2, H3])

    def test_permitted_image_is_accepted_with_distinct_profiles(self):
        result = evaluate(payload(image={"id": "still-ok", "rights": "permitted"}))
        self.assert_contract(result, "accepted")
        self.assertEqual(result["preservedResults"], [H1, H2, "still-ok"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertNotIn("still-ok", result["rejectedClaims"])

    def test_denied_rights_exclude_image_like_unknown(self):
        result = evaluate(payload(image={"id": "still-no", "rights": "denied"}))
        self.assert_contract(result, "excluded")
        self.assertIn("still-no", result["rejectedClaims"])
        self.assertNotIn("still-no", result["preservedResults"])
        self.assertEqual(hashes_of(result), [H1, H2])

    def test_unsupported_physical_claim_is_software_only(self):
        body = payload(
            unsupportedPhysicalClaim=True,
            image={"id": "still-ok", "rights": "permitted"},
        )
        result = evaluate(body)
        self.assert_contract(result, "software_only")
        self.assertIn(body["claimText"], result["rejectedClaims"])
        self.assertNotIn(body["claimText"], result["preservedResults"])
        self.assertIn(body["softwareResult"], result["preservedResults"])
        self.assertIn(body["openQuestion"], result["openQuestions"])
        self.assertEqual(result["openQuestions"], [body["openQuestion"]])
        self.assertEqual(hashes_of(result), [H1, H2])
        self.assertIn("still-ok", result["preservedResults"])
        self.assertNotIn(result["decision"], {"established", "allowed"})

    def test_unsupported_claim_still_excludes_unknown_and_denied_images(self):
        for rights in ("unknown", "denied"):
            with self.subTest(rights=rights):
                body = payload(
                    unsupportedPhysicalClaim=True,
                    image={"id": "blocked", "rights": rights},
                )
                result = evaluate(body)
                self.assert_contract(result, "software_only")
                self.assertEqual(
                    result["rejectedClaims"], ["blocked", body["claimText"]]
                )
                self.assertNotIn("blocked", result["preservedResults"])
                self.assertIn(body["softwareResult"], result["preservedResults"])
                self.assertIn(body["openQuestion"], result["openQuestions"])

    def test_non_physical_evidence_never_becomes_established(self):
        for kind in ("emulator", "simulated", "unavailable_probe"):
            with self.subTest(kind=kind, claim=False):
                result = evaluate(
                    payload(
                        evidenceKind=kind,
                        image={"id": "still-ok", "rights": "permitted"},
                    )
                )
                self.assert_contract(result, "accepted")
                self.assertNotEqual(result["decision"], "established")
                text = " ".join(result["reasons"])
                self.assertIn(kind, text)
                self.assertIn("does not establish physical behavior", text)
            with self.subTest(kind=kind, claim=True):
                body = payload(
                    evidenceKind=kind,
                    unsupportedPhysicalClaim=True,
                    image={"id": "still-ok", "rights": "permitted"},
                )
                result = evaluate(body)
                self.assert_contract(result, "software_only")
                self.assertNotEqual(result["decision"], "established")
                self.assertIn(body["claimText"], result["rejectedClaims"])
                self.assertIn(body["softwareResult"], result["preservedResults"])
                self.assertIn(body["openQuestion"], result["openQuestions"])
                text = " ".join(result["reasons"])
                self.assertIn("not established", text)

    def test_false_pass_physical_established_label_is_rejected(self):
        claim = "untested physical behavior is established"
        software = "narrower software comparator matched the fixture bytes"
        question = "physical measurement remains open"
        result = evaluate(
            payload(
                unsupportedPhysicalClaim=True,
                claimText=claim,
                softwareResult=software,
                openQuestion=question,
                evidenceKind="emulator",
                image={"id": "still-17", "rights": "unknown"},
            )
        )
        self.assertEqual(result["decision"], "software_only")
        self.assertIn(claim, result["rejectedClaims"])
        self.assertIn(software, result["preservedResults"])
        self.assertIn(question, result["openQuestions"])
        self.assertNotEqual(result["decision"], "established")

    def test_payload_is_not_mutated(self):
        body = payload()
        snapshot = copy.deepcopy(body)
        evaluate(body)
        self.assertEqual(body, snapshot)

    def test_bad_payload_and_wrong_case_raise(self):
        with self.assertRaises(ValueError):
            evaluate(["not", "a", "dict"])
        with self.assertRaises(ValueError):
            evaluate(None)
        with self.assertRaises(ValueError):
            evaluate(payload(caseId="TC-P007-02"))
        with self.assertRaises(ValueError):
            evaluate(payload(caseId="TC-P007-01 "))
        missing = payload()
        del missing["openQuestion"]
        with self.assertRaises(ValueError):
            evaluate(missing)
        with self.assertRaises(ValueError):
            evaluate(payload(unsupportedPhysicalClaim=1))
        with self.assertRaises(ValueError):
            evaluate(payload(image={"id": "x", "rights": "public"}))
        with self.assertRaises(ValueError):
            evaluate(payload(image={"id": "", "rights": "unknown"}))
        with self.assertRaises(ValueError):
            evaluate(payload(profiles=[{"displayName": NAME}]))
        with self.assertRaises(ValueError):
            evaluate(payload(profiles="profiles"))
        with self.assertRaises(ValueError):
            evaluate(payload(evidenceKind=""))
        with self.assertRaises(ValueError):
            evaluate(payload(claimText=None))
        with self.assertRaises(ValueError):
            evaluate(payload(profiles=[{"displayName": NAME, "sha256": 1}]))


if __name__ == "__main__":
    unittest.main()
