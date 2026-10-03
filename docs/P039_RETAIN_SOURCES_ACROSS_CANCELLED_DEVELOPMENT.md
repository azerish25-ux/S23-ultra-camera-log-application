# P039 — retain sources across cancelled development

Active phase: **P039**. Entry gate: **P038**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a non-destructive development contract. It does
**not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Non-destructive development contract and cancellation tests.

Machine-readable fixture:
[P039_RETAIN_SOURCES_ACROSS_CANCELLED_DEVELOPMENT.json](P039_RETAIN_SOURCES_ACROSS_CANCELLED_DEVELOPMENT.json)
(`schemaVersion` 1, `phase` `P039`, `mapId`
`s23-retain-sources-cancelled-development-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture cancels development halfway through four original frames, closes
the read-only lease, labels the partial movie `incomplete`, restarts, and
retries with another film recipe. The retry frame list is the original frame
list. The source content hash is the same before and after. The destination
and the temporary path are different names from `take.rawseq`.

`scripts/gates/p039_retain_sources_across_cancelled_development.py` encodes
the phase method, fixture, oracle, and mutant:

- `assess` keeps the source token, profile token, and every original frame in
  `preservedResults`. The fixture decision is `sources_retained`, never
  `qualified` or `allowed`.
- The partial result stays labelled incomplete. The retry reads the original
  frames. A hash change, an open lease, a writable handle, or a retry that
  misses the original frames is `rejected` without wiping that inventory.
- The mutant reuses the source filename as the destination of a developed
  movie. That document is `rejected`. A test fails if that mutant is
  implemented as `sources_retained`.
- Cancellation that is not halfway, a missing restart, or a retry that does
  not change the film recipe is `withheld`. The source inventory remains.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p039*.py' -v
```

The phase test loads the fixture, checks that the source hash is unchanged,
and checks that a developed movie cannot reuse the source filename. Case
modules TC-P039-01 through TC-P039-08 are separate files. This phase module
does not call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- A host pass does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `sources_retained` is a software label for this fixture. It is not a
  finished export and it is not physical qualification.
- Reusing the source filename as a movie destination is rejected here. That
  rejection is not evidence from a device filesystem.
- No Kotlin, Gradle, or workflow sources were changed.
