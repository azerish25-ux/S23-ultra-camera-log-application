# P143 — Support release-specific and scene-specific looks

Active phase: **P143**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Release-aware catalogue and ambiguity tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Release-aware catalogue and ambiguity tests

- Goal: Avoid treating every distribution version of a film as one fixed color target.
- Method: Record reference edition, format, display assumptions, and scene family when known. Permit several interpretations under one movie title. A missing edition remains unknown; the app must not infer a theatrical print response from an arbitrary screenshot.
- Fixture: Two legally obtained references from different releases with visibly different contrast and color treatment.
- Oracle: The database preserves separate recipe targets and identifies which reference supports each.
- Mutant that must fail: Average all references into one supposedly definitive movie look.

Machine-readable fixture: [P143_SUPPORT_RELEASE_SPECIFIC_AND_SCENE_SPECIFIC_LOOKS.json](P143_SUPPORT_RELEASE_SPECIFIC_AND_SCENE_SPECIFIC_LOOKS.json).

`scripts/gates/p143_support_release_specific_and_scene_specific_looks.py` keys every look by `film_id`, `release_id`, and optional `scene_id`. Two releases of the same film remain distinct entries; their contrast and color parameters are not averaged. `averaged` true, a `release_id` of `"all"`, a collapsed release list, or a definitive single look is rejected. Ambiguous releases, including an unidentified edition, stay listed even when a caller asks to drop them. A scene look must name its release and is recorded only beside the release-level look; it must not replace that release-level entry. A missing `release_id` is rejected. A missing edition stays `unknown`, and a theatrical print inferred from a screenshot is rejected. Each accepted entry names the reference that supports it. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p143*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P143-01 through TC-P143-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
