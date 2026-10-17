"""TC-P138-01 Missing production fact.

Host fixture. A removed lens or stock stays null. A plausible guess marked
documented is rejected. Creative reconstruction must be labelled and must not
invent the missing production fact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P138-01",
    "phase": "P138",
    "workstream": 18,
    "name": "Missing production fact",
    "intervention": "Remove verified lens or scene-specific stock information from an otherwise complete movie record.",
    "expected": "Keep the fact unknown while allowing a clearly labelled creative reconstruction.",
    "negative": "A plausible equipment guess marked documented must fail.",
    "repeat": "Repeat camera, lens, stock, process, and release-version fields.",
}

NEGATIVE_TOKEN = "plausible-guess-marked-documented"
UNLABELLED = "unlabelled-reconstruction"
MISSING_FIELDS = {"camera", "lens", "stock", "process", "release-version"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "family",
    "max_entries",
    "missingField",
    "guess",
    "guessDocumented",
    "reconstructionLabelled",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p138_build_the_first_sourced_recipe_family.py"
    spec = importlib.util.spec_from_file_location("p138_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_family_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    missing = _GATE.require_text(payload["missingField"], "missingField")
    _GATE.require(missing in MISSING_FIELDS, "missingField is not a production fact")
    guess_documented = _GATE.require_bool(payload["guessDocumented"], "guessDocumented")
    labelled = _GATE.require_bool(payload["reconstructionLabelled"], "reconstructionLabelled")
    guess = payload["guess"]
    if guess is not None:
        guess = _GATE.require_text(guess, "guess")
    if guess_documented:
        _GATE.require(guess is not None, "a documented guess requires a value")
    entries = bundle["analysis"]["entries"]
    has_reconstruction = any(entry["reconstruction"] for entry in entries)
    if has_reconstruction != labelled:
        faults.append(UNLABELLED)
    if missing in {"stock", "lens"}:
        for entry in entries:
            if entry[missing] == guess and guess is not None and not _GATE.has_trace(entry, missing):
                if guess_documented or entry["documented"]:
                    faults.append(NEGATIVE_TOKEN)
            if entry["reconstruction"] and entry[missing] is not None:
                faults.append(NEGATIVE_TOKEN if guess_documented or entry["documented"] else _GATE.INVENTED)
    elif guess is not None:
        faults.append(NEGATIVE_TOKEN if guess_documented else _GATE.INVENTED)
    if guess_documented:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "missingField": missing,
        "guess": guess,
        "keptUnknown": guess is None or not any(
            entry.get(missing) == guess for entry in entries if missing in entry
        ),
        "reconstructionLabelled": labelled and has_reconstruction,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"], UNLABELLED: "creative reconstruction must be clearly labelled"},
    )
