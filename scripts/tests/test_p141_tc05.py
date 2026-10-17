"""Tests for TC-P141-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p141_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p141_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def cited(asset_id, kind):
    return _GATE.production_still(
        asset_id=asset_id,
        kind=kind,
        citation=kind + " citation only",
        public_url="https://example.invalid/" + asset_id,
    )


def payload(**overrides):
    base = {
        "evidenceId": "p141-tc05",
        "repeat": "promotional images",
        "assets": [
            cited("promo-still", "image"),
            cited("commercial-lut", "lut"),
            cited("research-weights", "model"),
            _GATE.owned_thumbnail(),
        ],
    }
    base.update(overrides)
    return base


class TCP14105(unittest.TestCase):
    def assert_contract(self, result, evidence="p141-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P141-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn(_GATE.LICENCE_RULE, " ".join(result["reasons"]))
        self.assertTrue(result["reasons"])

    def test_citations_stay_and_unlicensed_bytes_stay_out(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["packagedAssetIds"], [_GATE.THUMB_ID])
        self.assertEqual(record["excludedAssetIds"], ["promo-still", "commercial-lut", "research-weights"])
        self.assertEqual(result["preservedResults"][2]["citationsRetained"], ["promo-still", "commercial-lut", "research-weights"])
        self.assertEqual(_MODULE.CASE["name"], "Publicly accessible but unlicensed asset")
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_public_visibility_is_not_a_licence(self):
        assets = [cited("promo-still", "image")]
        assets[0]["licence"] = "public web page"
        assets[0]["redistribute"] = True
        result = evaluate(payload(assets=assets))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PUBLIC_WEB_NOT_LICENCE, result["rejectedClaims"])
        self.assertIn(_GATE.PUBLIC_URL_NULL_LICENCE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIsNone(result["preservedResults"][1]["citations"][0]["licence"])
        self.assertEqual(result["preservedResults"][1]["citations"][0]["citation"], "image citation only")

    def test_redistribute_without_licence_or_attribution_is_rejected(self):
        missing_licence = cited("commercial-lut", "lut")
        missing_licence["redistribute"] = True
        missing_licence["attribution"] = "Vendor"
        result = evaluate(payload(assets=[missing_licence], repeat="commercial LUTs"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.REDISTRIBUTE_WITHOUT_LICENCE, result["rejectedClaims"])
        bare = _GATE.make_asset(asset_id="research-weights", kind="model", attribution=None)
        attributed = evaluate(payload(assets=[bare], repeat="research model weights"))
        self.assertEqual(attributed["decision"], "rejected")
        self.assertIn(_GATE.ATTRIBUTION_MISSING, attributed["rejectedClaims"])

    def test_licensed_attribution_is_recorded_and_frames_without_licence_are_not(self):
        licensed = _GATE.make_asset(asset_id="approved-profile", kind="profile")
        ok = evaluate(payload(assets=[licensed]))
        self.assertEqual(ok["decision"], "recorded")
        self.assertEqual(ok["preservedResults"][1]["redistributableAssetIds"], ["approved-profile"])
        frame = _GATE.make_asset(
            asset_id="grabbed-frame",
            kind="frame",
            licence=None,
            attribution=None,
            redistribute=False,
            bundled=True,
            citation="Frame citation",
        )
        rejected = evaluate(payload(assets=[frame]))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn(_GATE.UNLICENSED_FRAME_BUNDLED, rejected["rejectedClaims"])
        self.assertNotIn("grabbed-frame", rejected["preservedResults"][1]["packagedAssetIds"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p141-tc05-weights"
        result = evaluate(payload(evidenceId=evidence, repeat="research model weights"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(assets=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(applyNegative=True))
