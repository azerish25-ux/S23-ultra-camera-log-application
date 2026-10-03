"""TC-P007-06 uncontrolled threshold revision."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gates"))
import p007_tc06 as gate


RESULT_KEYS = ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"]
GATES = ("cadence", "color error", "render latency", "temporal artifact severity")
STOCK = "Stock profile"
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_DUP = "d" * 64


def profiles(*digests: str) -> list[dict[str, str]]:
    return [{"displayName": STOCK, "sha256": digest} for digest in digests]


class UncontrolledThresholdTests(unittest.TestCase):
    def payload(self, name, loosened, reviewed, versionRecorded, originalFailed, prof=None) -> dict:
        return {
            "caseId": "TC-P007-06",
            "threshold": {
                "name": name,
                "loosened": loosened,
                "reviewed": reviewed,
                "versionRecorded": versionRecorded,
                "originalFailed": originalFailed,
            },
            "profiles": profiles(HASH_A, HASH_B) if prof is None else prof,
        }

    def assert_shape(self, result: dict, decision: str) -> None:
        self.assertEqual(RESULT_KEYS, list(result))
        self.assertEqual("TC-P007-06", result["caseId"])
        self.assertEqual(decision, result["decision"])
        self.assertNotEqual("allowed", result["decision"])
        for key in ("reasons", "rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertTrue(result["reasons"])
        self.assertNotIn("allowed", " ".join(result["reasons"]))
        self.assertFalse(any(item.startswith("original-pass:") for item in result["preservedResults"]))

    def test_cadence_unreviewed_loosen_keeps_original_failure(self):
        result = gate.evaluate(self.payload("cadence", True, False, False, True))
        self.assert_shape(result, "blocked")
        self.assertEqual(["cadence"], result["rejectedClaims"])
        self.assertEqual(
            ["original-failure:cadence", HASH_A, HASH_B],
            result["preservedResults"],
        )
        text = " ".join(result["reasons"])
        self.assertIn("not an original pass", text)
        self.assertIn("same display name", text)
        self.assertTrue(result["openQuestions"])

    def test_color_error_review_without_version_is_blocked(self):
        result = gate.evaluate(self.payload("color error", True, True, False, True))
        self.assert_shape(result, "blocked")
        self.assertIn("original-failure:color error", result["preservedResults"])
        self.assertIn(HASH_A, result["preservedResults"])
        self.assertIn(HASH_B, result["preservedResults"])
        self.assertNotEqual("allowed", result["decision"])

    def test_render_latency_version_without_review_is_blocked(self):
        result = gate.evaluate(self.payload("render latency", True, False, True, True))
        self.assert_shape(result, "blocked")
        self.assertEqual(
            ["original-failure:render latency", HASH_A, HASH_B],
            result["preservedResults"],
        )
        self.assertIn("render latency", result["rejectedClaims"])

    def test_temporal_artifact_reviewed_revision_is_not_an_original_pass(self):
        result = gate.evaluate(self.payload(
            "temporal artifact severity", True, True, True, True,
        ))
        self.assert_shape(result, "reviewed_revision")
        self.assertEqual([], result["rejectedClaims"])
        self.assertIn("Renewed independent validation is still required.", result["openQuestions"])
        self.assertIn("Renewed independent validation is still required.", result["reasons"])
        self.assertEqual(
            ["original-failure:temporal artifact severity", HASH_A, HASH_B],
            result["preservedResults"],
        )
        self.assertIn("not a claim that the original run passed", " ".join(result["reasons"]))

    def test_reviewed_revision_without_original_failure_does_not_invent_one(self):
        for name in GATES:
            with self.subTest(name=name):
                result = gate.evaluate(self.payload(name, True, True, True, False))
                self.assert_shape(result, "reviewed_revision")
                self.assertNotIn(f"original-failure:{name}", result["preservedResults"])
                self.assertEqual([HASH_A, HASH_B], result["preservedResults"])
                self.assertIn("not a claim that the original run passed", " ".join(result["reasons"]))

    def test_each_gate_matrix(self):
        cases = (
            (True, False, False, True, "blocked"),
            (True, True, False, True, "blocked"),
            (True, False, True, True, "blocked"),
            (True, True, True, True, "reviewed_revision"),
            (True, True, True, False, "reviewed_revision"),
            (False, False, False, True, "failed"),
            (False, True, True, True, "failed"),
            (False, False, False, False, "unchanged"),
            (False, True, True, False, "unchanged"),
        )
        for name in GATES:
            for loosened, reviewed, versioned, failed, decision in cases:
                with self.subTest(name=name, loosened=loosened, reviewed=reviewed,
                                  versioned=versioned, failed=failed):
                    result = gate.evaluate(self.payload(name, loosened, reviewed, versioned, failed))
                    self.assert_shape(result, decision)
                    self.assertIn(HASH_A, result["preservedResults"])
                    self.assertIn(HASH_B, result["preservedResults"])
                    if decision == "blocked":
                        self.assertEqual(["original-failure:" + name, HASH_A, HASH_B], result["preservedResults"])
                        self.assertEqual([name], result["rejectedClaims"])
                        self.assertIn("not an original pass", " ".join(result["reasons"]))
                    elif decision == "failed":
                        self.assertIn("original-failure:" + name, result["preservedResults"])
                    elif decision == "unchanged":
                        self.assertNotIn("original-failure:" + name, result["preservedResults"])
                        self.assertEqual([HASH_A, HASH_B], result["preservedResults"])

    def test_duplicate_profile_hashes_stay_distinct_on_blocked_cadence(self):
        prof = [
            {"displayName": STOCK, "sha256": HASH_B},
            {"displayName": "Other label", "sha256": HASH_B},
            {"displayName": STOCK, "sha256": HASH_A},
            {"displayName": STOCK, "sha256": HASH_DUP},
            {"displayName": STOCK, "sha256": HASH_A},
        ]
        result = gate.evaluate(self.payload("cadence", True, False, False, True, prof=prof))
        self.assert_shape(result, "blocked")
        self.assertEqual(
            ["original-failure:cadence", HASH_B, HASH_A, HASH_DUP],
            result["preservedResults"],
        )
        self.assertEqual(1, result["preservedResults"].count(HASH_B))

    def test_schema_and_case_id_errors(self):
        with self.assertRaises(ValueError):
            gate.evaluate("not-a-dict")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload("cadence", False, False, False, False) | {"caseId": "TC-P007-05"})
        with self.assertRaises(ValueError):
            gate.evaluate({"caseId": "TC-P007-06", "profiles": []})
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload("cadence", 1, False, False, True))  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload("", True, True, True, True))
        with self.assertRaises(ValueError):
            bad = self.payload("cadence", False, False, False, False)
            del bad["threshold"]["versionRecorded"]
            gate.evaluate(bad)
        with self.assertRaises(ValueError):
            gate.evaluate(self.payload("cadence", False, False, False, False, prof=[{"sha256": HASH_A}]))


if __name__ == "__main__":
    unittest.main()
