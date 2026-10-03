"""TC-P007-04 contradictory outcomes and distinct profile hashes."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


def _load():
    path = Path(__file__).resolve().parents[1] / "gates" / "p007_tc04.py"
    spec = importlib.util.spec_from_file_location("p007_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load()

SHA_A = "a" * 64
SHA_B = "b" * 64
RAW_LOG = "raw-log-p007-04"


def _profiles(name="StockProfile", first=SHA_A, second=SHA_B):
    return [
        {"displayName": name, "sha256": first},
        {"displayName": name, "sha256": second},
    ]


def _payload(summary=True, raw=False, skipped=False, stale=False, raw_log=RAW_LOG, profiles=None, case_id="TC-P007-04"):
    return {
        "caseId": case_id,
        "summaryPassed": summary,
        "rawFailed": raw,
        "skippedPhysicalAsPass": skipped,
        "staleReport": stale,
        "rawLogId": raw_log,
        "profiles": _profiles() if profiles is None else profiles,
    }


def _assert_contract(test, result):
    test.assertEqual(
        list(result),
        ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"],
    )
    test.assertEqual(result["caseId"], "TC-P007-04")
    test.assertNotEqual(result["decision"], "allowed")
    test.assertIsInstance(result["reasons"], list)
    test.assertTrue(result["reasons"])
    test.assertTrue(all(isinstance(item, str) and item.strip() for item in result["reasons"]))
    test.assertIsInstance(result["rejectedClaims"], list)
    test.assertIsInstance(result["preservedResults"], list)
    test.assertIsInstance(result["openQuestions"], list)


def _assert_profiles_preserved(test, result, raw_log=RAW_LOG, profiles=None):
    profiles = _profiles() if profiles is None else profiles
    test.assertIn(raw_log, result["preservedResults"])
    for profile in profiles:
        test.assertIn(profile["sha256"], result["preservedResults"])
    test.assertEqual(result["preservedResults"], [raw_log] + [profile["sha256"] for profile in profiles])


class TcP00704ContradictoryOutcomes(unittest.TestCase):
    def test_wrong_case_id_and_bad_payload_raise(self):
        with self.assertRaisesRegex(ValueError, "caseId"):
            GATE.evaluate(_payload(case_id="TC-P007-03"))
        with self.assertRaisesRegex(ValueError, "bad payload"):
            GATE.evaluate(None)
        with self.assertRaisesRegex(ValueError, "summaryPassed"):
            GATE.evaluate(_payload(summary=1))
        with self.assertRaisesRegex(ValueError, "rawLogId"):
            GATE.evaluate(_payload(raw_log="  "))
        with self.assertRaisesRegex(ValueError, "profiles"):
            bad = _payload()
            bad["profiles"] = [{"displayName": "OnlyName"}]
            GATE.evaluate(bad)
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            bad = _payload()
            bad["note"] = "trust the summary"
            GATE.evaluate(bad)

    def test_false_pass_green_summary_and_failing_raw_log_is_blocked(self):
        payload = _payload(summary=True, raw=True, skipped=False, stale=False)
        original = copy.deepcopy(payload)
        result = GATE.evaluate(payload)
        self.assertEqual(payload, original)
        _assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        self.assertNotEqual(result["decision"], "allowed")
        self.assertNotEqual(result["decision"], "consistent")
        self.assertNotEqual(result["decision"], "failed")
        _assert_profiles_preserved(self, result)
        self.assertEqual(result["preservedResults"].count(SHA_A), 1)
        self.assertEqual(result["preservedResults"].count(SHA_B), 1)
        self.assertNotIn("StockProfile", result["preservedResults"])
        self.assertIn("acceptance", result["rejectedClaims"])
        self.assertIn("summary-pass", result["rejectedClaims"])
        self.assertIn("raw-log", result["rejectedClaims"])
        text = " ".join(result["reasons"]).lower()
        self.assertIn("raw", text)
        self.assertIn("block", text)
        self.assertIn("distinct", text)
        self.assertEqual(result["openQuestions"], [])

    def test_skipped_physical_counted_as_pass_is_blocked(self):
        result = GATE.evaluate(_payload(summary=True, raw=False, skipped=True, stale=False))
        _assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        self.assertNotEqual(result["decision"], "allowed")
        _assert_profiles_preserved(self, result)
        self.assertIn("skipped-physical-as-pass", result["rejectedClaims"])
        self.assertNotIn("raw-log", result["rejectedClaims"])
        self.assertTrue(any("physical" in question.lower() for question in result["openQuestions"]))
        self.assertIn("skipped", " ".join(result["reasons"]).lower())

    def test_stale_report_with_green_summary_is_blocked(self):
        result = GATE.evaluate(_payload(summary=True, raw=False, skipped=False, stale=True))
        _assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        self.assertNotEqual(result["decision"], "allowed")
        _assert_profiles_preserved(self, result)
        self.assertIn("stale-report", result["rejectedClaims"])
        self.assertTrue(any("stale" in question.lower() or "report" in question.lower() for question in result["openQuestions"]))
        self.assertIn("stale", " ".join(result["reasons"]).lower())

    def test_all_false_pass_flags_together_are_blocked_and_preserve_hashes(self):
        result = GATE.evaluate(_payload(summary=True, raw=True, skipped=True, stale=True))
        _assert_contract(self, result)
        self.assertEqual(result["decision"], "blocked")
        _assert_profiles_preserved(self, result)
        for claim in ("acceptance", "summary-pass", "raw-log", "skipped-physical-as-pass", "stale-report"):
            self.assertIn(claim, result["rejectedClaims"])
        self.assertGreaterEqual(len(result["openQuestions"]), 2)
        self.assertIn("distinct", " ".join(result["reasons"]).lower())

    def test_distinct_hashes_without_false_pass_are_consistent_or_failed(self):
        consistent = GATE.evaluate(_payload(summary=True, raw=False, skipped=False, stale=False))
        _assert_contract(self, consistent)
        self.assertEqual(consistent["decision"], "consistent")
        self.assertEqual(consistent["rejectedClaims"], [])
        _assert_profiles_preserved(self, consistent)
        self.assertIn("distinct", " ".join(consistent["reasons"]).lower())

        failed = GATE.evaluate(_payload(summary=False, raw=True, skipped=False, stale=False))
        _assert_contract(self, failed)
        self.assertEqual(failed["decision"], "failed")
        self.assertNotEqual(failed["decision"], "blocked")
        self.assertNotEqual(failed["decision"], "allowed")
        self.assertIn("raw-log", failed["rejectedClaims"])
        self.assertIn("acceptance", failed["rejectedClaims"])
        self.assertNotIn("summary-pass", failed["rejectedClaims"])
        _assert_profiles_preserved(self, failed)
        self.assertIn("failed", " ".join(failed["reasons"]).lower())

        quiet = GATE.evaluate(_payload(summary=False, raw=False, skipped=False, stale=False))
        _assert_contract(self, quiet)
        self.assertEqual(quiet["decision"], "consistent")
        _assert_profiles_preserved(self, quiet)

    def test_same_display_name_does_not_collapse_hashes_when_raw_failed_only(self):
        profiles = _profiles("Rec709")
        result = GATE.evaluate(_payload(summary=False, raw=True, profiles=profiles))
        _assert_contract(self, result)
        self.assertEqual(result["decision"], "failed")
        self.assertEqual(result["preservedResults"], [RAW_LOG, SHA_A, SHA_B])
        self.assertIn("distinct", " ".join(result["reasons"]).lower())

    def test_skipped_or_stale_without_green_summary_follows_raw_log(self):
        failed = GATE.evaluate(_payload(summary=False, raw=True, skipped=True, stale=True))
        _assert_contract(self, failed)
        self.assertEqual(failed["decision"], "failed")
        self.assertNotEqual(failed["decision"], "allowed")
        _assert_profiles_preserved(self, failed)
        self.assertTrue(failed["openQuestions"])

        consistent = GATE.evaluate(_payload(summary=False, raw=False, skipped=True, stale=False))
        _assert_contract(self, consistent)
        self.assertEqual(consistent["decision"], "consistent")
        _assert_profiles_preserved(self, consistent)


if __name__ == "__main__":
    unittest.main()
