# P102 — Construct a difficult-scene depth corpus

Active phase: **P102**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host reference for "Difficult-scene corpus and per-category evaluation protocol". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Difficult-scene corpus and per-category evaluation protocol

- Goal: Evaluate the scenes that determine whether synthetic cinema blur is usable.
- Method: Include hair, fur, glasses, mirrors, water, smoke, fences, thin wires, low texture, motion blur, low light, and crossing subjects. Obtain consent and rights for all footage. Use synthetic geometry where ground truth is available and honest qualitative labels elsewhere.
- Fixture: A scene with a person behind a fence and a reflection that appears at a different apparent depth.
- Oracle: The evaluation records specific boundary and ordering failures rather than averaging them away in one global score.
- Mutant that must fail: Benchmark only isolated portraits against simple backgrounds.

Machine-readable fixture: [P102_CONSTRUCT_A_DIFFICULT_SCENE_DEPTH_CORPUS.json](P102_CONSTRUCT_A_DIFFICULT_SCENE_DEPTH_CORPUS.json).

`scripts/gates/p102_construct_a_difficult_scene_depth_corpus.py` checks the manifest, not a boolean stand-in.

- Each scene carries content, its SHA-256, tags, split (`train` or `held_out`), and frame count. The digest is `hashlib.sha256` of the UTF-8 content. A declared digest that does not match is invalid.
- Exact hash equality is the near-duplicate test. A repeated digest is not a new scene: `unique-scenes` stays on the distinct digests and `duplicate-content-hash` is rejected.
- Held-out must be non-empty and disjoint from train hashes.
- Coverage is the fraction of required held-out tags: hair, glass, low light, thin objects, mirrors, saturated. A missing difficult tag rejects the corpus. A tag that appears only in train does not count.
- A corpus whose scenes are only easy textured portraits on simple backgrounds is rejected. That is the mutant.
- Depth labels are `metric` or `relative`. Metric depth must be synthetic ground truth in metres. Relative depth labelled metres is rejected.
- Boundary and ordering failures stay on the scene. A single global score, or a protocol that does not record per category, is rejected. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p102*.py' -v
```

## Non-claims

- This is an authored host reference, not a device probe and not a physical S23 measurement.
- It does not certify sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P102-01 through TC-P102-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
