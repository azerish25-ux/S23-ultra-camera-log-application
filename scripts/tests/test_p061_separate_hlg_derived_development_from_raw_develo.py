"""Host checks for the P061 source normalization router. Not a physical S23 probe.

TC-P061-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p061_separate_hlg_derived_development_from_raw_develo import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    FORBIDDEN_PROMOTION,
    FRAME_ID,
    HOST_LIMIT,
    INVERSE_CURVE,
    MAP_ID,
    METHOD,
    MUTANT,
    ONE_INVERSE,
    ORACLE,
    assess,
    classify,
    validate_document,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def load_document() -> dict:
    path = ROOT / "docs" / "P061_SEPARATE_HLG_DERIVED_DEVELOPMENT_FROM_RAW_DEVELO.json"
    return json.loads(path.read_text(encoding="utf-8"))


class P061RouterTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P061")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-source-normalization-router-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("upstream ISP processing may not be invertible", METHOD)
        self.assertIn("Do not invent missing scene values from flattened SDR", METHOD)
        self.assertEqual(
            FIXTURE,
            "The same visible frame supplied as declared HLG, SDR, and an untagged imported video.",
        )
        self.assertEqual(
            ORACLE,
            "Each path receives its correct or explicitly unresolved interpretation; "
            "none is silently promoted to RAW-derived Log.",
        )
        self.assertEqual(MUTANT, "Apply one inverse curve to every source regardless of metadata.")
        self.assertEqual(FRAME_ID, "same-visible-frame")
        self.assertEqual(INVERSE_CURVE, "display-to-scene-guess")
        self.assertEqual(FORBIDDEN_PROMOTION, "RAW-derived-Log")

    def test_fixture_routes_hlg_sdr_and_untagged_without_one_inverse(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P061")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        codes = {item["visibleCode"] for item in raw["sources"]}
        self.assertEqual(codes, {"0.5"})
        self.assertEqual(
            [classify(item) for item in raw["sources"]],
            ["hlg-derived", "sdr-derived", "unresolved"],
        )
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "routed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("interpretation:declared-hlg:hlg-derived", result["preservedResults"])
        self.assertIn("interpretation:declared-sdr:sdr-derived", result["preservedResults"])
        self.assertIn("interpretation:untagged-import:unresolved", result["preservedResults"])
        self.assertIn("recipe:declared-hlg:isp-processed-hlg", result["preservedResults"])
        self.assertIn("output:declared-hlg:hlg-derived:isp-processed-hlg", result["preservedResults"])
        self.assertIn("recipe:declared-sdr:isp-processed-sdr", result["preservedResults"])
        self.assertIn("output:declared-sdr:sdr-derived:isp-processed-sdr", result["preservedResults"])
        self.assertIn("scene:declared-sdr:not-invented", result["preservedResults"])
        self.assertIn("scene-values:not-invented", result["preservedResults"])
        self.assertIn("inverse:not-applied", result["preservedResults"])
        self.assertIn("decoded:declared-hlg:HLG:Rec.2020:video", result["preservedResults"])
        self.assertIn("decoded:untagged-import:unknown:unknown:unknown", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertNotIn("RAW-derived-Log", " ".join(result["preservedResults"]))
        self.assertFalse(any(item.startswith("attempted:") for item in result["preservedResults"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_mutant_one_inverse_is_rejected_and_keeps_the_inventory(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, route=ONE_INVERSE)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "routed")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(
            mutant["rejectedClaims"],
            ["one-inverse-curve", "silent-raw-log-promotion"],
        )
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "routed"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("decoded:declared-hlg:HLG:Rec.2020:video", mutant["preservedResults"])
        self.assertIn("decoded:declared-sdr:Rec.709:Rec.709:video", mutant["preservedResults"])
        self.assertIn(
            "source:declared-hlg:HLG:HLG:Rec.2020:video:isp-processed-hlg",
            mutant["preservedResults"],
        )
        self.assertIn(
            "source:declared-sdr:SDR:Rec.709:Rec.709:video:isp-processed-sdr",
            mutant["preservedResults"],
        )
        self.assertIn(
            "source:untagged-import:untagged:unknown:unknown:unknown:imported-video",
            mutant["preservedResults"],
        )
        self.assertIn("attempted:declared-hlg:RAW-derived-Log", mutant["preservedResults"])
        self.assertIn("attempted:declared-sdr:RAW-derived-Log", mutant["preservedResults"])
        self.assertIn("attempted:untagged-import:RAW-derived-Log", mutant["preservedResults"])
        self.assertIn("inverse:display-to-scene-guess:declared-hlg", mutant["preservedResults"])
        self.assertIn("scene:declared-sdr:invented", mutant["preservedResults"])
        self.assertNotIn("inverse:not-applied", mutant["preservedResults"])
        self.assertNotIn("interpretation:declared-hlg:hlg-derived", mutant["preservedResults"])
        prefix = [
            item
            for item in honest["preservedResults"]
            if item.startswith(("source:", "frame:", "visible:", "decoded:", "isp-invertible:"))
        ]
        for item in prefix:
            self.assertIn(item, mutant["preservedResults"])

    def test_contradictory_hlg_transfer_keeps_the_other_sources(self) -> None:
        raw = load_document()
        raw["sources"][0]["transfer"] = "Rec.709"
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("contradictory:declared-hlg", result["rejectedClaims"])
        self.assertIn("interpretation:declared-sdr:sdr-derived", result["preservedResults"])
        self.assertIn("interpretation:untagged-import:unresolved", result["preservedResults"])
        self.assertIn("interpretation:declared-hlg:contradictory", result["preservedResults"])
        self.assertIn("scene:declared-sdr:not-invented", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "routed"})

    def test_claimed_isp_invertibility_is_rejected(self) -> None:
        raw = load_document()
        raw["sources"][1]["ispInvertible"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("contradictory:declared-sdr", result["rejectedClaims"])
        self.assertIn("isp-invertible:declared-sdr:true", result["preservedResults"])
        self.assertIn(
            "source:declared-hlg:HLG:HLG:Rec.2020:video:isp-processed-hlg",
            result["preservedResults"],
        )
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["sources"]
        short = copy.deepcopy(valid)
        short["sources"] = short["sources"][:2]
        code = copy.deepcopy(valid)
        code["sources"][2]["visibleCode"] = "0.25"
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P060"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            short,
            code,
            bad_phase,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, route="qualified")


if __name__ == "__main__":
    unittest.main()
