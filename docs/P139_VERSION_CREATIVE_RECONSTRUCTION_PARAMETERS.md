# P139 — Version creative reconstruction parameters

Active phase: **P139**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Reconstruction versioning and immutable fact tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Reconstruction versioning and immutable fact tests

- Goal: Make our interpretation editable without modifying the underlying production facts.
- Method: Keep a recipe graph linked to, but distinct from, evidence records. Version exposure, stock model, virtual lens, grain, halation, print response, and grade independently. A user adaptation becomes a derivative recipe with its own name and provenance.
- Fixture: A user changes the virtual aperture and print contrast of a movie-inspired recipe.
- Oracle: The original documented facts remain unchanged and the edited appearance is stored as a user reconstruction.
- Mutant that must fail: Overwrite the cinematographer’s documented settings with the user’s creative changes.

Machine-readable fixture: [P139_VERSION_CREATIVE_RECONSTRUCTION_PARAMETERS.json](P139_VERSION_CREATIVE_RECONSTRUCTION_PARAMETERS.json).

Production facts are an immutable dict. `fact_hash` is SHA-256 over the UTF-8 canonical JSON of that dict (`sort_keys=True`, `separators=(",", ":")`). A creative edit appends a reconstruction version with `parent_id` and its own `parameter_hash`, the SHA-256 of canonical `{"facts", "params", "parent"}`. That version keeps the original fact hash. The first reconstruction may use `parent_id` null. A later version whose parent is missing is rejected. Overwriting a documented fact key is rejected when the same facts object was mutated, when `fact_hash` changes, or when `mutated_facts` is true.

`scripts/gates/p139_version_creative_reconstruction_parameters.py` rejects `applyMutant` and a changed fact hash. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p139*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P139-01 through TC-P139-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
