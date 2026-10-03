"""TC-P007-03 missing provenance, distinct profile hashes, and rights exclusion."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

KINDS = ("model", "stock_profile", "movie_reference", "generated_screenshot")


def _load():
    path = Path(__file__).resolve().parents[1] / "gates" / "p007_tc03.py"
    spec = importlib.util.spec_from_file_location("p007_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load()


def _provenance():
    return {
        "origin": "authored:P007",
        "owner": "repository tests",
        "acquiredAt": "2026-10-02",
        "permittedUse": "test and private comparison",
    }


def _fixture(fixture_id, kind, name, sha, rights="permitted", provenance="present", visual="convincing frame"):
    return {
        "id": fixture_id,
        "kind": kind,
        "displayName": name,
        "sha256": sha,
        "provenance": _provenance() if provenance == "present" else provenance,
        "visualResult": visual,
        "rights": rights,
    }


def _payload(*fixtures, case_id="TC-P007-03"):
    return {"caseId": case_id, "fixtures": list(fixtures)}


def _assert_contract(test, result):
    test.assertEqual(
        list(result),
        ["caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions"],
    )
    test.assertEqual(result["caseId"], "TC-P007-03")
    test.assertIsInstance(result["reasons"], list)
    test.assertIsInstance(result["rejectedClaims"], list)
    test.assertIsInstance(result["preservedResults"], list)
    test.assertIsInstance(result["openQuestions"], list)
    test.assertNotEqual(result["decision"], "allowed")
    test.assertNotEqual(result["decision"], "reproducible")
    test.assertTrue(result["reasons"])
    test.assertTrue(all(isinstance(item, str) and item.strip() for item in result["reasons"]))
    test.assertTrue(all(isinstance(item, str) and item.strip() for item in result["openQuestions"]))


def _ids(result):
    return [item["id"] for item in result["preservedResults"]]


class TcP00703MissingProvenance(unittest.TestCase):
    def test_wrong_case_id_and_bad_payload_raise(self):
        valid = _fixture("model-a", "model", "Hero", "a" * 64)
        with self.assertRaisesRegex(ValueError, "caseId"):
            GATE.evaluate(_payload(valid, case_id="TC-P007-04"))
        with self.assertRaisesRegex(ValueError, "bad payload"):
            GATE.evaluate(["TC-P007-03"])
        with self.assertRaisesRegex(ValueError, "bad payload"):
            GATE.evaluate({"caseId": "TC-P007-03"})
        with self.assertRaisesRegex(ValueError, "bad payload"):
            GATE.evaluate({"caseId": "TC-P007-03", "fixtures": [valid], "extra": True})
        broken = _fixture("model-a", "clip", "Hero", "a" * 64)
        with self.assertRaisesRegex(ValueError, "kind"):
            GATE.evaluate(_payload(broken))
        unknown_rights = _fixture("model-a", "model", "Hero", "a" * 64, rights="public")
        with self.assertRaisesRegex(ValueError, "rights"):
            GATE.evaluate(_payload(unknown_rights))
        incomplete = _fixture("model-a", "model", "Hero", "a" * 64)
        del incomplete["provenance"]["owner"]
        with self.assertRaisesRegex(ValueError, "provenance"):
            GATE.evaluate(_payload(incomplete))
        with self.assertRaisesRegex(ValueError, "duplicate fixture id"):
            GATE.evaluate(_payload(valid, _fixture("model-a", "model", "Other", "b" * 64)))
        empty_name = _fixture("model-a", "model", "  ", "a" * 64)
        with self.assertRaisesRegex(ValueError, "displayName"):
            GATE.evaluate(_payload(empty_name))

    def test_missing_provenance_excludes_each_kind_despite_visual_result(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                attractive = {"label": "gold master", "decision": "reproducible", "score": 1}
                missing = _fixture(kind + "-missing", kind, "Look", "c" * 64, rights="permitted",
                                   provenance=None, visual=attractive)
                kept_a = _fixture(kind + "-a", kind, "Look", "a" * 64)
                kept_b = _fixture(kind + "-b", kind, "Look", "b" * 64)
                payload = _payload(kept_a, missing, kept_b)
                original = copy.deepcopy(payload)
                result = GATE.evaluate(payload)
                self.assertEqual(payload, original)
                _assert_contract(self, result)
                self.assertEqual(result["decision"], "excluded")
                self.assertIn(kind + "-missing", result["rejectedClaims"])
                self.assertEqual(_ids(result), [kind + "-a", kind + "-b"])
                self.assertEqual([item["sha256"] for item in result["preservedResults"]], ["a" * 64, "b" * 64])
                self.assertEqual({item["displayName"] for item in result["preservedResults"]}, {"Look"})
                self.assertTrue(all(item["kind"] == kind for item in result["preservedResults"]))
                self.assertNotIn(kind + "-missing", _ids(result))
                self.assertTrue(any(kind + "-missing" in question for question in result["openQuestions"]))
                text = " ".join(result["reasons"]).lower()
                self.assertIn("visual", text)
                self.assertIn("distinct", text)

    def test_unknown_or_denied_rights_excluded_with_provenance_for_each_kind(self):
        for kind in KINDS:
            for rights in ("unknown", "denied"):
                with self.subTest(kind=kind, rights=rights):
                    blocked = _fixture(kind + "-" + rights, kind, "BundleImage", "d" * 64, rights=rights,
                                       visual="publication-ready still")
                    kept = _fixture(kind + "-kept", kind, "BundleImage", "e" * 64)
                    result = GATE.evaluate(_payload(blocked, kept))
                    _assert_contract(self, result)
                    self.assertEqual(result["decision"], "excluded")
                    self.assertIn(blocked["id"], result["rejectedClaims"])
                    self.assertNotIn(blocked["id"], _ids(result))
                    self.assertEqual(_ids(result), [kept["id"]])
                    text = " ".join(result["reasons"]).lower()
                    self.assertIn("public bundle", text)
                    self.assertIn(rights, text)
                    if rights == "unknown":
                        self.assertTrue(any(blocked["id"] in question for question in result["openQuestions"]))
                    else:
                        self.assertFalse(any(blocked["id"] in question for question in result["openQuestions"]))

    def test_identical_display_names_with_different_hashes_are_both_accepted(self):
        fixtures = []
        expected = []
        for index, kind in enumerate(KINDS):
            digest_a = f"{index:02d}" + "1" * 62
            digest_b = f"{index:02d}" + "2" * 62
            fixtures.append(_fixture(kind + "-1", kind, "SharedName", digest_a))
            fixtures.append(_fixture(kind + "-2", kind, "SharedName", digest_b))
            expected.extend([kind + "-1", kind + "-2"])
        result = GATE.evaluate(_payload(*fixtures))
        _assert_contract(self, result)
        self.assertEqual(result["decision"], "accepted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], [])
        self.assertEqual(_ids(result), expected)
        names = {}
        for item in result["preservedResults"]:
            names.setdefault(item["displayName"], set()).add(item["sha256"])
        self.assertEqual(set(names), {"SharedName"})
        self.assertEqual(len(names["SharedName"]), len(KINDS) * 2)
        self.assertIn("distinct", " ".join(result["reasons"]).lower())

    def test_partial_exclusion_preserves_only_valid_ids(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                fixtures = [
                    _fixture(other + "-ok", other, other, other[0] * 64)
                    for other in KINDS if other != kind
                ]
                fixtures.append(_fixture(kind + "-bad", kind, "Shared", "f" * 64, rights="unknown",
                                         visual={"decision": "reproducible"}))
                result = GATE.evaluate(_payload(*fixtures))
                _assert_contract(self, result)
                self.assertEqual(result["decision"], "excluded")
                self.assertEqual(result["rejectedClaims"], [kind + "-bad"])
                self.assertEqual(_ids(result), [other + "-ok" for other in KINDS if other != kind])
                self.assertIn("remain preserved", " ".join(result["reasons"]))

    def test_all_excluded_when_every_fixture_lacks_provenance(self):
        fixtures = [
            _fixture(kind, kind, "Orphan", (str(index) * 64), provenance=None, rights="unknown",
                     visual="reproducible")
            for index, kind in enumerate(KINDS, start=1)
        ]
        result = GATE.evaluate(_payload(*fixtures))
        _assert_contract(self, result)
        self.assertEqual(result["decision"], "excluded")
        self.assertEqual(result["rejectedClaims"], list(KINDS))
        self.assertEqual(result["preservedResults"], [])
        self.assertGreaterEqual(len(result["openQuestions"]), len(KINDS))

    def test_same_hash_same_display_name_records_stay_separate_ids(self):
        result = GATE.evaluate(_payload(
            _fixture("one", "stock_profile", "Look", "a" * 64),
            _fixture("two", "stock_profile", "Look", "a" * 64),
        ))
        _assert_contract(self, result)
        self.assertEqual(result["decision"], "accepted")
        self.assertEqual(_ids(result), ["one", "two"])
        self.assertNotIn("distinct versions", " ".join(result["reasons"]))


if __name__ == "__main__":
    unittest.main()
