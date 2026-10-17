"""Host checks for P133. Not a physical S23 probe."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "p133_implement_accessible_focus_and_recipe_controls",
    Path(__file__).resolve().parents[1]
    / "gates"
    / "p133_implement_accessible_focus_and_recipe_controls.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def load_document() -> dict:
    return json.loads(
        (
            _ROOT / "docs" / "P133_IMPLEMENT_ACCESSIBLE_FOCUS_AND_RECIPE_CONTROLS.json"
        ).read_text(encoding="utf-8")
    )


def document(**overrides):
    value = _MODULE.fixture_document()
    value.update(overrides)
    return value


def with_controls(controls, focus_order=None, **overrides):
    value = document()
    value["controls"] = controls
    value["focusOrder"] = list(_MODULE.fixture_focus_order() if focus_order is None else focus_order)
    value.update(overrides)
    return value


def audit_of(result):
    return result["preservedResults"][1]


class P133Tests(unittest.TestCase):
    def test_phase_constants_match_the_spec(self):
        self.assertEqual(_MODULE.BASE_REVISION, "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b")
        self.assertEqual(_MODULE.PHASE, "P133")
        self.assertEqual(_MODULE.WORKSTREAM, 17)
        self.assertEqual(_MODULE.TITLE, "Implement accessible focus and recipe controls")
        self.assertEqual(
            _MODULE.GOAL,
            "Make visual editing possible without relying solely on tiny unlabeled gestures.",
        )
        self.assertEqual(
            _MODULE.METHOD,
            "Provide accessible names, state descriptions, keyboard or switch navigation where applicable, "
            "and numeric alternatives for ROIs and focus controls. Do not convey failure only through color. "
            "Preserve focus order across panels and orientation changes.",
        )
        self.assertEqual(
            _MODULE.FIXTURE,
            "A screen-reader user selects a grey-reference ROI, changes virtual focus, "
            "and cancels a development job.",
        )
        self.assertEqual(
            _MODULE.ORACLE,
            "All actions have usable labels and state feedback, and cancellation remains "
            "available without a precision gesture.",
        )
        self.assertEqual(_MODULE.MUTANT, "Expose a custom control only as an unlabeled canvas.")
        self.assertEqual(_MODULE.DELIVERABLE, "Accessibility interaction tests and semantic control audit")
        self.assertEqual(_MODULE.DEPENDENCIES, ("P132",))
        self.assertEqual(_MODULE.MIN_TARGET_DP, 48)
        self.assertIn("accessible_name", _MODULE.ACCESSIBILITY_RULE)
        self.assertIn("record and stop", _MODULE.ACCESSIBILITY_RULE)
        self.assertIn("below 48", _MODULE.ACCESSIBILITY_RULE)

    def test_fixture_records_named_focus_and_recipe_controls(self):
        source = load_document()
        self.assertEqual(source, _MODULE.fixture_document())
        result = assess(source)
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "P133")
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn(source["evidenceId"], result["preservedResults"])
        self.assertIn(source["claim"], result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("minimumTargetSize=48", result["reasons"])
        self.assertIn("focus order includes record and stop", result["reasons"])
        self.assertIn("recipe controls are separate from capture controls", result["reasons"])
        self.assertIn("cancellation available without a precision gesture", result["reasons"])
        record = audit_of(result)
        self.assertEqual(record["minimumTargetSize"], 48)
        self.assertEqual(record["minimumTargetThreshold"], 48)
        self.assertTrue(record["focusIncludesRecord"])
        self.assertTrue(record["focusIncludesStop"])
        self.assertEqual(record["focusOrder"][0], "record")
        self.assertIn("stop", record["focusOrder"])
        self.assertTrue(record["recipeSeparate"])
        self.assertTrue(record["cancelAvailable"])
        self.assertEqual(record["unlabeledCanvasIds"], [])
        self.assertEqual(record["undersizedIds"], [])
        self.assertEqual(record["recipeIds"], ["film-recipe", "recipe-evidence"])
        self.assertEqual(record["captureIds"], ["record", "stop", "source-status"])
        self.assertFalse(set(record["recipeIds"]) & set(record["captureIds"]))

    def test_evaluate_uses_the_same_accessibility_rule(self):
        result = evaluate(
            {
                "caseId": "TC-P133-05",
                "evidenceId": "p133-evaluate",
                "applyMutant": False,
                "controls": _MODULE.fixture_controls(),
                "focusOrder": _MODULE.fixture_focus_order(),
            }
        )
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P133-05")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p133-evaluate", result["preservedResults"])
        self.assertEqual(audit_of(result)["minimumTargetSize"], 48)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_empty_accessible_name_is_an_unlabeled_canvas(self):
        controls = _MODULE.replace_control(
            _MODULE.fixture_controls(), "virtual-focus", accessible_name=""
        )
        result = assess(with_controls(controls))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLABELED_CANVAS, result["rejectedClaims"])
        self.assertIn("virtual-focus", audit_of(result)["unlabeledCanvasIds"])
        self.assertIn("p133-accessible-focus-recipe", result["preservedResults"])
        self.assertIn(_MODULE.MUTANT, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_canvas_role_without_a_name_is_rejected(self):
        controls = _MODULE.fixture_controls()
        controls.append(
            _MODULE.make_control(
                "custom-canvas",
                "",
                "canvas",
                "button",
                family="capture",
                group="custom-canvas",
                state_description="unspoken gesture",
            )
        )
        order = _MODULE.fixture_focus_order() + ["custom-canvas"]
        result = assess(with_controls(controls, order))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLABELED_CANVAS, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NON_GESTURE_PATH_MISSING, result["rejectedClaims"])
        self.assertEqual(audit_of(result)["unlabeledCanvasIds"], ["custom-canvas"])

    def test_named_canvas_without_a_non_gesture_path_is_rejected(self):
        controls = _MODULE.fixture_controls()
        controls.append(
            _MODULE.make_control(
                "named-canvas",
                "Custom focus",
                "canvas",
                "canvas",
                family="capture",
                group="named-canvas",
                state_description="drawn only",
            )
        )
        order = _MODULE.fixture_focus_order() + ["named-canvas"]
        result = assess(with_controls(controls, order))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NON_GESTURE_PATH_MISSING, result["rejectedClaims"])
        self.assertNotIn(_MODULE.UNLABELED_CANVAS, result["rejectedClaims"])
        self.assertEqual(audit_of(result)["gestureOnlyIds"], ["named-canvas"])

    def test_named_canvas_with_a_button_path_is_recorded(self):
        controls = _MODULE.fixture_controls()
        controls.append(
            _MODULE.make_control(
                "named-canvas",
                "Custom focus",
                "canvas",
                "button",
                family="focus",
                group="virtual-focus",
                state_description="button alternative",
            )
        )
        order = _MODULE.fixture_focus_order() + ["named-canvas"]
        result = assess(with_controls(controls, order))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_focus_order_must_include_record_and_stop(self):
        order = [item for item in _MODULE.fixture_focus_order() if item != "stop"]
        result = assess(with_controls(_MODULE.fixture_controls(), order))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOCUS_ORDER_MISSING_RECORD_STOP, result["rejectedClaims"])
        self.assertIn(_MODULE.FOCUS_ORDER_SKIPS_CONTROL, result["rejectedClaims"])
        self.assertFalse(audit_of(result)["focusIncludesStop"])
        self.assertTrue(audit_of(result)["focusIncludesRecord"])
        self.assertIn("p133-accessible-focus-recipe", result["preservedResults"])

    def test_size_below_48_without_an_alternative_is_rejected_and_reported(self):
        controls = _MODULE.replace_control(_MODULE.fixture_controls(), "record", target_size=47.9)
        result = assess(with_controls(controls))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDERSIZED_WITHOUT_ALTERNATIVE, result["rejectedClaims"])
        self.assertEqual(audit_of(result)["minimumTargetSize"], 47.9)
        self.assertIn("minimumTargetSize=47.9", result["reasons"])
        self.assertEqual(audit_of(result)["undersizedIds"], ["record"])
        self.assertIn("p133-accessible-focus-recipe", result["preservedResults"])

    def test_size_below_48_with_a_labeled_alternative_is_recorded(self):
        controls = _MODULE.replace_control(_MODULE.fixture_controls(), "virtual-focus", target_size=32)
        controls.append(
            _MODULE.make_control(
                "virtual-focus-stepper",
                "Virtual focus distance",
                "stepper",
                "stepper",
                target_size=48,
                family="focus",
                group="virtual-focus",
                state_description="2.8 m",
            )
        )
        order = _MODULE.fixture_focus_order() + ["virtual-focus-stepper"]
        result = assess(with_controls(controls, order))
        self.assertEqual(result["decision"], "recorded", result["rejectedClaims"])
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(audit_of(result)["minimumTargetSize"], 32)
        self.assertIn("minimumTargetSize=32", result["reasons"])
        self.assertEqual(audit_of(result)["undersizedIds"], [])

    def test_an_unlabeled_sibling_is_not_an_alternative(self):
        controls = _MODULE.replace_control(_MODULE.fixture_controls(), "record", target_size=24)
        controls.append(
            _MODULE.make_control(
                "record-gesture",
                "",
                "button",
                "button",
                target_size=64,
                family="capture",
                group="record",
                state_description="hidden",
            )
        )
        order = _MODULE.fixture_focus_order() + ["record-gesture"]
        result = assess(with_controls(controls, order))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDERSIZED_WITHOUT_ALTERNATIVE, result["rejectedClaims"])
        self.assertIn(_MODULE.UNLABELED_CANVAS, result["rejectedClaims"])

    def test_recipe_controls_that_share_a_capture_group_are_rejected(self):
        controls = _MODULE.replace_control(_MODULE.fixture_controls(), "film-recipe", group="record")
        result = assess(with_controls(controls))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RECIPE_NOT_SEPARATE, result["rejectedClaims"])
        self.assertFalse(audit_of(result)["recipeSeparate"])
        self.assertEqual(audit_of(result)["sharedGroups"], ["record"])
        self.assertIn("film-recipe", audit_of(result)["recipeIds"])
        self.assertIn("record", audit_of(result)["captureIds"])
        self.assertIn("p133-accessible-focus-recipe", result["preservedResults"])

    def test_moving_a_recipe_onto_the_capture_panel_is_rejected(self):
        controls = _MODULE.replace_control(_MODULE.fixture_controls(), "film-recipe", panel="capture")
        result = assess(with_controls(controls))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.RECIPE_NOT_SEPARATE, result["rejectedClaims"])
        self.assertIn(_MODULE.PANEL_MISMATCH, result["rejectedClaims"])

    def test_apply_mutant_rejects_a_clean_surface(self):
        result = assess(document(applyMutant=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNLABELED_CANVAS, result["rejectedClaims"])
        self.assertIn("mutant rejected: " + _MODULE.MUTANT, result["reasons"])
        self.assertIn("p133-accessible-focus-recipe", result["preservedResults"])
        self.assertEqual(audit_of(result)["minimumTargetSize"], 48)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_color_only_failure_and_missing_state_are_rejected(self):
        colored = assess(
            with_controls(
                _MODULE.replace_control(
                    _MODULE.fixture_controls(), "cancel-development", color_only_failure=True
                )
            )
        )
        self.assertEqual(colored["decision"], "rejected")
        self.assertIn(_MODULE.COLOR_ONLY, colored["rejectedClaims"])
        self.assertIn(_MODULE.CANCEL_UNAVAILABLE, colored["rejectedClaims"])
        silent = assess(
            with_controls(
                _MODULE.replace_control(_MODULE.fixture_controls(), "virtual-focus", state_description="")
            )
        )
        self.assertEqual(silent["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_STATE, silent["rejectedClaims"])

    def test_focus_without_a_numeric_path_is_rejected(self):
        controls = _MODULE.replace_control(
            _MODULE.fixture_controls(), "virtual-focus", role="button", path="button"
        )
        result = assess(with_controls(controls))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_NUMERIC, result["rejectedClaims"])

    def test_invalid_payloads_raise(self):
        controls = _MODULE.fixture_controls()
        broken_name = _MODULE.replace_control(controls, "record", accessible_name=" Record")
        duplicate = controls + [dict(controls[0])]
        invalid = [
            {},
            [],
            document(schemaVersion=2),
            document(phase="P134"),
            document(implementationBaseRevision="deadbeef"),
            document(applyMutant="no"),
            document(extra=True),
            with_controls([]),
            with_controls(broken_name),
            with_controls(duplicate),
            with_controls(controls, ["record", "record"]),
            with_controls(controls, ["nope"]),
            with_controls(_MODULE.replace_control(controls, "record", role="link")),
            with_controls(_MODULE.replace_control(controls, "record", path="swipe")),
            with_controls(_MODULE.replace_control(controls, "record", target_size=0)),
            with_controls(_MODULE.replace_control(controls, "record", target_size=True)),
            with_controls(_MODULE.replace_control(controls, "record", color_only_failure="no")),
            {
                "caseId": "TC-P133-05",
                "evidenceId": "p133-evaluate",
                "applyMutant": False,
                "controls": controls,
            },
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    if isinstance(payload, dict) and "caseId" in payload and "phase" not in payload:
                        evaluate(payload)
                    else:
                        assess(payload)

    def test_handoff_and_note_keep_the_non_claims(self):
        handoff = json.loads((_ROOT / "docs" / "evidence" / "P133-handoff.json").read_text())
        self.assertEqual(handoff["phase"], "P133")
        self.assertEqual(handoff["nextPhase"], "P134")
        self.assertIsNone(handoff["commit"])
        self.assertEqual(handoff["failures"], 0)
        self.assertEqual(
            handoff["nonClaims"],
            "Host reference only. Not a physical S23 qualification.",
        )
        self.assertEqual(
            handoff["testsRun"],
            "python3 -m unittest discover -s scripts/tests -p 'test_p133*.py' -v",
        )
        note = (_ROOT / "docs" / "P133_IMPLEMENT_ACCESSIBLE_FOCUS_AND_RECIPE_CONTROLS.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Accessibility interaction tests and semantic control audit", note)
        self.assertIn("not a physical S23 measurement", note)
        self.assertIn("sensor-derived Log", note)
        self.assertIn("ten-bit fidelity", note)
        self.assertIn("film-stock fidelity", note)
        self.assertIn("cinema-camera equivalence", note)
        self.assertIn("accessible_name", note)
        self.assertIn("below 48", note)
        self.assertIn("record", note)
        self.assertIn("recipe", note)

    def test_case_modules_match_the_spec_and_reject_invalid_payloads(self):
        expected = {
            1: ("Landscape and large-text stress", "Critical actions hidden inside scrolling content must fail."),
            2: ("Source-look label confusion", "Renaming a source mode after the virtual format must fail."),
            3: ("Invalid control draft", "Partially typed input reaching the camera must fail."),
            4: (
                "Stale or wrong-domain scope",
                "An RGB8 preview histogram must not certify source bit depth or sensor clipping.",
            ),
            5: ("Nonvisual interaction", "An unlabeled custom canvas as the only control must fail."),
            6: (
                "Premature success indication",
                "A one-hundred-percent banner before required verification must fail.",
            ),
            7: ("Unfair comparison view", "Automatically enhancing one side of a comparison must fail."),
            8: (
                "Real shooting interruption",
                "A desktop mockup cannot substitute for observed physical task completion.",
            ),
        }
        for index in range(1, 9):
            path = Path(__file__).resolve().parents[1] / "gates" / f"p133_tc0{index}.py"
            spec = importlib.util.spec_from_file_location(f"p133_tc0{index}_loaded", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CASE["id"], f"TC-P133-0{index}")
            self.assertEqual(module.CASE["phase"], "P133")
            self.assertEqual(module.CASE["workstream"], 17)
            self.assertEqual(module.CASE["name"], expected[index][0])
            self.assertEqual(module.CASE["negative"], expected[index][1])
            with self.assertRaises(ValueError):
                module.evaluate({})
