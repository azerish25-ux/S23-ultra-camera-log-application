"""TC-P008-08 independent reproduction."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


def _load():
    path = Path(__file__).resolve().parents[1] / "gates" / "p008_tc08.py"
    spec = importlib.util.spec_from_file_location("p008_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load()

RESULT_KEYS = [
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
]

FORBIDDEN = ("complete", "allowed")


def payload(**overrides):
    reproduction = {
        "undocumentedFiles": False,
        "manualIntervention": False,
        "missingPrerequisite": None,
        "phoneConnected": False,
    }
    reproduction.update(overrides.pop("reproduction", {}))
    base = {
        "reproduction": reproduction,
        "statedSoftwareResult": "host gate green on the pinned revision",
        "tempPath": "/tmp/s23-repro",
        "remoteCommit": "remote-sha-008",
        "hostGatePassed": True,
        "physicalGate": "pending",
    }
    base.update(overrides)
    return base


class TcP00808Tests(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(list(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "TC-P008-08")
        self.assertIsInstance(result["reasons"], list)
        self.assertIsInstance(result["rejectedClaims"], list)
        self.assertIsInstance(result["preservedResults"], dict)
        self.assertIsInstance(result["openQuestions"], list)
        self.assertNotIn(result["decision"], FORBIDDEN)
        if result["decision"] != "allowed":
            self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_undocumented_files_stay_unverified(self):
        stated = "host gate green on the pinned revision"
        body = payload(
            reproduction={
                "undocumentedFiles": True,
                "manualIntervention": False,
                "missingPrerequisite": None,
                "phoneConnected": True,
            },
            statedSoftwareResult=stated,
            tempPath="/var/tmp/fresh-a",
            remoteCommit="keep-remote",
            hostGatePassed=True,
            physicalGate="passed",
        )
        original = copy.deepcopy(body)
        result = gate.evaluate(body)
        self.assertEqual(body, original)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("undocumented-files", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"]["statedSoftwareResult"], stated)
        self.assertEqual(result["preservedResults"]["remoteCommit"], "keep-remote")
        self.assertNotIn(result["decision"], ("reproduced", "software_verified_only", "complete"))

    def test_unrecorded_manual_intervention_stays_unverified(self):
        body = payload(
            reproduction={"manualIntervention": True, "phoneConnected": False},
            hostGatePassed=True,
            physicalGate="passed",
            tempPath="/tmp/other",
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn("unrecorded-manual-intervention", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"]["statedSoftwareResult"],
            body["statedSoftwareResult"],
        )
        self.assertEqual(result["preservedResults"]["remoteCommit"], body["remoteCommit"])

    def test_missing_prerequisite_is_an_open_question_and_unverified(self):
        prerequisite = "fresh Gradle distribution without the developer cache"
        body = payload(
            reproduction={
                "undocumentedFiles": False,
                "manualIntervention": False,
                "missingPrerequisite": prerequisite,
                "phoneConnected": False,
            },
            hostGatePassed=True,
            physicalGate="pending",
            remoteCommit="remote-kept",
            statedSoftwareResult="claimed host result",
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn(prerequisite, result["openQuestions"])
        self.assertEqual(result["openQuestions"], [prerequisite])
        self.assertIn("missing-prerequisite", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"]["statedSoftwareResult"], "claimed host result")
        self.assertEqual(result["preservedResults"]["remoteCommit"], "remote-kept")
        self.assertNotEqual(result["decision"], "complete")

    def test_combined_reproduction_gaps_stay_unverified(self):
        prerequisite = "private colour notes"
        body = payload(
            reproduction={
                "undocumentedFiles": True,
                "manualIntervention": True,
                "missingPrerequisite": prerequisite,
                "phoneConnected": True,
            },
            hostGatePassed=True,
            physicalGate="passed",
        )
        result = gate.evaluate(body)
        self.assert_contract(result)
        self.assertEqual(result["decision"], "unverified")
        self.assertIn(prerequisite, result["openQuestions"])
        self.assertIn("undocumented-files", result["rejectedClaims"])
        self.assertIn("unrecorded-manual-intervention", result["rejectedClaims"])
        self.assertEqual(
            result["preservedResults"]["remoteCommit"], body["remoteCommit"]
        )
        self.assertEqual(
            result["preservedResults"]["statedSoftwareResult"],
            body["statedSoftwareResult"],
        )

    def test_clean_host_pass_with_pending_physical_gate_is_software_verified_only(self):
        for phone in (False, True):
            for temp in ("/tmp/one", "/var/tmp/two", ""):
                with self.subTest(phone=phone, temp=temp):
                    body = payload(
                        reproduction={"phoneConnected": phone},
                        tempPath=temp,
                        hostGatePassed=True,
                        physicalGate="pending",
                        remoteCommit="concurrent-remote",
                        statedSoftwareResult="software result only",
                    )
                    result = gate.evaluate(body)
                    self.assert_contract(result)
                    self.assertEqual(result["decision"], "software_verified_only")
                    self.assertEqual(
                        result["openQuestions"], ["physical device gate pending"]
                    )
                    self.assertEqual(
                        result["preservedResults"]["remoteCommit"], "concurrent-remote"
                    )
                    self.assertEqual(
                        result["preservedResults"]["statedSoftwareResult"],
                        "software result only",
                    )
                    self.assertNotIn(
                        result["decision"], ("complete", "reproduced", "allowed")
                    )
                    if phone:
                        self.assertIn(
                            "does not certify",
                            " ".join(result["reasons"]).lower(),
                        )

    def test_temp_path_is_ignored(self):
        left = gate.evaluate(payload(tempPath="/tmp/alpha"))
        right = gate.evaluate(payload(tempPath="/completely/different"))
        self.assertEqual(left, right)
        self.assertNotIn("/tmp/alpha", " ".join(left["reasons"]))
        self.assertNotIn("tempPath", left["preservedResults"])

    def test_phone_does_not_change_pending_decision(self):
        connected = gate.evaluate(payload(reproduction={"phoneConnected": True}))
        disconnected = gate.evaluate(payload(reproduction={"phoneConnected": False}))
        self.assertEqual(connected["decision"], "software_verified_only")
        self.assertEqual(disconnected["decision"], "software_verified_only")
        self.assertEqual(connected["openQuestions"], disconnected["openQuestions"])
        self.assertEqual(connected["preservedResults"], disconnected["preservedResults"])
        self.assertEqual(connected["rejectedClaims"], disconnected["rejectedClaims"])

    def test_clean_host_and_physical_gates_are_reproduced(self):
        for phone in (False, True):
            for temp in ("/tmp/repro-a", "/tmp/repro-b"):
                with self.subTest(phone=phone, temp=temp):
                    body = payload(
                        reproduction={"phoneConnected": phone},
                        tempPath=temp,
                        hostGatePassed=True,
                        physicalGate="passed",
                        remoteCommit="reproduced-remote",
                        statedSoftwareResult="reproduced software result",
                    )
                    result = gate.evaluate(body)
                    self.assert_contract(result)
                    self.assertEqual(result["decision"], "reproduced")
                    self.assertEqual(result["openQuestions"], [])
                    self.assertEqual(result["rejectedClaims"], [])
                    self.assertEqual(
                        result["preservedResults"]["remoteCommit"], "reproduced-remote"
                    )
                    self.assertEqual(
                        result["preservedResults"]["statedSoftwareResult"],
                        "reproduced software result",
                    )
                    self.assertNotEqual(result["decision"], "complete")

    def test_failed_host_gate_does_not_become_software_verified_or_reproduced(self):
        for physical in ("pending", "passed"):
            for phone in (False, True):
                with self.subTest(physical=physical, phone=phone):
                    result = gate.evaluate(
                        payload(
                            reproduction={"phoneConnected": phone},
                            hostGatePassed=False,
                            physicalGate=physical,
                            tempPath="/tmp/does-not-matter",
                        )
                    )
                    self.assert_contract(result)
                    self.assertEqual(result["decision"], "blocked")
                    self.assertNotIn(
                        result["decision"],
                        ("software_verified_only", "reproduced", "complete", "allowed"),
                    )
                    self.assertEqual(
                        result["preservedResults"]["remoteCommit"],
                        payload()["remoteCommit"],
                    )

    def test_dirty_reproduction_beats_green_gates(self):
        cases = [
            {"undocumentedFiles": True},
            {"manualIntervention": True},
            {"missingPrerequisite": "emulator image checksum"},
        ]
        for gap in cases:
            with self.subTest(gap=gap):
                result = gate.evaluate(
                    payload(
                        reproduction=gap,
                        hostGatePassed=True,
                        physicalGate="passed",
                        tempPath="/tmp/false-pass",
                    )
                )
                self.assert_contract(result)
                self.assertEqual(result["decision"], "unverified")
                if "missingPrerequisite" in gap:
                    self.assertIn(gap["missingPrerequisite"], result["openQuestions"])

    def test_invalid_payload_raises_value_error(self):
        valid = payload()
        invalid = [
            None,
            [],
            {},
            {**valid, "extra": 1},
            {key: valid[key] for key in valid if key != "physicalGate"},
            {**valid, "hostGatePassed": 1},
            {**valid, "hostGatePassed": "true"},
            {**valid, "physicalGate": "failed"},
            {**valid, "physicalGate": "pending "},
            {**valid, "physicalGate": "Pending"},
            {**valid, "physicalGate": None},
            {**valid, "tempPath": None},
            {**valid, "tempPath": 5},
            {**valid, "remoteCommit": "  "},
            {**valid, "statedSoftwareResult": ""},
            {**valid, "reproduction": []},
            {
                **valid,
                "reproduction": {**valid["reproduction"], "undocumentedFiles": "no"},
            },
            {
                **valid,
                "reproduction": {**valid["reproduction"], "manualIntervention": 0},
            },
            {
                **valid,
                "reproduction": {**valid["reproduction"], "phoneConnected": "yes"},
            },
            {
                **valid,
                "reproduction": {**valid["reproduction"], "missingPrerequisite": ""},
            },
            {
                **valid,
                "reproduction": {**valid["reproduction"], "missingPrerequisite": "  "},
            },
            {
                **valid,
                "reproduction": {**valid["reproduction"], "missingPrerequisite": False},
            },
            {
                **valid,
                "reproduction": {
                    key: valid["reproduction"][key]
                    for key in valid["reproduction"]
                    if key != "phoneConnected"
                },
            },
        ]
        for body in invalid:
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    gate.evaluate(body)


if __name__ == "__main__":
    unittest.main()
