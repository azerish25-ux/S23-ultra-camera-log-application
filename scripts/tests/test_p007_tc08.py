"""TC-P007-08 independent reproduction."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from gates.p007_tc08 import evaluate

CASE_ID = "TC-P007-08"
PHYSICAL = "physical S23 qualification remains open"
RESULT_KEYS = [
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
]
HASH_A = "a" * 64
HASH_B = "b" * 64
STATED = "host software result reproduced from phase artifacts"


def profiles():
    return [
        {"displayName": "Stock", "sha256": HASH_A},
        {"displayName": "Stock", "sha256": HASH_B},
    ]


def payload(**overrides):
    reproduction = {
        "undocumentedFiles": False,
        "manualIntervention": False,
        "missingPrerequisite": None,
        "phoneConnected": False,
    }
    reproduction.update(overrides.pop("reproduction", {}))
    body = {
        "caseId": CASE_ID,
        "reproduction": reproduction,
        "statedSoftwareResult": STATED,
        "tempPath": "/tmp/p007-tc08-a",
        "profiles": profiles(),
    }
    body.update(overrides)
    return body


class Tcp007Tc08Tests(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(list(result), RESULT_KEYS)
        self.assertEqual(set(result), set(RESULT_KEYS))
        self.assertEqual(result["caseId"], CASE_ID)
        self.assertIsInstance(result["reasons"], list)
        self.assertIsInstance(result["rejectedClaims"], list)
        self.assertIsInstance(result["preservedResults"], list)
        self.assertIsInstance(result["openQuestions"], list)
        self.assertNotIn(result["decision"], {"allowed", "passed"})
        self.assertTrue(result["reasons"])
        self.assertIn(STATED, result["preservedResults"])
        self.assertEqual(
            [item for item in result["preservedResults"] if item in {HASH_A, HASH_B}],
            [HASH_A, HASH_B],
        )

    def test_undocumented_files_remain_unverified(self):
        result = evaluate(payload(reproduction={"undocumentedFiles": True}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("undocumented-files", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"allowed", "passed"})
        text = " ".join(result["reasons"]).lower()
        self.assertIn("undocumented", text)

    def test_manual_intervention_remains_unverified(self):
        result = evaluate(payload(reproduction={"manualIntervention": True}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("unrecorded-manual-intervention", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"allowed", "passed"})
        text = " ".join(result["reasons"]).lower()
        self.assertIn("manual", text)

    def test_missing_prerequisite_is_an_open_question(self):
        missing = "original developer private notes"
        result = evaluate(payload(reproduction={"missingPrerequisite": missing}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertEqual(result["openQuestions"], [missing])
        self.assertIn("missing-prerequisite", result["rejectedClaims"])
        self.assertNotIn(PHYSICAL, result["openQuestions"])

    def test_combined_faults_never_pass(self):
        missing = "fresh dependency lock"
        result = evaluate(
            payload(
                reproduction={
                    "undocumentedFiles": True,
                    "manualIntervention": True,
                    "missingPrerequisite": missing,
                    "phoneConnected": True,
                },
                tempPath="/tmp/does-not-grant-a-pass",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertEqual(result["openQuestions"], [missing])
        self.assertEqual(
            result["rejectedClaims"],
            [
                "undocumented-files",
                "unrecorded-manual-intervention",
                "missing-prerequisite",
            ],
        )

    def test_clean_reproduction_leaves_physical_qualification_open(self):
        disconnected = evaluate(payload(reproduction={"phoneConnected": False}))
        connected = evaluate(
            payload(
                reproduction={"phoneConnected": True},
                tempPath="/tmp/p007-tc08-phone",
            )
        )
        for result in (disconnected, connected):
            self.assert_contract(result)
            self.assertEqual(result["decision"], "reproduced")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(PHYSICAL, result["openQuestions"])
            self.assertEqual(result["openQuestions"], [PHYSICAL])
        self.assertEqual(disconnected["decision"], connected["decision"])
        self.assertEqual(disconnected["openQuestions"], connected["openQuestions"])

    def test_temp_path_does_not_change_the_decision(self):
        first = evaluate(payload(tempPath="/tmp/p007-one"))
        second = evaluate(payload(tempPath="/var/tmp/p007-two"))
        self.assertEqual(first["decision"], second["decision"])
        self.assertEqual(first, second)
        dirty_a = evaluate(
            payload(reproduction={"undocumentedFiles": True}, tempPath="/tmp/left")
        )
        dirty_b = evaluate(
            payload(reproduction={"undocumentedFiles": True}, tempPath="/tmp/right")
        )
        self.assertEqual(dirty_a["decision"], "unverified")
        self.assertEqual(dirty_a, dirty_b)

    def test_distinct_hashes_with_the_same_display_name_are_preserved(self):
        third = "9" * 64
        body = payload()
        body["profiles"] = [
            {"displayName": "Stock", "sha256": HASH_A},
            {"displayName": "Stock", "sha256": HASH_B},
            {"displayName": "Stock", "sha256": third},
        ]
        result = evaluate(body)
        self.assertEqual(
            result["preservedResults"], [STATED, HASH_A, HASH_B, third]
        )

    def test_unknown_rights_image_fields_are_not_this_case(self):
        body = payload()
        body["profiles"] = [
            {"displayName": "Stock", "sha256": HASH_A, "rights": "unknown"},
            {
                "displayName": "Stock",
                "sha256": HASH_B,
                "redistribution": "unknown",
            },
        ]
        body["image"] = {"rights": "unknown", "sha256": "e" * 64}
        result = evaluate(body)
        self.assertEqual(result["decision"], "reproduced")
        self.assertNotIn("unknown-rights", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"], [STATED, HASH_A, HASH_B])
        self.assertNotIn("e" * 64, result["preservedResults"])

    def test_phone_and_temp_matrix_does_not_invent_success(self):
        for undocumented in (False, True):
            for manual in (False, True):
                for missing in (None, "cache absent"):
                    for phone in (False, True):
                        for temp in ("/tmp/alpha", "/tmp/beta"):
                            result = evaluate(
                                payload(
                                    reproduction={
                                        "undocumentedFiles": undocumented,
                                        "manualIntervention": manual,
                                        "missingPrerequisite": missing,
                                        "phoneConnected": phone,
                                    },
                                    tempPath=temp,
                                )
                            )
                            self.assert_contract(result)
                            if undocumented or manual or missing is not None:
                                self.assertEqual(result["decision"], "unverified")
                                if missing is not None:
                                    self.assertIn(missing, result["openQuestions"])
                            else:
                                self.assertEqual(result["decision"], "reproduced")
                                self.assertIn(PHYSICAL, result["openQuestions"])

    def test_wrong_case_id_and_invalid_payload_raise(self):
        with self.assertRaises(ValueError):
            evaluate(None)
        with self.assertRaises(ValueError):
            evaluate({"caseId": "TC-P007-07"})
        with self.assertRaises(ValueError):
            evaluate({"caseId": CASE_ID})
        broken = payload()
        broken["reproduction"]["undocumentedFiles"] = "yes"
        with self.assertRaises(ValueError):
            evaluate(broken)
        broken = payload()
        broken["reproduction"]["missingPrerequisite"] = 12
        with self.assertRaises(ValueError):
            evaluate(broken)
        broken = payload()
        broken["tempPath"] = None
        with self.assertRaises(ValueError):
            evaluate(broken)
        broken = payload()
        broken["profiles"] = [{"displayName": "Stock", "sha256": ""}]
        with self.assertRaises(ValueError):
            evaluate(broken)


if __name__ == "__main__":
    unittest.main()
