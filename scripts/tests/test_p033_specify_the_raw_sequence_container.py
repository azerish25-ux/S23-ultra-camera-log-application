"""Host checks for the P033 RAW sequence container. Not a physical S23 probe.

TC-P033-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p033_specify_the_raw_sequence_container import (  # noqa: E402
    ALLOCATION_BASIS,
    BASE_REVISION,
    FIXTURE,
    METHOD,
    MUTANT,
    MUTANT_BASIS,
    ORACLE,
    assess_source,
    bounds_checked_reserve,
    mutant_declared_reserve,
    validate_fixture,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
HANDOFF_KEYS = (
    "phase",
    "caseIds",
    "changedFiles",
    "commit",
    "testsRun",
    "failures",
    "unverified",
    "nextPhase",
)
FORBIDDEN = {"qualified", "allowed"}
PREFIX_BYTES = 6144 * 3


def load_fixture() -> dict:
    path = ROOT / "docs" / "P033_SPECIFY_THE_RAW_SEQUENCE_CONTAINER.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P033-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


def intact_source(document: dict) -> dict:
    closed = copy.deepcopy(document)
    closed["frames"] = closed["frames"][:3]
    closed["container"]["endState"] = "closed"
    return closed


class P033RawSequenceTests(unittest.TestCase):
    def test_fixture_encodes_method_oracle_and_base_revision(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_fixture(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P033")
        self.assertEqual(raw["contractId"], "s23-raw-sequence-container-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertIn("three-frame", raw["fixture"])
        self.assertIn("oversized length", raw["fixture"])
        self.assertEqual(raw["container"]["magic"], "S23RAW01")
        self.assertEqual(raw["container"]["schemaVersion"], 1)
        self.assertEqual(raw["container"]["routeIdentity"], "logical-0/RAW_SENSOR")
        self.assertEqual((raw["container"]["width"], raw["container"]["height"]), (64, 48))
        self.assertEqual(raw["container"]["cfa"], "RGGB")
        self.assertEqual(raw["container"]["packing"], "uint16le-tight")
        self.assertEqual(raw["container"]["calibrationSnapshotId"], "cal-unmeasured-1")
        self.assertEqual(raw["container"]["endState"], "interrupted")
        self.assertEqual(raw["recoveryMode"], "explicit-complete-prefix")
        self.assertIs(raw["originalRewritten"], False)
        self.assertEqual(len(raw["frames"]), 4)
        self.assertEqual(ALLOCATION_BASIS, "bounds-checked")
        self.assertNotEqual(ALLOCATION_BASIS, MUTANT_BASIS)

    def test_three_frame_prefix_and_corrupt_tail_are_separate(self) -> None:
        raw = load_fixture()
        before = copy.deepcopy(raw)
        result = assess_source(raw)
        self.assertEqual(raw, before)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P033")
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertEqual(result["rejectedClaims"], ["oversized-length", "truncated-record"])
        for token in (
            "magic:S23RAW01",
            "route:logical-0/RAW_SENSOR",
            "geometry:64x48",
            "cfa:RGGB",
            "packing:uint16le-tight",
            "calibration:cal-unmeasured-1",
            "prefix:0",
            "prefix:1",
            "prefix:2",
            "timestamp:1000000000",
            "timestamp:3000000000",
            "reserved:18432",
            "allocation:bounds-checked",
            "original:unmodified",
            "tail:3",
            "tail-declared:2147483648",
            "tail-present:128",
            "tail-end-state:truncated",
            "recovery:explicit-complete-prefix",
        ):
            self.assertIn(token, result["preservedResults"])
        self.assertNotIn("prefix:3", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertTrue(any("corruption is reported separately" in item for item in result["reasons"]))
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_mutant_declared_length_is_not_allocated(self) -> None:
        raw = load_fixture()
        honest = bounds_checked_reserve(raw)
        unsafe = mutant_declared_reserve(raw)
        self.assertEqual(honest, PREFIX_BYTES)
        self.assertEqual(unsafe, PREFIX_BYTES + raw["frames"][3]["declaredPayloadLength"])
        self.assertGreater(unsafe, honest)
        self.assertGreater(raw["frames"][3]["declaredPayloadLength"], raw["container"]["maxPayloadBytes"])
        result = assess_source(raw)
        self.assertEqual(result["decision"], "prefix_recovered")
        self.assertNotIn(result["decision"], FORBIDDEN | {"source_intact"})
        self.assertIn("reserved:" + str(honest), result["preservedResults"])
        self.assertNotIn("reserved:" + str(unsafe), result["preservedResults"])
        self.assertNotIn("allocation:" + MUTANT_BASIS, result["preservedResults"])
        self.assertTrue(any(MUTANT + " was not applied" in item for item in result["reasons"]))
        self.assertIn("tail-declared:2147483648", result["preservedResults"])

    def test_strict_mode_is_not_recovery_and_keeps_the_prefix(self) -> None:
        strict = load_fixture()
        strict["recoveryMode"] = "strict"
        result = assess_source(strict)
        self.assertEqual(result["decision"], "development_rejected")
        self.assertNotEqual(result["decision"], "prefix_recovered")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertEqual(result["rejectedClaims"], ["oversized-length", "truncated-record"])
        self.assertIn("prefix:0", result["preservedResults"])
        self.assertIn("prefix:2", result["preservedResults"])
        self.assertIn("reserved:18432", result["preservedResults"])
        self.assertIn("original:unmodified", result["preservedResults"])
        self.assertIn("tail:3", result["preservedResults"])
        self.assertTrue(any("strict development rejection" in item for item in result["reasons"]))

    def test_rewrite_is_rejected_without_dropping_the_prefix(self) -> None:
        rewritten = load_fixture()
        rewritten["originalRewritten"] = True
        result = assess_source(rewritten)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], FORBIDDEN | {"prefix_recovered"})
        self.assertIn("original-rewritten", result["rejectedClaims"])
        self.assertIn("oversized-length", result["rejectedClaims"])
        self.assertIn("prefix:1", result["preservedResults"])
        self.assertIn("geometry:64x48", result["preservedResults"])
        self.assertIn("rewrite:refused", result["preservedResults"])
        self.assertIn("reserved:18432", result["preservedResults"])
        self.assertNotIn("reserved:" + str(mutant_declared_reserve(rewritten)), result["preservedResults"])

    def test_intact_source_is_not_qualified(self) -> None:
        closed = intact_source(load_fixture())
        self.assertEqual(bounds_checked_reserve(closed), mutant_declared_reserve(closed))
        result = assess_source(closed)
        self.assertEqual(result["decision"], "source_intact")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("prefix:0", result["preservedResults"])
        self.assertIn("prefix:2", result["preservedResults"])
        self.assertNotIn("tail:3", result["preservedResults"])
        self.assertIn("end-state:closed", result["preservedResults"])
        self.assertTrue(any("not physical qualification" in item for item in result["reasons"]))

    def test_invalid_fixtures_raise(self) -> None:
        valid = load_fixture()
        cases = []
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        cases.append(extra)
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        cases.append(missing)
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P032"
        cases.append(bad_phase)
        bad_magic = copy.deepcopy(valid)
        bad_magic["container"]["magic"] = "RAW"
        cases.append(bad_magic)
        odd = copy.deepcopy(valid)
        odd["container"]["width"] = 63
        cases.append(odd)
        huge_complete = copy.deepcopy(valid)
        huge_complete["frames"][0]["declaredPayloadLength"] = 2**31
        cases.append(huge_complete)
        regression = copy.deepcopy(valid)
        regression["frames"][2]["timestampNs"] = "1500000000"
        cases.append(regression)
        bool_len = copy.deepcopy(valid)
        bool_len["frames"][3]["declaredPayloadLength"] = True
        cases.append(bool_len)
        closed_tail = copy.deepcopy(valid)
        closed_tail["container"]["endState"] = "closed"
        cases.append(closed_tail)
        cases.extend((None, [], {}, document_with_mode("other")))
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_fixture(sample)

    def test_handoff_and_doc_state_host_limits(self) -> None:
        handoff = load_handoff()
        self.assertEqual(tuple(handoff), HANDOFF_KEYS)
        self.assertEqual(handoff["phase"], "P033")
        self.assertEqual(handoff["nextPhase"], "P034")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], [])
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p033*.py' -v",
            handoff["testsRun"],
        )
        note = (ROOT / "docs" / "P033_SPECIFY_THE_RAW_SEQUENCE_CONTAINER.md").read_text(encoding="utf-8")
        self.assertIn("host fixture", note)
        self.assertIn("python3 -m unittest discover -s scripts/tests -p 'test_p033*.py' -v", note)
        self.assertIn("## Non-claims", note)
        for phrase in (
            "physical S23",
            "fixed cadence without measured evidence",
            "sensor-derived Log",
            "ten-bit fidelity",
            "film-stock fidelity",
            "cinema-camera equivalence",
        ):
            self.assertIn(phrase, note)


def document_with_mode(mode: str) -> dict:
    sample = load_fixture()
    sample["recoveryMode"] = mode
    return sample


if __name__ == "__main__":
    unittest.main()
