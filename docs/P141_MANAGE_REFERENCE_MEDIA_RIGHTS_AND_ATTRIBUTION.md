# P141 — Manage reference media rights and attribution

Active phase: **P141**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Content rights manifest and package licence gate". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Content rights manifest and package licence gate

- Goal: Avoid bundling copyrighted frames or proprietary look data without the required permission.
- Method: Store links and factual citations separately from distributable assets. Use owned comparison footage and approved thumbnails. Track model, profile, LUT, image, and text rights independently. Unknown redistribution status blocks packaging that asset until reviewed.
- Fixture: A useful production still with an accessible public URL but no permission to bundle it in the app.
- Oracle: The catalogue can retain a citation while excluding the image bytes from the distributable package.
- Mutant that must fail: Treat public web accessibility as a redistribution licence.

Machine-readable fixture: [P141_MANAGE_REFERENCE_MEDIA_RIGHTS_AND_ATTRIBUTION.json](P141_MANAGE_REFERENCE_MEDIA_RIGHTS_AND_ATTRIBUTION.json).

`scripts/gates/p141_manage_reference_media_rights_and_attribution.py` judges each packaged asset on its own `asset_id`, `licence` (a non-empty string or null), `attribution`, and `redistribute` bool. A public URL with licence null must not be redistributed. redistribute true without a licence is rejected. Treating "public web page" as a licence is rejected. Required attribution missing while redistribute is true is rejected. Assets with a licence and attribution can be recorded. Frames that lack a licence are not bundled. The catalogue keeps the citation and leaves those image bytes out of the distributable package. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

Licence rule: A public URL with licence null must not be redistributed. redistribute true without a licence is rejected. Treating "public web page" as a licence is rejected. Required attribution missing while redistribute is true is rejected. Assets with a licence and attribution can be recorded. Frames that lack a licence are not bundled.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p141*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P141-01 through TC-P141-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
