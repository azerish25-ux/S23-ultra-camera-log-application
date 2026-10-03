"""Host checks for the P012 dynamic-range profile planner. Not a physical S23 probe.

TC-P012-01..08 are specified in their own modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p012_discover_dynamic_range_profiles import (  # noqa: E402
    BASE_REVISION,
    CATEGORY_LABELS,
    FIXTURE,
    METHOD,
    MUTANT,
    MUTANT_REJECTION,
    ORACLE,
    PLANNER_ID,
    assess,
    inventory,
    validate_planner,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
PRESERVED = [
    "3840x2160:HLG@hlg-record",
    "1920x1080:SDR@sdr-preview",
    "3840x2160:HDR10@hdr10-surface",
    "4000x3000:RAW_LOG@raw-log",
    "1280x720:SDR@sdr-monitor",
    "1920x1080:HLG@hlg-preview-unreadable",
    "latency:hlg-record:8000000",
    "latency:hdr10-surface:12000000",
]
QUESTIONS = [
    "optionalCodecQuery query failed; unrelated routes were retained",
    "route hlg-preview-unreadable query error retained: dynamicRangeProfiles",
    "additional latency not exposed for sdr-preview",
    "additional latency not exposed for raw-log",
    "additional latency not exposed for sdr-monitor",
    "additional latency not exposed for hlg-preview-unreadable",
    "sensor-derived Log is not established by a RAW-derived Log label",
]


def load_planner() -> dict:
    return json.loads(
        (ROOT / "docs" / "P012_DISCOVER_DYNAMIC_RANGE_PROFILES.json").read_text(encoding="utf-8")
    )


def route(**overrides) -> dict:
    value = {
        "routeId": "sdr-a",
        "role": "preview",
        "profile": "SDR",
        "category": "SDR",
        "tenBit": False,
        "supported": True,
        "width": 1920,
        "height": 1080,
        "format": "YUV_420_888",
        "queryError": None,
        "additionalLatencyNs": None,
    }
    value.update(overrides)
    return value


def document(routes: list[dict], **overrides) -> dict:
    value = {
        "schemaVersion": 1,
        "phase": "P012",
        "plannerId": PLANNER_ID,
        "implementationBaseRevision": BASE_REVISION,
        "method": METHOD,
        "fixture": FIXTURE,
        "oracle": ORACLE,
        "mutant": MUTANT,
        "tenBitCapable": True,
        "failedProperties": [],
        "routes": routes,
        "constraints": [],
    }
    value.update(overrides)
    return value


class P012DiscoverDynamicRangeProfilesTests(unittest.TestCase):
    def assert_contract(self, result: dict) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P012")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"rejected", "withheld", "candidate", "independent_monitor"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertTrue(result["preservedResults"])

    def test_fixture_encodes_method_fixture_oracle_and_mutant(self) -> None:
        raw = load_planner()
        self.assertIsNone(validate_planner(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P012")
        self.assertEqual(raw["plannerId"], PLANNER_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertIs(raw["tenBitCapable"], True)
        self.assertEqual(raw["failedProperties"], ["optionalCodecQuery"])
        self.assertEqual(
            raw["constraints"],
            [{
                "constraintId": "hlg-rejects-sdr-preview",
                "kind": "same_request_rejected",
                "members": ["hlg-record", "sdr-preview"],
                "reason": "HLG-capable route rejects an SDR preview in the same capture request",
            }],
        )
        self.assertIn("HLG", METHOD)
        self.assertIn("RAW-derived Log", METHOD)
        self.assertIn("pairwise", METHOD)
        self.assertIn("latency", METHOD)

    def test_categories_stay_separate_and_a_failed_query_does_not_erase_routes(self) -> None:
        raw = load_planner()
        rows = inventory(raw)
        self.assertEqual(len(rows), len(raw["routes"]))
        self.assertEqual([row["routeId"] for row in rows], [route["routeId"] for route in raw["routes"]])
        labels = {row["category"]: row["categoryLabel"] for row in rows}
        self.assertEqual(labels, CATEGORY_LABELS)
        self.assertEqual(set(CATEGORY_LABELS.values()), {"HLG", "HDR10", "SDR", "RAW-derived Log"})
        self.assertEqual(len(set(CATEGORY_LABELS.values())), 4)
        self.assertNotEqual(labels["RAW_LOG"], labels["HLG"])
        self.assertNotEqual(labels["RAW_LOG"], labels["SDR"])
        self.assertNotEqual(labels["HDR10"], labels["HLG"])
        failed = next(row for row in rows if row["routeId"] == "hlg-preview-unreadable")
        self.assertEqual(failed["queryError"], "dynamicRangeProfiles")
        self.assertEqual(failed["identity"], "1920x1080:HLG@hlg-preview-unreadable")
        hlg = next(row for row in rows if row["routeId"] == "hlg-record")
        sdr = next(row for row in rows if row["routeId"] == "sdr-preview")
        self.assertEqual(hlg["additionalLatencyNs"], 8000000)
        self.assertIsNone(sdr["additionalLatencyNs"])
        self.assertIs(hlg["tenBit"], True)
        self.assertIs(sdr["tenBit"], False)

    def test_hlg_recording_rejects_sdr_preview_in_the_same_request(self) -> None:
        raw = load_planner()
        before = copy.deepcopy(raw)
        result = assess(raw, ["hlg-record", "sdr-preview"], None)
        self.assertEqual(raw, before)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertEqual(result["openQuestions"], QUESTIONS)
        self.assertEqual(result["rejectedClaims"], [
            "3840x2160:HLG@hlg-record",
            "1920x1080:SDR@sdr-preview",
            "cross-category-coexistence",
            "hlg-implies-sdr-hdr-coexistence",
            "constraint:hlg-rejects-sdr-preview",
        ])
        self.assertIn("HLG-capable route rejects an SDR preview in the same capture request", result["reasons"])
        self.assertIn("pairwise constraint hlg-rejects-sdr-preview rejects this capture request", result["reasons"])
        self.assertIn(MUTANT_REJECTION, result["reasons"])
        self.assertIn("no independent monitoring route was chosen", result["reasons"])
        self.assertNotIn("1280x720:SDR@sdr-monitor", result["rejectedClaims"])

    def test_mutant_hlg_support_does_not_imply_sdr_and_hdr_coexistence(self) -> None:
        """Fails if HLG support is treated as permission for SDR and HDR surfaces."""
        raw = load_planner()
        cleared = copy.deepcopy(raw)
        cleared["constraints"] = []
        result = assess(cleared, ["hlg-record", "sdr-preview", "hdr10-surface"], None)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"candidate", "qualified", "allowed", "independent_monitor"})
        self.assertEqual(result["rejectedClaims"], [
            "3840x2160:HLG@hlg-record",
            "1920x1080:SDR@sdr-preview",
            "3840x2160:HDR10@hdr10-surface",
            "cross-category-coexistence",
            "hlg-implies-sdr-hdr-coexistence",
        ])
        self.assertIn(MUTANT_REJECTION, result["reasons"])
        self.assertFalse(any(item.startswith("constraint:") for item in result["rejectedClaims"]))
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn("4000x3000:RAW_LOG@raw-log", result["preservedResults"])
        source = (ROOT / "scripts" / "gates" / "p012_discover_dynamic_range_profiles.py").read_text(encoding="utf-8")
        self.assertIn(MUTANT, source)
        self.assertIn(MUTANT_REJECTION, source)
        self.assertNotIn('decision = "allowed"', source)
        self.assertNotIn('decision = "qualified"', source)
        self.assertNotIn('return _result("allowed"', source)
        self.assertNotIn('return _result("qualified"', source)

    def test_independent_monitor_is_not_same_request_coexistence(self) -> None:
        raw = load_planner()
        result = assess(raw, ["hlg-record", "sdr-preview"], "sdr-monitor")
        self.assert_contract(result)
        self.assertEqual(result["decision"], "independent_monitor")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "candidate"})
        self.assertIn("3840x2160:HLG@hlg-record", result["rejectedClaims"])
        self.assertIn("1920x1080:SDR@sdr-preview", result["rejectedClaims"])
        self.assertIn("hlg-implies-sdr-hdr-coexistence", result["rejectedClaims"])
        self.assertNotIn("1280x720:SDR@sdr-monitor", result["rejectedClaims"])
        self.assertIn("1280x720:SDR@sdr-monitor", result["preservedResults"])
        self.assertTrue(any("independent monitoring route sdr-monitor is not in the capture request" == item
                            for item in result["reasons"]))
        self.assertTrue(any("does not authorize SDR and HDR surfaces" in item for item in result["reasons"]))
        self.assertEqual(result["preservedResults"], PRESERVED)

    def test_clean_hlg_request_may_name_an_explicit_monitor(self) -> None:
        raw = load_planner()
        result = assess(raw, ["hlg-record"], "sdr-monitor")
        self.assert_contract(result)
        self.assertEqual(result["decision"], "independent_monitor")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertTrue(any("independent monitoring route sdr-monitor was chosen explicitly" == item
                            for item in result["reasons"]))
        self.assertTrue(any("not coexistence" in item for item in result["reasons"]))
        self.assertNotIn("hlg-implies-sdr-hdr-coexistence", result["rejectedClaims"])
        self.assertTrue(any("8000000" in item for item in result["reasons"]))

    def test_single_hlg_records_exposed_latency_and_is_not_qualification(self) -> None:
        raw = load_planner()
        result = assess(raw, ["hlg-record"], None)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "candidate")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertEqual(result["openQuestions"], QUESTIONS)
        self.assertIn("latency:hlg-record:8000000", result["preservedResults"])
        self.assertIn("latency:hdr10-surface:12000000", result["preservedResults"])
        self.assertFalse(any(item.startswith("latency:sdr-preview:") for item in result["preservedResults"]))
        self.assertFalse(any(item.startswith("latency:raw-log:") for item in result["preservedResults"]))
        self.assertTrue(any("additional latency 8000000 ns recorded for hlg-record" == item
                            for item in result["reasons"]))
        self.assertTrue(any("not physical S23 qualification" in item for item in result["reasons"]))
        self.assertTrue(any("ten-bit fidelity is not claimed" in item for item in result["reasons"]))

    def test_ten_bit_false_withholds_hlg_and_keeps_sdr(self) -> None:
        raw = copy.deepcopy(load_planner())
        raw["tenBitCapable"] = False
        withheld = assess(raw, ["hlg-record"], None)
        self.assert_contract(withheld)
        self.assertEqual(withheld["decision"], "withheld")
        self.assertIn("3840x2160:HLG@hlg-record", withheld["rejectedClaims"])
        self.assertIn("1920x1080:SDR@sdr-preview", withheld["preservedResults"])
        self.assertIn("4000x3000:RAW_LOG@raw-log", withheld["preservedResults"])
        self.assertTrue(any("requires ten-bit capability" in item for item in withheld["reasons"]))
        self.assertIn("ten-bit fidelity is not claimed", withheld["reasons"])
        self.assertIn("ten-bit capability query is false; ten-bit fidelity is not claimed",
                      withheld["openQuestions"])
        sdr = assess(raw, ["sdr-preview"], None)
        self.assertEqual(sdr["decision"], "candidate")
        self.assertNotIn(sdr["decision"], {"qualified", "allowed"})
        self.assertIn("1920x1080:SDR@sdr-preview", sdr["preservedResults"])
        self.assertIn("3840x2160:HLG@hlg-record", sdr["preservedResults"])

    def test_selecting_every_route_rejects_without_wiping_inventory(self) -> None:
        raw = load_planner()
        selected = [route["routeId"] for route in raw["routes"] if route["role"] != "monitoring"]
        self.assertIn("hlg-record", selected)
        self.assertIn("sdr-preview", selected)
        self.assertIn("hdr10-surface", selected)
        self.assertIn("raw-log", selected)
        result = assess(raw, selected, None)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertGreater(len(result["preservedResults"]), len(selected))
        self.assertIn("hlg-implies-sdr-hdr-coexistence", result["rejectedClaims"])

    def test_hdr10_with_sdr_is_rejected_without_the_hlg_mutant_token(self) -> None:
        raw = load_planner()
        result = assess(raw, ["hdr10-surface", "sdr-preview"], None)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("cross-category-coexistence", result["rejectedClaims"])
        self.assertNotIn("hlg-implies-sdr-hdr-coexistence", result["rejectedClaims"])
        self.assertIn("HLG, HDR10, SDR, and RAW-derived Log remain separate categories", result["reasons"])

    def test_hlg_with_hdr10_is_still_the_mutant(self) -> None:
        raw = load_planner()
        result = assess(raw, ["hlg-record", "hdr10-surface"], None)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hlg-implies-sdr-hdr-coexistence", result["rejectedClaims"])
        self.assertNotIn("constraint:hlg-rejects-sdr-preview", result["rejectedClaims"])

    def test_hlg_with_raw_log_stays_a_separate_category(self) -> None:
        raw = load_planner()
        result = assess(raw, ["hlg-record", "raw-log"], None)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("cross-category-coexistence", result["rejectedClaims"])
        self.assertNotIn("hlg-implies-sdr-hdr-coexistence", result["rejectedClaims"])
        self.assertIn("sensor-derived Log is not established by a RAW-derived Log label", result["openQuestions"])
        alone = assess(raw, ["raw-log"], None)
        self.assertEqual(alone["decision"], "candidate")
        self.assertNotIn(alone["decision"], {"qualified", "allowed"})
        self.assertTrue(any("RAW-derived Log is not HLG, HDR10, SDR, or sensor-derived Log" == item
                            for item in alone["reasons"]))

    def test_same_category_pair_is_candidate_until_a_constraint_rejects_it(self) -> None:
        preview = route(routeId="sdr-preview", role="preview", width=1280, height=720)
        record = route(routeId="sdr-record", role="recording", width=1920, height=1080)
        open_pair = document([preview, record])
        result = assess(open_pair, ["sdr-preview", "sdr-record"], None)
        self.assertEqual(result["decision"], "candidate")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        closed = document([preview, record], constraints=[{
            "constraintId": "no-dual-sdr",
            "kind": "same_request_rejected",
            "members": ["sdr-preview", "sdr-record"],
            "reason": "declared camera constraint rejects dual SDR outputs",
        }])
        rejected = assess(closed, ["sdr-preview", "sdr-record"], None)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn("constraint:no-dual-sdr", rejected["rejectedClaims"])
        self.assertNotIn("hlg-implies-sdr-hdr-coexistence", rejected["rejectedClaims"])
        self.assertIn("pairwise constraint no-dual-sdr rejects this capture request", rejected["reasons"])
        self.assertIn("1280x720:SDR@sdr-preview", rejected["preservedResults"])
        self.assertIn("1920x1080:SDR@sdr-record", rejected["preservedResults"])

    def test_set_constraint_is_named_when_members_exceed_a_pair(self) -> None:
        routes = [
            route(routeId="sdr-a", width=640, height=480),
            route(routeId="sdr-b", width=1280, height=720),
            route(routeId="sdr-c", width=1920, height=1080, role="recording"),
        ]
        doc = document(routes, constraints=[{
            "constraintId": "no-triple-sdr",
            "kind": "same_request_rejected",
            "members": ["sdr-a", "sdr-b", "sdr-c"],
            "reason": "set constraint rejects three SDR outputs together",
        }])
        result = assess(doc, ["sdr-a", "sdr-b", "sdr-c"], None)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("set constraint no-triple-sdr rejects this capture request", result["reasons"])
        pair = assess(doc, ["sdr-a", "sdr-b"], None)
        self.assertEqual(pair["decision"], "candidate")

    def test_query_error_withholds_one_route_and_keeps_neighbors(self) -> None:
        raw = load_planner()
        result = assess(raw, ["hlg-preview-unreadable"], None)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["1920x1080:HLG@hlg-preview-unreadable"])
        self.assertIn("3840x2160:HLG@hlg-record", result["preservedResults"])
        self.assertIn("4000x3000:RAW_LOG@raw-log", result["preservedResults"])
        self.assertTrue(any("dynamicRangeProfiles" in item for item in result["reasons"]))
        broken = copy.deepcopy(raw)
        for item in broken["routes"]:
            if item["routeId"] == "sdr-preview":
                item["supported"] = False
        unsupported = assess(broken, ["sdr-preview"], None)
        self.assertEqual(unsupported["decision"], "withheld")
        self.assertIn("1920x1080:SDR@sdr-preview", unsupported["rejectedClaims"])
        self.assertIn("3840x2160:HLG@hlg-record", unsupported["preservedResults"])
        self.assertTrue(any("sdr-preview is not supported" == item for item in unsupported["reasons"]))

    def test_unusable_monitor_does_not_launder_a_mixed_request(self) -> None:
        raw = copy.deepcopy(load_planner())
        for item in raw["routes"]:
            if item["routeId"] == "sdr-monitor":
                item["queryError"] = "monitor unavailable"
        result = assess(raw, ["hlg-record", "sdr-preview"], "sdr-monitor")
        self.assertEqual(result["decision"], "rejected")
        self.assertNotEqual(result["decision"], "independent_monitor")
        self.assertTrue(any("monitoring route sdr-monitor is not usable and was not chosen" == item
                            for item in result["reasons"]))
        self.assertIn("1920x1080:HLG@hlg-preview-unreadable", result["preservedResults"])

    def test_invalid_documents_and_selections_raise(self) -> None:
        raw = load_planner()
        extra = copy.deepcopy(raw)
        extra["note"] = "device probe"
        missing = copy.deepcopy(raw)
        del missing["mutant"]
        wrong_phase = copy.deepcopy(raw)
        wrong_phase["phase"] = "P011"
        wrong_revision = copy.deepcopy(raw)
        wrong_revision["implementationBaseRevision"] = "abc"
        alias = copy.deepcopy(raw)
        for item in alias["routes"]:
            if item["routeId"] == "raw-log":
                item["category"] = "HLG"
        bad_profile = copy.deepcopy(raw)
        bad_profile["routes"][0]["profile"] = "HLG10"
        bad_profile["routes"][0]["category"] = "HLG10"
        latency = copy.deepcopy(raw)
        latency["routes"][1]["additionalLatencyNs"] = 0.0
        negative_latency = copy.deepcopy(raw)
        negative_latency["routes"][0]["additionalLatencyNs"] = -1
        bool_latency = copy.deepcopy(raw)
        bool_latency["routes"][0]["additionalLatencyNs"] = True
        empty_routes = copy.deepcopy(raw)
        empty_routes["routes"] = []
        duplicate = copy.deepcopy(raw)
        duplicate["routes"].append(copy.deepcopy(duplicate["routes"][0]))
        bad_member = copy.deepcopy(raw)
        bad_member["constraints"][0]["members"] = ["hlg-record", "missing"]
        allow_kind = copy.deepcopy(raw)
        allow_kind["constraints"][0]["kind"] = "same_request_allowed"
        ten_bit = copy.deepcopy(raw)
        ten_bit["tenBitCapable"] = "true"
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            alias,
            bad_profile,
            latency,
            negative_latency,
            bool_latency,
            empty_routes,
            duplicate,
            bad_member,
            allow_kind,
            ten_bit,
            document([route(routeId="")]),
            document([route(role="monitor")]),
            document([route()], schemaVersion=True),
            document([route()], failedProperties=["optionalCodecQuery", "optionalCodecQuery"]),
            document([route()], method="mutant"),
            document([route()], fixture="other"),
            document([route()], oracle="other"),
            document([route()], mutant="HLG allows coexistence"),
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_planner(sample)
        with self.assertRaises(ValueError):
            assess(raw, ["missing-route"], None)
        with self.assertRaises(ValueError):
            assess(raw, [], None)
        with self.assertRaises(ValueError):
            assess(raw, ["hlg-record", "hlg-record"], None)
        with self.assertRaises(ValueError):
            assess(raw, ["hlg-record", "sdr-monitor"], "sdr-monitor")
        with self.assertRaises(ValueError):
            assess(raw, ["hlg-record"], "sdr-preview")
        with self.assertRaises(ValueError):
            assess(raw, ["hlg-record"], "")
        with self.assertRaises(ValueError):
            assess(raw, "hlg-record", None)


if __name__ == "__main__":
    unittest.main()
