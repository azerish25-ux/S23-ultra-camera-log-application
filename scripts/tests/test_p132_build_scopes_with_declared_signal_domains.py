"""Host checks for P132. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p132_build_scopes_with_declared_signal_domains",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p132_build_scopes_with_declared_signal_domains.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (
            _ROOT / "docs" / "P132_BUILD_SCOPES_WITH_DECLARED_SIGNAL_DOMAINS.json"
        ).read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def scopes_with(scope_id, **overrides):
    return _MODULE.replace_scope(_MODULE.fixture_scopes(), scope_id, **overrides)


def record_of(result):
    return result["preservedResults"][1]


def scope_record(result, scope_id):
    matches = [item for item in record_of(result)["scopes"] if item["id"] == scope_id]
    if len(matches) != 1:
        raise AssertionError(scope_id)
    return matches[0]


class P132Tests(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-signal-domains"):
        self.assertEqual(tuple(result), KEYS)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.DOMAIN_RULE, result["reasons"])

    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P132")
        self.assertEqual(_MODULE.WORKSTREAM, 17)
        self.assertEqual(_MODULE.TITLE, "Build scopes with declared signal domains")
        self.assertEqual(
            _MODULE.GOAL,
            "Make waveform, histogram, clipping, and false color informative rather than misleading.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Label whether a scope measures source, working image, encoded Log, or display preview. "
            "Record sampling resolution and freshness. Preview-only RGB8 aids cannot certify sensor "
            "clipping or ten-bit precision. Keep scope computation off critical capture ownership.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A clipped display preview of an unclipped high-range source and a stale waveform "
            "after inference load spikes.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "The scope identifies its domain and stale status rather than falsely declaring "
            "source clipping from the preview.",
        )
        self.assertEqual(
            _MODULE.MUTANT,
            "Label every preview histogram sensor exposure regardless of its input.",
        )
        self.assertEqual(_MODULE.DELIVERABLE, "Scope domain model and monitoring correctness tests")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P131",))

    def test_fixture_records_domains_and_retains_clipping_counts(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assert_contract(result)
        self.assertEqual(result["caseId"], "P132")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn(_MODULE.ORACLE, " ".join(result["reasons"]))
        kept = record_of(result)
        self.assertEqual(kept["sourceDomain"], "sensor_code")
        self.assertEqual(kept["sourceClippingCount"], 0)
        self.assertEqual(kept["previewClippingCount"], 3)
        self.assertTrue(kept["highRange"])
        self.assertEqual(kept["staleScopeIds"], ["stale-waveform"])
        clipping = scope_record(result, "preview-clipping")
        self.assertEqual(clipping["clippingCount"], 3)
        self.assertEqual(clipping["domain"], "display_sdr")
        self.assertEqual(clipping["threshold"], 0.95)
        waveform = scope_record(result, "stale-waveform")
        self.assertEqual(waveform["domain"], "display_sdr")
        self.assertFalse(waveform["fresh"])
        self.assertIn(
            "scope stale-waveform kind=waveform domain=display_sdr freshness=stale samplingResolution=rgb8",
            " ".join(result["reasons"]),
        )
        self.assertIn("clippingCount[preview-clipping]=3 threshold=0.95", result["reasons"])
        self.assertIn("inputDomain[preview-false-color]=display_sdr", result["reasons"])
        self.assertEqual(scope_record(result, "preview-false-color")["inputDomain"], "display_sdr")
        self.assertEqual(_MODULE.clipping_count([0.95, 0.96, 0.95], 0.95), 1)
        self.assertEqual(_MODULE.clipping_count([[10, 10, 10], [255, 0, 0], [250, 250, 250]], 250), 1)

    def test_evaluate_accepts_a_scope_payload_and_a_document(self):
        payload = {
            "caseId": "P132-payload",
            "evidenceId": "p132-eval",
            "claim": _MODULE.CLAIM,
            "scopes": _MODULE.fixture_scopes(),
            "source": _MODULE.fixture_source(),
            "applyMutant": False,
        }
        result = evaluate(payload)
        self.assert_contract(result, "p132-eval")
        self.assertEqual(result["caseId"], "P132-payload")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(record_of(result)["previewClippingCount"], 3)
        same = evaluate(_MODULE.fixture_document())
        self.assertEqual(same["decision"], "recorded")
        self.assertEqual(same["caseId"], "P132")

    def test_display_rgb_histogram_labelled_sensor_exposure_is_rejected(self):
        scopes = scopes_with(
            "preview-histogram",
            domain="hlg_signal",
            sampleEncoding="display_rgb",
            label=_MODULE.SENSOR_EXPOSURE,
            samplingResolution="ten_bit",
            priorLabel=None,
        )
        result = assess(document(scopes=scopes))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DISPLAY_RGB_HISTOGRAM_LABELLED_SENSOR_EXPOSURE, result["rejectedClaims"])
        self.assertIn(_MODULE.MUTANT_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.RELABELLED_DISPLAY_HISTOGRAM, result["rejectedClaims"])
        self.assertNotIn(_MODULE.UNKNOWN_OR_MISSING_DOMAIN_SENSOR_EXPOSURE, result["rejectedClaims"])
        self.assertEqual(record_of(result)["previewClippingCount"], 3)
        self.assertIn("p132-signal-domains", result["preservedResults"])

    def test_unknown_or_missing_domain_labelled_sensor_exposure_is_rejected(self):
        unknown = scopes_with(
            "stale-waveform",
            domain="unknown",
            label=_MODULE.SENSOR_EXPOSURE,
            fresh=True,
            sampleEncoding="unspecified",
            samplingResolution="ten_bit",
        )
        unknown_result = assess(document(scopes=unknown))
        self.assertEqual(unknown_result["decision"], "rejected")
        self.assertEqual(
            unknown_result["rejectedClaims"],
            [_MODULE.UNKNOWN_OR_MISSING_DOMAIN_SENSOR_EXPOSURE],
        )
        self.assertEqual(scope_record(unknown_result, "stale-waveform")["domain"], "unknown")
        missing = scopes_with(
            "stale-waveform",
            domain=None,
            label=_MODULE.SENSOR_EXPOSURE,
            fresh=True,
            sampleEncoding="unspecified",
            samplingResolution="ten_bit",
        )
        missing_result = assess(document(scopes=missing))
        self.assertEqual(missing_result["decision"], "rejected")
        self.assertEqual(
            missing_result["rejectedClaims"],
            [_MODULE.UNKNOWN_OR_MISSING_DOMAIN_SENSOR_EXPOSURE],
        )
        self.assertEqual(scope_record(missing_result, "stale-waveform")["domain"], "missing")
        self.assertEqual(record_of(missing_result)["sourceClippingCount"], 0)

    def test_relabeling_a_display_histogram_as_sensor_exposure_is_rejected(self):
        scopes = scopes_with(
            "preview-histogram",
            domain="display_sdr",
            sampleEncoding="unspecified",
            samples=[0.2, 0.4, 0.5],
            label=_MODULE.SENSOR_EXPOSURE,
            priorLabel="display_preview",
            samplingResolution="ten_bit",
        )
        extra = _MODULE.make_scope(
            id="kept-preview-histogram",
            kind="histogram",
            domain="display_sdr",
            sampleEncoding="display_rgb",
            label="display_preview",
            samples=[[1, 2, 3]],
            samplingResolution="rgb8",
            fresh=True,
        )
        result = assess(document(scopes=scopes + [extra]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RELABELLED_DISPLAY_HISTOGRAM, result["rejectedClaims"])
        self.assertNotIn(_MODULE.DISPLAY_RGB_HISTOGRAM_LABELLED_SENSOR_EXPOSURE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.MUTANT_TOKEN, result["rejectedClaims"])
        prior_only = scopes_with(
            "preview-histogram",
            domain="sensor_code",
            sampleEncoding="sensor_code",
            samples=[10, 20, 30],
            label=_MODULE.SENSOR_EXPOSURE,
            priorLabel="display_histogram",
            samplingResolution="sensor",
        )
        prior_result = assess(document(scopes=prior_only))
        self.assertEqual(prior_result["decision"], "rejected")
        self.assertEqual(prior_result["rejectedClaims"], [_MODULE.RELABELLED_DISPLAY_HISTOGRAM])

    def test_sensor_histogram_may_be_labelled_sensor_exposure(self):
        scopes = scopes_with(
            "preview-histogram",
            domain="sensor_code",
            sampleEncoding="sensor_code",
            label=_MODULE.SENSOR_EXPOSURE,
            samples=[100, 200, 400, 800],
            samplingResolution="sensor",
            priorLabel=None,
        )
        result = assess(document(scopes=scopes))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(scope_record(result, "preview-histogram")["label"], "sensor_exposure")
        self.assertEqual(scope_record(result, "preview-histogram")["domain"], "sensor_code")

    def test_false_color_must_name_its_input_domain(self):
        missing = scopes_with("preview-false-color", inputDomain=None)
        missing_result = assess(document(scopes=missing))
        self.assertEqual(missing_result["decision"], "rejected")
        self.assertIn(_MODULE.FALSE_COLOR_UNNAMED_DOMAIN, missing_result["rejectedClaims"])
        unknown = scopes_with("preview-false-color", inputDomain="unknown")
        unknown_result = assess(document(scopes=unknown))
        self.assertEqual(unknown_result["decision"], "rejected")
        self.assertIn(_MODULE.FALSE_COLOR_UNNAMED_DOMAIN, unknown_result["rejectedClaims"])
        disagree = scopes_with("preview-false-color", inputDomain="hlg_signal")
        disagree_result = assess(document(scopes=disagree))
        self.assertEqual(disagree_result["decision"], "rejected")
        self.assertIn(_MODULE.FALSE_COLOR_DOMAIN_MISMATCH, disagree_result["rejectedClaims"])
        self.assertNotIn(_MODULE.FALSE_COLOR_UNNAMED_DOMAIN, disagree_result["rejectedClaims"])
        named = scopes_with(
            "preview-false-color",
            domain="hlg_signal",
            inputDomain="hlg_signal",
            sampleEncoding="hlg_signal",
            samplingResolution="ten_bit",
        )
        named_result = assess(document(scopes=named))
        self.assertEqual(named_result["decision"], "recorded")
        self.assertEqual(scope_record(named_result, "preview-false-color")["inputDomain"], "hlg_signal")

    def test_clipping_count_uses_samples_strictly_above_the_threshold(self):
        scopes = scopes_with(
            "preview-clipping",
            samples=[[10, 10, 10], [255, 0, 0], [250, 250, 250]],
            threshold=250,
            claimedClippingCount=1,
        )
        result = assess(document(scopes=scopes))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(scope_record(result, "preview-clipping")["clippingCount"], 1)
        self.assertEqual(record_of(result)["previewClippingCount"], 1)
        self.assertEqual(record_of(result)["sourceClippingCount"], 0)
        mismatched = scopes_with("preview-clipping", claimedClippingCount=99)
        rejected = assess(document(scopes=mismatched))
        self.assertEqual(rejected["decision"], "rejected")
        self.assertIn(_MODULE.CLAIMED_CLIP_MISMATCH, rejected["rejectedClaims"])
        self.assertEqual(scope_record(rejected, "preview-clipping")["clippingCount"], 3)
        self.assertIn("p132-signal-domains", rejected["preservedResults"])
        undeclared = scopes_with("preview-clipping", threshold=None, claimedClippingCount=None)
        undeclared_result = assess(document(scopes=undeclared))
        self.assertEqual(undeclared_result["decision"], "rejected")
        self.assertIn(_MODULE.CLIPPING_THRESHOLD_UNDECLARED, undeclared_result["rejectedClaims"])
        self.assertIsNone(scope_record(undeclared_result, "preview-clipping")["clippingCount"])

    def test_preview_must_not_declare_source_clipping_or_rgb8_precision(self):
        declared = scopes_with("preview-clipping", declaresSourceClipping=True)
        declared_result = assess(document(scopes=declared))
        self.assertEqual(declared_result["decision"], "rejected")
        self.assertIn(_MODULE.PREVIEW_DECLARES_SOURCE_CLIPPING, declared_result["rejectedClaims"])
        self.assertEqual(record_of(declared_result)["sourceClippingCount"], 0)
        self.assertEqual(record_of(declared_result)["previewClippingCount"], 3)
        rgb8 = scopes_with(
            "preview-histogram",
            certifiesSensorClipping=True,
            certifiesSourceBitDepth=True,
            certifiesTenBit=True,
        )
        rgb8_result = assess(document(scopes=rgb8))
        self.assertEqual(rgb8_result["decision"], "rejected")
        self.assertIn(_MODULE.RGB8_CERTIFIES_SENSOR, rgb8_result["rejectedClaims"])
        self.assertIn(_MODULE.RGB8_CERTIFIES_BIT_DEPTH, rgb8_result["rejectedClaims"])
        self.assertIn(_MODULE.RGB8_CERTIFIES_TEN_BIT, rgb8_result["rejectedClaims"])
        stale = scopes_with("stale-waveform", label=_MODULE.SENSOR_EXPOSURE, fresh=False)
        stale_result = assess(document(scopes=stale))
        self.assertEqual(stale_result["decision"], "rejected")
        self.assertIn(_MODULE.STALE_REPORTS_SENSOR, stale_result["rejectedClaims"])
        owned = scopes_with("stale-waveform", ownsCapture=True)
        owned_result = assess(document(scopes=owned))
        self.assertEqual(owned_result["decision"], "rejected")
        self.assertIn(_MODULE.SCOPE_OWNS_CAPTURE, owned_result["rejectedClaims"])

    def test_mutant_that_labels_every_preview_histogram_is_rejected(self):
        flagged = assess(document(applyMutant=True))
        self.assert_contract(flagged)
        self.assertEqual(flagged["decision"], "rejected")
        self.assertEqual(flagged["rejectedClaims"], [_MODULE.MUTANT_TOKEN])
        self.assertIn(_MODULE.MUTANT, flagged["reasons"])
        self.assertEqual(record_of(flagged)["previewClippingCount"], 3)
        self.assertEqual(scope_record(flagged, "preview-histogram")["label"], "display_preview")
        self.assertIn("p132-signal-domains", flagged["preservedResults"])
        self.assertNotIn(flagged["decision"], {"qualified", "allowed"})

    def test_missing_kind_is_rejected_and_evidence_remains(self):
        scopes = [scope for scope in _MODULE.fixture_scopes() if scope["kind"] != "waveform"]
        result = assess(document(scopes=scopes))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_SCOPE_KIND + ":waveform", result["rejectedClaims"])
        self.assertIn("p132-signal-domains", result["preservedResults"])

    def test_invalid_payloads_raise(self):
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P133"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            document(scopes=scopes_with("preview-histogram", kind="vectorscope")),
            document(scopes=scopes_with("preview-histogram", domain="preview")),
            document(scopes=scopes_with("preview-clipping", samples=[])),
            document(scopes=scopes_with("preview-clipping", threshold=float("nan"))),
            document(scopes=scopes_with("preview-clipping", claimedClippingCount=True)),
            document(source={"domain": "unknown", "samples": [1], "threshold": 1, "highRange": True}),
            {"decision": "qualified"},
            {"decision": "allowed", "caseId": "P132"},
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    assess(payload) if index < 13 else evaluate(payload)

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P132-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P132")
        self.assertEqual(handoff["nextPhase"], "P133")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p132*.py' -v",
        )
        note = (_ROOT / "docs" / "P132_BUILD_SCOPES_WITH_DECLARED_SIGNAL_DOMAINS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Scope domain model and monitoring correctness tests", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("sensor_exposure", note)
        self.assertIn("display_sdr", note)

    def test_case_modules_reject_invalid_payloads(self):
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p132_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p132_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P132-0{index}")
            self.assertEqual(module.CASE["phase"], "P132")
            self.assertEqual(module.CASE["workstream"], 17)
            self.assertNotIn("applyNegative", module.PAYLOAD_KEYS)
            with self.assertRaises(ValueError):
                module.evaluate({})
