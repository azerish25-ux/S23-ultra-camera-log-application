"""Host checks for P155. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p155_evaluate_reversible_application_level_alternatives",
    Path(__file__).resolve().parents[1] / "gates" / "p155_evaluate_reversible_application_level_alternatives.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P155_EVALUATE_REVERSIBLE_APPLICATION_LEVEL_ALTERNATIVES.json").read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def alt(name, tried, result):
    return {"name": name, "tried": tried, "result": result}


class P155Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P155")
        self.assertEqual(_MODULE.WORKSTREAM, 20)
        self.assertEqual(_MODULE.TITLE, "Evaluate reversible application-level alternatives")
        self.assertEqual(_MODULE.GOAL, "Exhaust useful normal-app approaches before escalating risk.")
        self.assertEqual(
            _MODULE.METHOD,
            "Compare alternate stream combinations, smaller source sizes, different codec "
            "interfaces, deferred development, CPU-GPU scheduling, and retained RAW workflows. "
            "Measure the information and quality tradeoffs. Keep each alternative honestly "
            "labelled by source lineage.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A surface-only ten-bit encoder that could support a qualified GPU route even "
            "though the P010 Image developer is unavailable.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The plan explores that interface before declaring the sensor-to-Log goal impossible.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Treat failure of one codec input interface as proof that every ten-bit path is unavailable.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Alternative-path experiments and comparative decision")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P154",))
        self.assertEqual(_MODULE.SLUG, "evaluate_reversible_application_level_alternatives")
        self.assertIn("explicitly left untested", _MODULE.COMPARATIVE_RULE)
        self.assertIn("one codec interface", _MODULE.COMPARATIVE_RULE)
        self.assertIn("untested", _MODULE.COMPARATIVE_RULE)
        self.assertIn("never qualified", _MODULE.COMPARATIVE_RULE)

    def test_fixture_explores_the_surface_encoder_without_smearing(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P155")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertIn("physical S23 not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.COMPARATIVE_RULE, " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        by_name = {row["name"]: row for row in snapshot["alternatives"]}
        self.assertEqual(by_name["p010-image"]["result"], "unavailable")
        self.assertEqual(by_name["surface-ten-bit-encoder"]["result"], "available")
        self.assertEqual(by_name["smaller-source-sizes"]["result"], "untested")
        self.assertEqual(by_name["smaller-source-sizes"]["labelling"], "explicitly-untested")
        self.assertEqual(by_name["smaller-source-sizes"]["information"], "unknown")
        self.assertEqual(by_name["surface-ten-bit-encoder"]["sourceLineage"], "surface-ten-bit-encoder")
        self.assertFalse(snapshot["spreadApplied"])
        self.assertFalse(snapshot["allTenBitPathsUnavailable"])
        self.assertTrue(snapshot["conclusionMatches"])
        self.assertGreater(snapshot["codecFailureCount"], 0)
        self.assertGreater(snapshot["availableCount"], 0)
        self.assertGreater(snapshot["untestedCount"], 0)
        spread = _MODULE.spread_one_codec_failure(source["alternatives"])
        self.assertTrue(all(row["result"] == "unavailable" for row in spread))
        self.assertNotEqual(
            [row["result"] for row in snapshot["alternatives"]],
            [row["result"] for row in spread],
        )
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_untested_alternative_rejects_all_ten_bit_unavailable(self):
        result = assess(document(conclusion=_MODULE.ALL_TEN_BIT_UNAVAILABLE))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.UNTESTED_BLOCKS_ALL_UNAVAILABLE, result["rejectedClaims"])
        self.assertIn(_MODULE.ONE_CODEC_MARKS_ALL, result["rejectedClaims"])
        self.assertIn(_MODULE.CONCLUSION_MISMATCH, result["rejectedClaims"])
        self.assertIn("p155-reversible-alternatives", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["alternatives"][3]["result"], "available")
        self.assertFalse(result["preservedResults"][1]["spreadApplied"])
        self.assertIn("untested", " ".join(result["reasons"]))

    def test_one_codec_failure_does_not_mark_every_path_unavailable(self):
        rows = [
            alt("p010-image", True, "unavailable"),
            alt("surface-ten-bit-encoder", True, "available"),
        ]
        result = assess(document(alternatives=rows, conclusion=_MODULE.ALL_TEN_BIT_UNAVAILABLE))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ONE_CODEC_MARKS_ALL, result["rejectedClaims"])
        self.assertNotIn(_MODULE.UNTESTED_BLOCKS_ALL_UNAVAILABLE, result["rejectedClaims"])
        published = result["preservedResults"][1]["alternatives"]
        self.assertEqual(published[1]["result"], "available")
        self.assertEqual(published[1]["information"], "retained")
        self.assertFalse(result["preservedResults"][1]["allTenBitPathsUnavailable"])
        matched = assess(document(alternatives=rows, conclusion=_MODULE.TEN_BIT_PATH_AVAILABLE))
        self.assertEqual(matched["decision"], "recorded")
        self.assertEqual(matched["rejectedClaims"], [])
        still_open = assess(document(alternatives=rows, conclusion=_MODULE.NOT_IMPOSSIBLE))
        self.assertEqual(still_open["decision"], "recorded")

    def test_single_failed_interface_is_not_every_ten_bit_path(self):
        rows = [alt("p010-image", True, "unavailable")]
        result = assess(document(alternatives=rows, conclusion=_MODULE.ALL_TEN_BIT_UNAVAILABLE))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ONE_CODEC_MARKS_ALL, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        honest = assess(document(alternatives=rows, conclusion=_MODULE.NOT_IMPOSSIBLE))
        self.assertEqual(honest["decision"], "recorded")
        self.assertFalse(honest["preservedResults"][1]["allTenBitPathsUnavailable"])

    def test_every_tried_path_unavailable_can_be_recorded(self):
        rows = [
            alt("p010-image", True, "unavailable"),
            alt("surface-ten-bit-encoder", True, "unavailable"),
            alt("retained-raw-workflows", True, "unavailable"),
        ]
        result = assess(document(alternatives=rows, conclusion=_MODULE.ALL_TEN_BIT_UNAVAILABLE))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["allTenBitPathsUnavailable"])
        self.assertTrue(result["preservedResults"][1]["conclusionMatches"])
        contradicted = assess(document(alternatives=rows, conclusion=_MODULE.NOT_IMPOSSIBLE))
        self.assertEqual(contradicted["decision"], "rejected")
        self.assertIn(_MODULE.CONCLUSION_MISMATCH, contradicted["rejectedClaims"])
        self.assertNotIn(_MODULE.ONE_CODEC_MARKS_ALL, contradicted["rejectedClaims"])

    def test_inconsistent_labelling_is_not_a_comparative_decision(self):
        tried_untested = [
            alt("p010-image", True, "unavailable"),
            alt("surface-ten-bit-encoder", True, "untested"),
        ]
        result = assess(document(alternatives=tried_untested, conclusion=_MODULE.NOT_IMPOSSIBLE))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PATH_NOT_LABELLED, result["rejectedClaims"])
        self.assertIn(_MODULE.CONCLUSION_MISMATCH, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["alternatives"][1]["labelling"], "invalid")
        untried_available = [alt("smaller-source-sizes", False, "available")]
        other = assess(document(alternatives=untried_available, conclusion=_MODULE.TEN_BIT_PATH_AVAILABLE))
        self.assertEqual(other["decision"], "rejected")
        self.assertIn(_MODULE.PATH_NOT_LABELLED, other["rejectedClaims"])

    def test_explicitly_untested_paths_can_remain_open(self):
        rows = [
            alt("p010-image", True, "unavailable"),
            alt("surface-ten-bit-encoder", False, "untested"),
            alt("cpu-gpu-scheduling", False, "untested"),
        ]
        result = assess(document(alternatives=rows, conclusion=_MODULE.UNTESTED_REMAIN))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["untestedCount"], 2)
        self.assertEqual(result["preservedResults"][1]["alternatives"][1]["quality"], "unknown")
        blocked = assess(document(alternatives=rows, conclusion=_MODULE.ALL_TEN_BIT_UNAVAILABLE))
        self.assertEqual(blocked["decision"], "rejected")
        self.assertIn(_MODULE.UNTESTED_BLOCKS_ALL_UNAVAILABLE, blocked["rejectedClaims"])

    def test_apply_mutant_rejects_without_rewriting_results(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ONE_CODEC_MARKS_ALL, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("p155-reversible-alternatives", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        by_name = {row["name"]: row for row in result["preservedResults"][1]["alternatives"]}
        self.assertEqual(by_name["surface-ten-bit-encoder"]["result"], "available")
        self.assertFalse(result["preservedResults"][1]["spreadApplied"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P156"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(alternatives=[]),
            document(conclusion=""),
            document(alternatives=[alt("p010-image", True, "qualified")]),
            document(alternatives=[alt("p010-image", 1, "unavailable")]),
            document(alternatives=[
                alt("p010-image", True, "unavailable"),
                alt("p010-image", True, "available"),
            ]),
            document(alternatives=[{"name": "p010-image", "tried": True}]),
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate({"evidenceId": "x"})

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P155-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P155")
        self.assertEqual(handoff["nextPhase"], "P156")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p155*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P155_EVALUATE_REVERSIBLE_APPLICATION_LEVEL_ALTERNATIVES.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Alternative-path experiments and comparative decision", note)
        self.assertIn("physical S23 not run", note)
        self.assertIn("one codec", note.lower())
        self.assertIn("untested", note)
        self.assertIn("explicitly left untested", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)
