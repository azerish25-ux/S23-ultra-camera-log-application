# P122 — Create non-destructive recipe versions

Active phase: **P122**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Recipe snapshot store and concurrent-edit tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Recipe snapshot store and concurrent-edit tests

- Goal: Make every creative edit reproducible without rewriting the source or previous result.
- Method: Store immutable source references and versioned graph parameters. Separate autosaved drafts from renderable snapshots. A render consumes one frozen recipe even if the user continues editing; changes create another version.
- Fixture: A user adjusts grain and focus while an earlier export is already running.
- Oracle: The running export remains bound to its original recipe and the new edit receives a distinct identity.
- Mutant that must fail: Read live UI slider values during each frame of an export.

Machine-readable fixture: [P122_CREATE_NON_DESTRUCTIVE_RECIPE_VERSIONS.json](P122_CREATE_NON_DESTRUCTIVE_RECIPE_VERSIONS.json).

`version_sha256` is SHA-256 over the UTF-8 hash preimage, which is canonical JSON of `{params, parent, source}` with sorted keys and no whitespace (`separators=(",", ":")`). It is not a hash of the whole version object. The published parent preimage is:

```text
{"params":{"focus":0.4,"grain":0.15},"parent":null,"source":"9f08a9433990a82fcc30bdeb08ab218ae4f002b36466df429c12d59b72d9275c"}
```

That digests to `cd6a49c49dda03f5a206c43f4fba5d67cb2b7d540971fe06ccc9431401a3e112`. The child edit (`focus` 0.72, `grain` 0.33, parent `rv-1`, same source) digests to `9ccaa17151f11e7bd0d7604cf726dfdfa673f5a3a62872dff2e9afc6e0de4d5f`. The source digest is SHA-256 of `s23-imported-clip-a` and does not change across versions. Forking leaves the parent object's canonical JSON byte-identical. In-place mutation, a changed source hash, a missing parent, a recomputed hash mismatch, and a running export that follows the live edit are rejected.

`scripts/gates/p122_create_non_destructive_recipe_versions.py` rejects `applyMutant` and `mutatedInPlace`. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p122*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P122-01 through TC-P122-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
