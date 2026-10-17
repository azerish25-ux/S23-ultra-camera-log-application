"""Host checks for P151. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p151_generate_honest_release_notes_and_capability_badges",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p151_generate_honest_release_notes_and_capability_badges.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (_ROOT / "docs" / "P151_GENERATE_HONEST_RELEASE_NOTES_AND_CAPABILITY_BADGES.json").read_text(
            encoding="utf-8"
        )
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def claims_plus(extra: dict) -> list:
    return _MODULE.fixture_claims() + [extra]


class P151Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P151")
        self.assertEqual(_MODULE.WORKSTREAM, 19)
        self.assertEqual(_MODULE.TITLE, "Generate honest release notes and capability badges")
        self.assertEqual(
            _MODULE.GOAL,
            "Tie every public capability claim to current evidence and documented limits.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Build release summaries from accepted records, including exact supported tuples and "
            "experimental features. Separate software tests from physical qualification. Keep known "
            "failures visible and avoid general camera-equivalence or universal-resolution language.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A release with qualified SDR recording, experimental RAW development, and "
            "deferred-only depth effects.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The release notes reflect those scopes and do not advertise live RAW cinema capture "
            "or universal 8K support.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Copy aspirational requirements directly into the implemented features list.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Evidence-driven release notes and claim audit")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P150",))
        self.assertIn("unavailable", _MODULE.BADGE_RULE)
        self.assertIn("experimental", _MODULE.BADGE_RULE)
        self.assertIn("evidenced", _MODULE.BADGE_RULE)
        self.assertIn("evidence_id", _MODULE.BADGE_RULE)
        self.assertIn("implemented_features", _MODULE.BADGE_RULE)
        self.assertIn("must not read as shipped", _MODULE.BADGE_RULE)
        self.assertEqual(_MODULE.BADGES, frozenset({"unavailable", "experimental", "evidenced"}))

    def test_fixture_reflects_scopes_without_advertising(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P151")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("physical S23 was not run", result["reasons"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        self.assertIn(_MODULE.BADGE_RULE, " ".join(result["reasons"]))
        snapshot = result["preservedResults"][1]
        self.assertEqual(snapshot["badges"]["sdr-recording"], "evidenced")
        self.assertEqual(snapshot["badges"]["raw-development"], "experimental")
        self.assertEqual(snapshot["badges"]["depth-effects"], "experimental")
        self.assertEqual(snapshot["implementedFeatures"], ["sdr-recording"])
        self.assertNotIn("raw-development", snapshot["implementedFeatures"])
        self.assertNotIn("depth-effects", snapshot["implementedFeatures"])
        self.assertTrue(snapshot["scopesReflected"])
        self.assertFalse(snapshot["physicalS23Run"])
        self.assertEqual(snapshot["knownFailures"], list(_MODULE.KNOWN_FAILURES))
        self.assertEqual(snapshot["aspirationalCopied"], [])
        notes = " ".join(snapshot["releaseNotes"])
        self.assertIn("qualified SDR recording", notes)
        self.assertIn("experimental RAW development", notes)
        self.assertIn("deferred-only depth effects", notes)
        self.assertIn("known failure:", notes)
        self.assertNotIn(_MODULE.LIVE_RAW_ADVERTISED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.UNIVERSAL_8K_ADVERTISED, result["rejectedClaims"])
        self.assertEqual(evaluate(source)["decision"], "recorded")
        self.assertEqual(evaluate(_MODULE.core_payload())["decision"], "recorded")

    def test_copying_aspirational_requirements_is_rejected(self):
        result = assess(
            document(
                implementedFeatures=["sdr-recording", "live-raw-cinema-capture", "universal-8k"]
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.ASPIRATIONAL_COPIED, result["rejectedClaims"])
        self.assertIn(_MODULE.LIVE_RAW_ADVERTISED, result["rejectedClaims"])
        self.assertIn(_MODULE.UNIVERSAL_8K_ADVERTISED, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertIn("p151-release-notes", result["preservedResults"])
        self.assertEqual(
            result["preservedResults"][1]["aspirationalCopied"],
            ["live-raw-cinema-capture", "universal-8k"],
        )

    def test_apply_mutant_copies_aspirational_requirements(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ASPIRATIONAL_COPIED, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("live-raw-cinema-capture", result["preservedResults"][1]["implementedFeatures"])
        self.assertIn("universal-8k", result["preservedResults"][1]["implementedFeatures"])
        self.assertIn("p151-release-notes", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_null_evidence_outside_implemented_features_is_recorded(self):
        claims = claims_plus({
            "claim_id": "unmeasured-gate",
            "badge": "experimental",
            "evidence_id": None,
            "limit": "no accepted evidence yet",
        })
        result = assess(document(claims=claims))
        self.assertEqual(result["decision"], "recorded")
        self.assertIsNone(result["preservedResults"][1]["evidenceIds"]["unmeasured-gate"])
        self.assertNotIn(_MODULE.NULL_EVIDENCE_IMPLEMENTED, result["rejectedClaims"])

    def test_null_evidence_in_implemented_features_is_rejected(self):
        claims = claims_plus({
            "claim_id": "unmeasured-gate",
            "badge": "experimental",
            "evidence_id": None,
            "limit": "no accepted evidence yet",
        })
        result = assess(
            document(claims=claims, implementedFeatures=["sdr-recording", "unmeasured-gate"])
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NULL_EVIDENCE_IMPLEMENTED, result["rejectedClaims"])
        self.assertIn(_MODULE.EXPERIMENTAL_IMPLEMENTED, result["rejectedClaims"])
        self.assertIn("evidence_id null", " ".join(result["reasons"]))
        self.assertIn("p151-release-notes", result["preservedResults"])

    def test_unavailable_must_not_read_as_shipped(self):
        parked = {
            "claim_id": "optional-denoise",
            "badge": "unavailable",
            "evidence_id": "ev-denoise-absent",
            "limit": "not shipped",
        }
        recorded = assess(document(claims=claims_plus(parked)))
        self.assertEqual(recorded["decision"], "recorded")
        shipped = assess(
            document(
                claims=claims_plus(parked),
                implementedFeatures=["sdr-recording", "optional-denoise"],
            )
        )
        self.assertEqual(shipped["decision"], "rejected")
        self.assertIn(_MODULE.UNAVAILABLE_SHIPPED, shipped["rejectedClaims"])
        self.assertNotIn(_MODULE.NULL_EVIDENCE_IMPLEMENTED, shipped["rejectedClaims"])
        wording = dict(parked)
        wording["limit"] = "shipped"
        wording["claim_id"] = "optional-grade"
        read_as_shipped = assess(document(claims=claims_plus(wording)))
        self.assertEqual(read_as_shipped["decision"], "rejected")
        self.assertIn(_MODULE.UNAVAILABLE_SHIPPED, read_as_shipped["rejectedClaims"])

    def test_live_raw_and_universal_8k_advertising_is_rejected(self):
        live = assess(
            document(
                claims=claims_plus({
                    "claim_id": "live-raw-cinema-capture",
                    "badge": "experimental",
                    "evidence_id": "ev-live-raw",
                    "limit": "experimental only",
                })
            )
        )
        self.assertEqual(live["decision"], "rejected")
        self.assertIn(_MODULE.LIVE_RAW_ADVERTISED, live["rejectedClaims"])
        self.assertNotIn(_MODULE.ASPIRATIONAL_COPIED, live["rejectedClaims"])
        universal = assess(
            document(
                claims=claims_plus({
                    "claim_id": "delivery-sizes",
                    "badge": "evidenced",
                    "evidence_id": "ev-sizes",
                    "limit": "supports universal 8K",
                })
            )
        )
        self.assertEqual(universal["decision"], "rejected")
        self.assertIn(_MODULE.UNIVERSAL_8K_ADVERTISED, universal["rejectedClaims"])
        negated = assess(
            document(
                claims=claims_plus({
                    "claim_id": "delivery-sizes",
                    "badge": "evidenced",
                    "evidence_id": "ev-sizes",
                    "limit": "not universal 8K",
                })
            )
        )
        self.assertEqual(negated["decision"], "recorded")

    def test_camera_equivalence_and_universal_resolution_language_is_rejected(self):
        camera = assess(
            document(
                claims=claims_plus({
                    "claim_id": "look-match",
                    "badge": "experimental",
                    "evidence_id": "ev-look",
                    "limit": "camera-equivalence with a cinema camera",
                })
            )
        )
        self.assertEqual(camera["decision"], "rejected")
        self.assertIn(_MODULE.CAMERA_EQUIVALENCE, camera["rejectedClaims"])
        resolution = assess(
            document(
                claims=claims_plus({
                    "claim_id": "scaler",
                    "badge": "experimental",
                    "evidence_id": "ev-scaler",
                    "limit": "universal resolution output",
                })
            )
        )
        self.assertEqual(resolution["decision"], "rejected")
        self.assertIn(_MODULE.UNIVERSAL_RESOLUTION, resolution["rejectedClaims"])

    def test_missing_scope_is_rejected_and_evidence_remains(self):
        claims = [claim for claim in _MODULE.fixture_claims() if claim["claim_id"] != "depth-effects"]
        result = assess(document(claims=claims))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SCOPE_NOT_REFLECTED, result["rejectedClaims"])
        self.assertIn(_MODULE.ORACLE, result["reasons"])
        self.assertFalse(result["preservedResults"][1]["scopesReflected"])
        self.assertIn("p151-release-notes", result["preservedResults"])
        self.assertIn("physical S23 was not run", result["preservedResults"][1]["knownFailures"])

    def test_experimental_feature_is_not_implemented(self):
        result = assess(document(implementedFeatures=["sdr-recording", "raw-development"]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EXPERIMENTAL_IMPLEMENTED, result["rejectedClaims"])
        self.assertIn(_MODULE.SCOPE_NOT_REFLECTED, result["rejectedClaims"])

    def test_evidenced_without_evidence_or_limit_raises(self):
        broken_evidence = _MODULE.fixture_claims()
        broken_evidence[0] = {
            "claim_id": "sdr-recording",
            "badge": "evidenced",
            "evidence_id": None,
            "limit": _MODULE.SDR_LIMIT,
        }
        broken_limit = _MODULE.fixture_claims()
        broken_limit[0] = {
            "claim_id": "sdr-recording",
            "badge": "evidenced",
            "evidence_id": "ev-sdr-recording",
            "limit": "",
        }
        qualified_badge = _MODULE.fixture_claims()
        qualified_badge[0] = dict(qualified_badge[0])
        qualified_badge[0]["badge"] = "qualified"
        for claims in (broken_evidence, broken_limit, qualified_badge):
            with self.assertRaises(ValueError):
                assess(document(claims=claims))

    def test_second_evidence_id_is_preserved(self):
        evidence = "p151-repeat-source-modes"
        result = evaluate(_MODULE.core_payload(evidenceId=evidence))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["caseId"], "P151")
        self.assertIn(evidence, result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P152"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(claims=[]),
            document(implementedFeatures=["not-a-claim"]),
            document(knownFailures=["", "x"]),
            document(claims=[]),
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload)
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        # An empty claim list with no implemented ids is structurally valid and fails the oracle.
        empty = assess(document(claims=[], implementedFeatures=[]))
        self.assertEqual(empty["decision"], "rejected")
        self.assertIn(_MODULE.SCOPE_NOT_REFLECTED, empty["rejectedClaims"])

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P151-handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(handoff["phase"], "P151")
        self.assertEqual(handoff["nextPhase"], "P152")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p151*.py' -v",
        )
        self.assertIn("physical S23 capture", handoff["unverified"])
        note = (_ROOT / "docs" / "P151_GENERATE_HONEST_RELEASE_NOTES_AND_CAPABILITY_BADGES.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Evidence-driven release notes and claim audit", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn(_MODULE.BADGE_RULE, note)
        self.assertIn("evidence_id", note)
        self.assertIn("implemented_features", note)
        self.assertIn("unavailable", note)
        self.assertIn("experimental", note)
        self.assertIn("evidenced", note)
        self.assertIn("live RAW cinema capture", note)
        self.assertIn("universal 8K", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("never `qualified` or `allowed`", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p151_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p151_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P151-0{index}")
            self.assertEqual(module.CASE["phase"], "P151")
            self.assertEqual(module.CASE["workstream"], 19)
            with self.assertRaises(ValueError):
                module.evaluate({})
            with self.assertRaises(ValueError):
                module.evaluate([])
