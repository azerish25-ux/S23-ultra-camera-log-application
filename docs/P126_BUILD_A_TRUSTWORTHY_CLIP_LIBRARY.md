# P126 — Build a trustworthy clip library

Active phase: **P126**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Clip library schema and missing-media tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Clip library schema and missing-media tests

- Goal: Keep source, result, metadata, thumbnail, and recovery identities paired.
- Method: Index exact media identities, recipe versions, verification status, duration, geometry, and availability. Thumbnails are derived previews, not proof of output validity. Handle revoked grants and missing files without corrupting the library or silently deleting historical records.
- Fixture: A thumbnail remains cached after the underlying media permission is revoked.
- Oracle: The library shows unavailable media clearly and does not imply that the thumbnail represents accessible verified footage.
- Mutant that must fail: Use thumbnail existence as the media availability check.

Machine-readable fixture: [P126_BUILD_A_TRUSTWORTHY_CLIP_LIBRARY.json](P126_BUILD_A_TRUSTWORTHY_CLIP_LIBRARY.json).

`scripts/gates/p126_build_a_trustworthy_clip_library.py` indexes each clip by `clip_id`, `content_sha256`, `byte_count`, `present`, `playable`, and `verification`. A row may be playable only when `present` is true, `verification` is `verified`, `byte_count` is positive, and any supplied `content` recomputes with SHA-256 to `content_sha256`. `present` false forces `playable` false and `verification` `missing`; playable true while bytes are absent is rejected. Unverified rows stay unverified, and promoting one to verified without a matching content hash is rejected. Duplicate `clip_id` values with different hashes are rejected. Known missing ids in `omitted_ids` must stay in the index and are listed, not dropped. A cached thumbnail does not certify accessible verified footage. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p126*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P126-01 through TC-P126-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
