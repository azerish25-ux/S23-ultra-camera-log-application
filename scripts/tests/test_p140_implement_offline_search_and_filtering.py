"""Host checks for P140. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p140_implement_offline_search_and_filtering",
    Path(__file__).resolve().parents[1] / "gates" / "p140_implement_offline_search_and_filtering.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P140_IMPLEMENT_OFFLINE_SEARCH_AND_FILTERING.json").read_text(encoding="utf-8")
    )


def search_payload(**overrides):
    document = _MODULE.fixture_document()
    value = {
        "evidenceId": document["evidenceId"],
        "repeat": "format",
        "claim": document["claim"],
        "applyMutant": False,
        "remote_model": False,
        "network_used": False,
        "catalogue": document["catalogue"],
        "query": document["query"],
        "filters": document["filters"],
        "typoTolerance": document["typoTolerance"],
        "sort": document["sort"],
        "dropQueryTokens": False,
        "recommendationIds": [],
    }
    value.update(overrides)
    return value


def trace_of(result):
    return result["preservedResults"][1]


class P140Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P140")
        self.assertEqual(_MODULE.WORKSTREAM, 18)
        self.assertEqual(_MODULE.TITLE, "Implement offline search and filtering")
        self.assertEqual(
            _MODULE.GOAL,
            "Make the catalogue useful without network dependence or opaque recommendation behavior.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Index titles, alternate titles, stock names, formats, scene families, and evidence quality. "
            "Support typo-tolerant discovery with explicit matching behavior. Keep local user recipes "
            "private and allow sorting by relevant technical criteria rather than invented popularity.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A search for a misspelled film title while the phone is offline and a filter for "
            "monochrome large-format recipes.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The correct local candidates appear with their evidence status and no network request "
            "is required.",
        )
        self.assertEqual(_MODULE.MUTANT, "Call a remote language model for every catalogue search.")
        self.assertEqual(_MODULE.DELIVERABLE, "Offline search index and deterministic retrieval tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P139",))
        self.assertIn("every query token", _MODULE.RETRIEVAL_RULE)
        self.assertIn("remote_model true or network_used true is rejected", _MODULE.RETRIEVAL_RULE)

    def test_fixture_records_the_local_monochrome_candidate(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P140")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.RETRIEVAL_RULE, " ".join(result["reasons"]))
        trace = trace_of(result)
        self.assertEqual(trace["ids"], ["night-hunter-lf"])
        self.assertEqual(trace["repeatedIds"], ["night-hunter-lf"])
        self.assertEqual(trace["queryTokens"], ["nigt", "hunter"])
        self.assertEqual(trace["matches"][0]["evidenceStatus"], "partial")
        self.assertEqual(trace["matches"][0]["matchedTokens"][0], {"query": "nigt", "indexed": "night", "distance": 1})
        self.assertEqual(trace["matches"][0]["matchedTokens"][1], {"query": "hunter", "indexed": "hunter", "distance": 0})
        self.assertFalse(trace["remoteCall"])
        self.assertFalse(trace["networkUsed"])
        self.assertFalse(trace["recommendationList"])
        self.assertTrue(trace["queryTokensPreserved"])
        self.assertIn("river-day-lf", trace["filterOnlyIds"])
        self.assertNotIn("river-day-lf", trace["ids"])
        self.assertEqual(trace["privateExcluded"], ["user-night-grade"])
        self.assertEqual(trace["sortedBy"], "id")

    def test_exact_tokens_are_lowercase_and_require_every_token(self):
        catalogue = _MODULE.fixture_catalogue()
        index = _MODULE.build_token_index(catalogue)
        self.assertEqual(_MODULE.query_tokens("Night, HUNTER night!"), ["night", "hunter"])
        first = _MODULE.retrieve(index, "NIGHT hunter", {"monochrome": True, "formats": "large-format"})
        second = _MODULE.retrieve(index, "hunter night", {"formats": "large-format", "monochrome": True})
        self.assertEqual(first, ["night-hunter-lf"])
        self.assertEqual(first, second)
        self.assertEqual(_MODULE.retrieve(index, "nigt hunter"), [])
        self.assertEqual(_MODULE.retrieve(index, "hunter"), ["night-hunter-35", "night-hunter-lf"])
        self.assertNotIn("user-night-grade", _MODULE.retrieve(index, "hunter"))
        mutated = _MODULE.retrieve(index, "fleuve")
        mutated.append("injected")
        self.assertEqual(_MODULE.retrieve(index, "fleuve"), ["river-day-lf"])

    def test_id_and_text_are_indexed_but_field_names_are_not(self):
        index = _MODULE.build_token_index([
            {"id": "zz-unique-token", "title": "Hello"},
            {"id": "aa-other", "title": "Brass"},
        ])
        self.assertEqual(_MODULE.retrieve(index, "UNIQUE"), ["zz-unique-token"])
        self.assertEqual(_MODULE.retrieve(index, "hello brass"), [])
        self.assertEqual(_MODULE.retrieve(index, "title"), [])
        self.assertEqual(_MODULE.retrieve(index, "brass hello"), [])
        self.assertEqual(_MODULE.retrieve(index, "hello"), ["zz-unique-token"])
        self.assertEqual(_MODULE.retrieve(index, "brass"), ["aa-other"])

    def test_same_query_twice_and_technical_sort_are_deterministic(self):
        catalogue = [
            {"id": "m-popular", "title": "Stock", "evidenceQuality": "preference", "evidenceStatus": "preference", "popularity": 100},
            {"id": "a-sourced", "title": "Stock", "evidenceQuality": "documented", "evidenceStatus": "documented", "popularity": 1},
        ]
        index = _MODULE.build_token_index(catalogue)
        self.assertEqual(_MODULE.retrieve(index, "stock"), ["a-sourced", "m-popular"])
        self.assertEqual(
            _MODULE.retrieve(index, "stock", sort="evidenceQuality"),
            ["a-sourced", "m-popular"],
        )
        result = evaluate(search_payload(
            catalogue=catalogue,
            query="stock",
            filters={},
            typoTolerance=0,
            sort="popularity",
            repeat="popularity",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.POPULARITY_SORT, result["rejectedClaims"])
        self.assertEqual(trace_of(result)["ids"], ["a-sourced", "m-popular"])
        self.assertEqual(trace_of(result)["sortedBy"], "id")
        self.assertNotEqual(trace_of(result)["ids"], ["m-popular", "a-sourced"])

    def test_remote_model_network_and_mutant_are_rejected(self):
        for flag in ("remote_model", "network_used"):
            result = assess(_MODULE.fixture_document() | {flag: True})
            self.assertEqual(result["decision"], "rejected", flag)
            self.assertNotIn(result["decision"], {"qualified", "allowed"})
            self.assertIn("p140-offline-search", result["preservedResults"])
            self.assertFalse(trace_of(result)["remoteCall"])
            self.assertEqual(trace_of(result)["ids"], ["night-hunter-lf"])
        remote = assess(_MODULE.fixture_document() | {"remote_model": True})
        self.assertIn(_MODULE.MUTANT, remote["rejectedClaims"])
        self.assertIn(_MODULE.REMOTE_MODEL, remote["rejectedClaims"])
        networked = assess(_MODULE.fixture_document() | {"network_used": True})
        self.assertIn(_MODULE.NETWORK_USED, networked["rejectedClaims"])
        self.assertNotIn(_MODULE.MUTANT, networked["rejectedClaims"])
        mutant = assess(_MODULE.fixture_document() | {"applyMutant": True})
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn(_MODULE.MUTANT, mutant["rejectedClaims"])
        self.assertIn("p140-offline-search", mutant["preservedResults"])

    def test_filter_does_not_drop_query_tokens(self):
        result = evaluate(search_payload(query="hunter", typoTolerance=0, filters={"monochrome": True}, dropQueryTokens=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DROPPED_TOKENS, result["rejectedClaims"])
        trace = trace_of(result)
        self.assertEqual(trace["queryTokens"], ["hunter"])
        self.assertEqual(trace["ids"], ["night-hunter-lf"])
        self.assertIn("river-day-lf", trace["filterOnlyIds"])
        self.assertNotIn("river-day-lf", trace["ids"])
        self.assertTrue(trace["queryTokensPreserved"])

    def test_empty_query_is_explicit_and_not_a_recommendation(self):
        result = evaluate(search_payload(query="   ", filters={"monochrome": True}, recommendationIds=[]))
        self.assertEqual(result["decision"], "recorded")
        trace = trace_of(result)
        self.assertEqual(trace["ids"], [])
        self.assertEqual(trace["repeatedIds"], [])
        self.assertEqual(trace["queryTokens"], [])
        self.assertTrue(trace["explicitEmpty"])
        self.assertFalse(trace["remoteCall"])
        self.assertFalse(trace["networkUsed"])
        self.assertFalse(trace["recommendationList"])
        self.assertEqual(trace["filterOnlyIds"], [])
        recommended = evaluate(search_payload(query="", recommendationIds=["river-day-lf"], filters={"monochrome": True}))
        self.assertEqual(recommended["decision"], "rejected")
        self.assertIn(_MODULE.EMPTY_RECOMMENDATION, recommended["rejectedClaims"])
        self.assertEqual(trace_of(recommended)["ids"], [])
        self.assertNotIn("river-day-lf", trace_of(recommended)["ids"])
        self.assertIn("p140-offline-search", recommended["preservedResults"])

    def test_evidence_sort_prefers_documented_over_popularity(self):
        catalogue = [
            {"id": "a-popular", "title": "Recipe stock", "evidenceQuality": "preference", "evidenceStatus": "preference", "popularity": 99},
            {"id": "z-sourced", "title": "Recipe stock", "evidenceQuality": "documented", "evidenceStatus": "documented", "popularity": 1},
        ]
        result = evaluate(search_payload(
            catalogue=catalogue,
            query="RECIPE",
            filters={},
            typoTolerance=0,
            sort="evidenceQuality",
        ))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(trace_of(result)["ids"], ["z-sourced", "a-popular"])
        self.assertEqual(trace_of(result)["sortedBy"], "evidenceQuality")
        self.assertEqual(trace_of(result)["matches"][0]["evidenceStatus"], "documented")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess([])
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            assess(_MODULE.fixture_document() | {"phase": "P141"})
        with self.assertRaises(ValueError):
            assess(_MODULE.fixture_document() | {"implementationBaseRevision": "deadbeef"})
        with self.assertRaises(ValueError):
            evaluate(search_payload(typoTolerance=True))
        with self.assertRaises(ValueError):
            evaluate(search_payload(remote_model="yes"))
        with self.assertRaises(ValueError):
            _MODULE.build_token_index([{"id": "a", "title": "A"}, {"id": "a", "title": "B"}])
        with self.assertRaises(ValueError):
            _MODULE.retrieve(_MODULE.build_token_index([]), "night", sort="popularity")
