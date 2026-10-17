"""Host checks for P141. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p141_manage_reference_media_rights_and_attribution",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p141_manage_reference_media_rights_and_attribution.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P141_MANAGE_REFERENCE_MEDIA_RIGHTS_AND_ATTRIBUTION.json").read_text(
            encoding="utf-8"
        )
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def with_assets(*assets):
    return document(assets=list(assets))


def rights(result):
    return result["preservedResults"][1]


class P141Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P141")
        self.assertEqual(_MODULE.WORKSTREAM, 18)
        self.assertEqual(_MODULE.TITLE, "Manage reference media rights and attribution")
        self.assertEqual(
            _MODULE.GOAL,
            "Avoid bundling copyrighted frames or proprietary look data without the required permission.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Store links and factual citations separately from distributable assets. "
            "Use owned comparison footage and approved thumbnails. Track model, profile, LUT, image, "
            "and text rights independently. Unknown redistribution status blocks packaging that asset "
            "until reviewed.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A useful production still with an accessible public URL but no permission to bundle it in the app.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The catalogue can retain a citation while excluding the image bytes from the distributable package.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Treat public web accessibility as a redistribution licence.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Content rights manifest and package licence gate")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P140",))

    def assert_contract(self, result, evidence="p141-reference-rights"):
        self.assertEqual(tuple(result), KEYS)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_MODULE.LICENCE_RULE, " ".join(result["reasons"]))
        self.assertTrue(result["reasons"])

    def test_fixture_retains_the_citation_and_excludes_the_still(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assert_contract(result)
        self.assertEqual(result["caseId"], "P141")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        record = rights(result)
        self.assertEqual(record["excludedAssetIds"], [_MODULE.STILL_ID])
        self.assertEqual(record["packagedAssetIds"], [_MODULE.THUMB_ID])
        self.assertEqual(record["redistributableAssetIds"], [_MODULE.THUMB_ID])
        self.assertEqual(record["rejectedAssetIds"], [])
        still = record["citations"][0]
        self.assertEqual(still["asset_id"], _MODULE.STILL_ID)
        self.assertEqual(still["citation"], _MODULE.STILL_CITATION)
        self.assertEqual(still["public_url"], _MODULE.STILL_URL)
        self.assertIsNone(still["licence"])
        self.assertIn("public URL with licence null is not redistributed: " + _MODULE.STILL_ID, result["reasons"])
        self.assertIn("citation retained for " + _MODULE.STILL_ID, result["reasons"])
        self.assertIn("image bytes excluded from the distributable package: " + _MODULE.STILL_ID, result["reasons"])
        self.assertIn("licensed asset with attribution recorded: " + _MODULE.THUMB_ID, result["reasons"])

    def test_evaluate_records_the_same_licence_split(self):
        result = evaluate(
            {
                "caseId": "P141",
                "evidenceId": "p141-evaluate",
                "repeat": "promotional images",
                "applyMutant": False,
                "assets": _MODULE.fixture_assets(),
            }
        )
        self.assert_contract(result, "p141-evaluate")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P141")
        self.assertEqual(rights(result)["excludedAssetIds"], [_MODULE.STILL_ID])
        self.assertIn("promotional images", result["openQuestions"])

    def test_public_url_with_null_licence_must_not_be_redistributed(self):
        still = _MODULE.production_still(redistribute=True)
        result = assess(with_assets(still))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLIC_URL_NULL_LICENCE, result["rejectedClaims"])
        self.assertIn(_MODULE.REDISTRIBUTE_WITHOUT_LICENCE, result["rejectedClaims"])
        self.assertIn(_MODULE.UNKNOWN_REDISTRIBUTION, result["rejectedClaims"])
        self.assertNotIn(_MODULE.STILL_ID, rights(result)["packagedAssetIds"])
        self.assertIn(_MODULE.STILL_ID, rights(result)["excludedAssetIds"])
        self.assertEqual(rights(result)["citations"][0]["citation"], _MODULE.STILL_CITATION)
        self.assertIsNone(rights(result)["citations"][0]["licence"])

    def test_redistribute_without_a_licence_is_rejected(self):
        asset = _MODULE.make_asset(licence=None, public_url=None, attribution="Example Archive", bundled=False)
        result = assess(with_assets(asset))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REDISTRIBUTE_WITHOUT_LICENCE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.PUBLIC_URL_NULL_LICENCE, result["rejectedClaims"])
        self.assertNotIn("licensed-asset", rights(result)["redistributableAssetIds"])

    def test_public_web_page_is_not_a_licence(self):
        for licence in ("public web page", "Public Web Page", "public-web-page", "public webpage"):
            still = _MODULE.production_still(licence=licence, attribution="Someone")
            result = assess(with_assets(still))
            self.assertEqual(result["decision"], "rejected", licence)
            self.assertIn(_MODULE.PUBLIC_WEB_NOT_LICENCE, result["rejectedClaims"])
            self.assertIn(_MODULE.MUTANT, " ".join(result["reasons"]))
            self.assertIsNone(rights(result)["citations"][0]["licence"])
            self.assertNotIn(_MODULE.STILL_ID, rights(result)["packagedAssetIds"])
        url_licence = _MODULE.make_asset(licence="https://example.invalid/still", bundled=False, redistribute=False)
        result = assess(with_assets(url_licence))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLIC_WEB_NOT_LICENCE, result["rejectedClaims"])

    def test_missing_attribution_while_redistributing_is_rejected(self):
        asset = _MODULE.make_asset(attribution=None)
        result = assess(with_assets(asset))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ATTRIBUTION_MISSING, result["rejectedClaims"])
        self.assertNotIn(_MODULE.REDISTRIBUTE_WITHOUT_LICENCE, result["rejectedClaims"])
        self.assertNotIn("licensed-asset", rights(result)["redistributableAssetIds"])
        self.assertEqual(rights(result)["citations"][0]["licence"], "cc-by-4.0")

    def test_licence_and_attribution_can_be_recorded(self):
        asset = _MODULE.make_asset(kind="lut", asset_id="commercial-lut")
        result = assess(with_assets(asset))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(rights(result)["packagedAssetIds"], ["commercial-lut"])
        self.assertEqual(rights(result)["redistributableAssetIds"], ["commercial-lut"])
        self.assertEqual(rights(result)["citations"][0]["licence"], "cc-by-4.0")
        self.assertEqual(rights(result)["citations"][0]["attribution"], "Example Archive")

    def test_frames_without_a_licence_are_not_bundled(self):
        frame = _MODULE.make_asset(
            asset_id="grabbed-frame",
            kind="frame",
            licence=None,
            attribution=None,
            redistribute=False,
            bundled=True,
            citation="Frame cited only",
        )
        rejected = assess(with_assets(frame))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn(_MODULE.UNLICENSED_FRAME_BUNDLED, rejected["rejectedClaims"])
        self.assertIn(_MODULE.UNLICENSED_BYTES_BUNDLED, rejected["rejectedClaims"])
        self.assertNotIn("grabbed-frame", rights(rejected)["packagedAssetIds"])
        self.assertIn("citation retained for grabbed-frame", rejected["reasons"])
        held = _MODULE.make_asset(
            asset_id="grabbed-frame",
            kind="frame",
            licence=None,
            attribution=None,
            redistribute=False,
            bundled=False,
            citation="Frame cited only",
            public_url=None,
        )
        recorded = assess(with_assets(held))
        self.assertEqual(recorded["decision"], "recorded")
        self.assertIn("frame lacking a licence is not bundled: grabbed-frame", recorded["reasons"])
        self.assertIn("grabbed-frame", rights(recorded)["excludedAssetIds"])

    def test_sibling_licence_does_not_cover_an_unlicensed_asset(self):
        lut = _MODULE.make_asset(asset_id="commercial-lut", kind="lut")
        image = _MODULE.production_still(asset_id="promo-still", bundled=True)
        profile = _MODULE.make_asset(
            asset_id="camera-profile",
            kind="profile",
            licence=None,
            attribution=None,
            redistribute=False,
            bundled=False,
            citation="Profile citation only",
        )
        text = _MODULE.make_asset(asset_id="caption", kind="text", licence="owned-text", bundled=True)
        model = _MODULE.make_asset(
            asset_id="research-weights",
            kind="model",
            licence=None,
            attribution=None,
            redistribute=True,
            bundled=True,
            public_url="https://example.invalid/weights",
            citation="Research weights citation",
        )
        result = assess(with_assets(lut, image, profile, text, model))
        self.assertEqual(result["decision"], "rejected")
        record = rights(result)
        self.assertEqual(record["packagedAssetIds"], ["commercial-lut", "caption"])
        self.assertIn("promo-still", record["excludedAssetIds"])
        self.assertIn("camera-profile", record["excludedAssetIds"])
        self.assertIn("research-weights", record["rejectedAssetIds"])
        self.assertNotIn("promo-still", record["packagedAssetIds"])
        self.assertIn(_MODULE.PUBLIC_URL_NULL_LICENCE, result["rejectedClaims"])
        kinds = {item["asset_id"]: item["kind"] for item in record["citations"]}
        self.assertEqual(kinds["research-weights"], "model")
        self.assertEqual(kinds["commercial-lut"], "lut")
        self.assertIsNone(next(item["licence"] for item in record["citations"] if item["asset_id"] == "promo-still"))

    def test_mutant_flag_is_rejected_and_evidence_remains(self):
        result = assess(document(applyMutant=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PUBLIC_WEB_NOT_LICENCE, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn(_MODULE.STILL_ID, rights(result)["excludedAssetIds"])
        self.assertEqual(rights(result)["citations"][0]["citation"], _MODULE.STILL_CITATION)

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(schemaVersion=True),
            document(phase="P142"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            with_assets(),
            with_assets(_MODULE.production_still(licence="")),
            with_assets(_MODULE.production_still(licence=" public web page")),
            with_assets(_MODULE.make_asset(redistribute="yes")),
            with_assets(_MODULE.make_asset(kind="LUT")),
            with_assets(_MODULE.make_asset(attribution=" ")),
            with_assets(_MODULE.production_still(), _MODULE.production_still(asset_id=_MODULE.STILL_ID)),
            with_assets(_MODULE.make_asset(public_url="")),
            {"caseId": "P141"},
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    if isinstance(payload, dict) and "caseId" in payload and "phase" not in payload:
                        evaluate(payload)
                    else:
                        assess(payload)

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P141-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P141")
        self.assertEqual(handoff["nextPhase"], "P142")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(handoff["nonClaims"], "Host reference only. Not a physical S23 qualification.")
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p141*.py' -v",
        )
        note = (_ROOT / "docs" / "P141_MANAGE_REFERENCE_MEDIA_RIGHTS_AND_ATTRIBUTION.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Content rights manifest and package licence gate", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("public web page", note)
        self.assertIn(_MODULE.LICENCE_RULE, note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p141_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p141_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P141-0{index}")
            self.assertEqual(module.CASE["phase"], "P141")
            self.assertEqual(module.CASE["workstream"], 18)
            with self.assertRaises(ValueError):
                module.evaluate({})
