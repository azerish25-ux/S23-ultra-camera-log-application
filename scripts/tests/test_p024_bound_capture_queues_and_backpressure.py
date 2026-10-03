"""Host checks for P024 bounded capture queues. Not a physical S23 probe.

TC-P024-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p024_bound_capture_queues_and_backpressure",
    ROOT / "scripts" / "gates" / "p024_bound_capture_queues_and_backpressure.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

assess = _MODULE.assess
is_mutant = _MODULE.is_mutant
observe = _MODULE.observe
unbounded_shared_accepts_all = _MODULE.unbounded_shared_accepts_all
validate_policy = _MODULE.validate_policy

BASE = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
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


def load_fixture() -> dict:
    path = ROOT / "docs" / "P024_BOUND_CAPTURE_QUEUES_AND_BACKPRESSURE.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_handoff() -> dict:
    path = ROOT / "docs" / "evidence" / "P024-handoff.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens(document: dict) -> list[str]:
    tokens: list[str] = []
    for condition in document["conditions"]:
        for frame in condition["frames"]:
            tokens.append(f"{condition['id']}:{frame['id']}@{frame['timestampNs']}")
    return tokens


class P024BackpressureTests(unittest.TestCase):
    def assert_contract(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P024")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))

    def test_module_encodes_method_fixture_oracle_and_mutant(self) -> None:
        self.assertIn("Budget queues in bytes and frames", _MODULE.METHOD)
        self.assertIn("preview drops", _MODULE.METHOD)
        self.assertIn("visible stop with gap evidence", _MODULE.METHOD)
        self.assertIn("without altering source timestamps", _MODULE.METHOD)
        self.assertEqual(
            _MODULE.FIXTURE,
            (
                "A depth worker blocked for several seconds while the source writer "
                "remains healthy, followed by a deliberately stalled source writer."
            ),
        )
        self.assertIn("monitoring freshness", _MODULE.ORACLE)
        self.assertIn("documented capture stop", _MODULE.ORACLE)
        self.assertEqual(
            _MODULE.MUTANT,
            "Use one unbounded queue for source writing, preview, and inference.",
        )
        self.assertEqual(_MODULE.BASE_REVISION, BASE)
        self.assertEqual(_MODULE.PHASE, "P024")
        self.assertEqual(_MODULE.POLICY_ID, "s23-backpressure-fixture")

    def test_fixture_separates_monitoring_stall_from_source_stop(self) -> None:
        raw = load_fixture()
        self.assertIsNone(validate_policy(raw))
        self.assertFalse(is_mutant(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P024")
        self.assertEqual(raw["policyId"], "s23-backpressure-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE)
        self.assertEqual(raw["method"], _MODULE.METHOD)
        self.assertEqual(raw["fixture"], _MODULE.FIXTURE)
        self.assertEqual(raw["oracle"], _MODULE.ORACLE)
        self.assertEqual(raw["mutant"], _MODULE.MUTANT)
        self.assertEqual([item["role"] for item in raw["queues"]], ["source", "preview", "inference"])
        self.assertEqual(raw["queues"][0]["overflowPolicy"], "visible_stop_with_gap")
        self.assertEqual(raw["queues"][1]["overflowPolicy"], "discard_stale")
        self.assertEqual(raw["queues"][2]["overflowPolicy"], "discard_stale")
        self.assertTrue(all(item["bounded"] is True for item in raw["queues"]))
        self.assertEqual(raw["conditions"][0]["id"], "depth_blocked")
        self.assertEqual(raw["conditions"][0]["sourceWriter"], "healthy")
        self.assertGreaterEqual(raw["conditions"][0]["blockedSeconds"], 2)
        self.assertEqual(raw["conditions"][1]["id"], "source_stalled")
        self.assertEqual(raw["conditions"][1]["sourceWriter"], "stalled")
        observed = observe(raw)
        depth = observed["conditions"]["depth_blocked"]
        stalled = observed["conditions"]["source_stalled"]
        self.assertEqual(depth["monitoringFreshness"], "reduced")
        self.assertIs(depth["captureStopped"], False)
        self.assertIs(depth["hiddenLoss"], False)
        self.assertEqual(depth["sourceTimestamps"], depth["offeredTimestamps"])
        self.assertGreater(depth["inferenceDropped"], 0)
        self.assertIs(stalled["captureStopped"], True)
        self.assertIs(stalled["documentedStop"], True)
        self.assertTrue(stalled["gaps"])
        self.assertEqual(
            stalled["sourceTimestamps"],
            stalled["offeredTimestamps"][: len(stalled["sourceTimestamps"])],
        )
        self.assertNotEqual(stalled["sourceTimestamps"], stalled["offeredTimestamps"])
        result = assess(raw)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "policy_holds")
        self.assertEqual(result["rejectedClaims"], [f"gap:{token}" for token in stalled["gaps"]])
        for token in depth["retained"]:
            self.assertIn(f"depth_blocked:{token}", result["preservedResults"])
        for token in stalled["retained"]:
            self.assertIn(f"source_stalled:{token}", result["preservedResults"])
        for token in stalled["gaps"]:
            self.assertNotIn(f"source_stalled:{token}", result["preservedResults"])
        self.assertTrue(
            any(
                f"inference discarded {depth['inferenceDropped']} stale frames" in item
                for item in result["reasons"]
            )
        )
        self.assertTrue(
            any(
                f"peaked at {observed['leasePeak']} within limit {raw['budgets']['leaseLimit']}"
                in item
                for item in result["reasons"]
            )
        )
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))
        self.assertNotIn(result["decision"], FORBIDDEN)

    def test_mutant_unbounded_shared_queue_is_rejected(self) -> None:
        raw = load_fixture()
        mutant = copy.deepcopy(raw)
        mutant["sharedUnbounded"] = True
        mutant["queues"] = [
            {
                "name": "shared",
                "roles": ["source", "preview", "inference"],
                "bounded": False,
                "overflowPolicy": "unbounded",
                "frameCapacity": None,
                "byteCapacity": None,
            }
        ]
        self.assertTrue(is_mutant(mutant))
        behaviour = unbounded_shared_accepts_all(len(raw["conditions"][1]["frames"]))
        self.assertEqual(behaviour["accepted"], 5)
        self.assertIs(behaviour["stopped"], False)
        self.assertEqual(behaviour["gaps"], [])
        self.assertIs(behaviour["bounded"], False)
        result = assess(mutant)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "policy_holds"})
        self.assertIn("unbounded-shared-queue", result["rejectedClaims"])
        self.assertIn("hidden-source-loss", result["rejectedClaims"])
        for token in _tokens(raw):
            self.assertIn(token, result["preservedResults"])
        self.assertTrue(any(_MODULE.MUTANT in item for item in result["reasons"]))
        honest = assess(raw)
        self.assertEqual(honest["decision"], "policy_holds")
        self.assertNotEqual(result["decision"], honest["decision"])
        honest_stop = observe(raw)["conditions"]["source_stalled"]["captureStopped"]
        self.assertIs(honest_stop, True)
        self.assertNotEqual(honest_stop, behaviour["stopped"])

    def test_shared_flag_alone_rejects_and_keeps_source_frames(self) -> None:
        mutant = {
            "schemaVersion": 1,
            "phase": "P024",
            "implementationBaseRevision": BASE,
            "mutant": _MODULE.MUTANT,
            "sharedUnbounded": True,
            "sourceFrames": [
                {"id": "f0", "timestampNs": "0"},
                {"id": "f1", "timestampNs": "1000"},
            ],
        }
        result = assess(mutant)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], FORBIDDEN | {"policy_holds"})
        self.assertEqual(result["preservedResults"], ["f0@0", "f1@1000"])
        self.assertIn("unbounded-shared-queue", result["rejectedClaims"])

    def test_hidden_replacement_and_unbounded_source_keep_the_inventory(self) -> None:
        raw = load_fixture()
        inventory = _tokens(raw)
        overwrite = copy.deepcopy(raw)
        overwrite["queues"][0]["overflowPolicy"] = "overwrite"
        replaced = assess(overwrite)
        self.assert_contract(replaced)
        self.assertEqual(replaced["decision"], "rejected")
        self.assertEqual(replaced["rejectedClaims"], ["hidden-frame-replacement"])
        self.assertEqual(replaced["preservedResults"], inventory)
        self.assertNotIn(replaced["decision"], FORBIDDEN | {"policy_holds"})
        unbounded = copy.deepcopy(raw)
        unbounded["queues"][0]["overflowPolicy"] = "unbounded"
        unbounded["queues"][0]["bounded"] = False
        opened = assess(unbounded)
        self.assertEqual(opened["decision"], "rejected")
        self.assertEqual(opened["rejectedClaims"], ["unbounded-source-queue"])
        self.assertEqual(opened["preservedResults"], inventory)
        preview = copy.deepcopy(raw)
        preview["queues"][1]["overflowPolicy"] = "visible_stop_with_gap"
        blocked = assess(preview)
        self.assertEqual(blocked["decision"], "rejected")
        self.assertIn("preview-policy-alters-source", blocked["rejectedClaims"])
        self.assertEqual(blocked["preservedResults"], inventory)

    def test_lease_pressure_is_withheld_without_wiping_frames(self) -> None:
        raw = load_fixture()
        inventory = _tokens(raw)
        crowded = copy.deepcopy(raw)
        crowded["budgets"]["leaseLimit"] = 2
        result = assess(crowded)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], FORBIDDEN | {"policy_holds"})
        self.assertEqual(result["rejectedClaims"], ["lease-budget-exceeded"])
        self.assertEqual(result["preservedResults"], inventory)
        peaked = copy.deepcopy(raw)
        peaked["budgets"]["leaseLimit"] = 3
        peaked["leases"] = peaked["leases"][:1]
        peaked_result = assess(peaked)
        self.assertEqual(peaked_result["decision"], "withheld")
        self.assertIn("lease-budget-exceeded", peaked_result["rejectedClaims"])
        self.assertEqual(peaked_result["preservedResults"], inventory)
        self.assertTrue(any("lease peak 4 exceeded limit 3" in item for item in peaked_result["reasons"]))

    def test_stall_that_never_fills_the_source_is_withheld(self) -> None:
        raw = load_fixture()
        short = copy.deepcopy(raw)
        short["conditions"][1]["frames"] = short["conditions"][1]["frames"][:2]
        result = assess(short)
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn(result["decision"], FORBIDDEN | {"policy_holds"})
        self.assertIn("depth_blocked:d0@1000000000", result["preservedResults"])
        self.assertIn("source_stalled:s0@3000000000", result["preservedResults"])
        self.assertIn("source_stalled:s1@3333333333", result["preservedResults"])

    def test_smaller_preview_budget_still_keeps_source_timestamps(self) -> None:
        raw = load_fixture()
        tight = copy.deepcopy(raw)
        tight["budgets"]["previewFrames"] = 1
        tight["budgets"]["previewBytes"] = 512
        tight["queues"][1]["frameCapacity"] = 1
        tight["queues"][1]["byteCapacity"] = 512
        observed = observe(tight)
        depth = observed["conditions"]["depth_blocked"]
        self.assertGreater(depth["previewDropped"], 0)
        self.assertEqual(depth["sourceTimestamps"], depth["offeredTimestamps"])
        self.assertIs(depth["captureStopped"], False)
        result = assess(tight)
        self.assertEqual(result["decision"], "policy_holds")
        self.assertNotIn(result["decision"], FORBIDDEN)
        self.assertIn("depth_blocked:d4@2333333333", result["preservedResults"])

    def test_invalid_policies_raise(self) -> None:
        valid = load_fixture()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["oracle"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P023"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "fffd5c9a63cb732e103052acae29ae0c251585cc"
        wrong_method = copy.deepcopy(valid)
        wrong_method["method"] = "one unbounded queue"
        mutant = copy.deepcopy(valid)
        mutant["sharedUnbounded"] = True
        empty = copy.deepcopy(valid)
        empty["conditions"] = []
        bad_stamp = copy.deepcopy(valid)
        bad_stamp["conditions"][0]["frames"][1]["timestampNs"] = "1000000000"
        short_block = copy.deepcopy(valid)
        short_block["conditions"][0]["blockedSeconds"] = 1
        swapped = copy.deepcopy(valid)
        swapped["conditions"] = list(reversed(swapped["conditions"]))
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            wrong_method,
            mutant,
            empty,
            bad_stamp,
            short_block,
            swapped,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_policy(sample)
        with self.assertRaises(ValueError):
            unbounded_shared_accepts_all(0)
        with self.assertRaises(ValueError):
            assess({"phase": "P024"})

    def test_handoff_lists_cases_and_does_not_invent_a_commit(self) -> None:
        handoff = load_handoff()
        self.assertEqual(tuple(handoff), HANDOFF_KEYS)
        self.assertEqual(handoff["phase"], "P024")
        self.assertEqual(handoff["caseIds"], [f"TC-P024-0{index}" for index in range(1, 9)])
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], [])
        self.assertEqual(handoff["nextPhase"], "P025")
        self.assertIn(
            "python3 -m unittest discover -s scripts/tests -p 'test_p024*.py' -v",
            handoff["testsRun"],
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        self.assertIn("fixed cadence without measured evidence", handoff["unverified"])
        self.assertIn("sensor-derived Log", handoff["unverified"])
        self.assertIn("ten-bit fidelity", handoff["unverified"])
        self.assertIn("film-stock fidelity", handoff["unverified"])
        self.assertIn("cinema-camera equivalence", handoff["unverified"])
        for relative in handoff["changedFiles"]:
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
