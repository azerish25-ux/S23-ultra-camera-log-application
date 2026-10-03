# P067 — validate half and full precision boundaries

Active phase: **P067**. Entry gate: **P066**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for half- and full-precision error budgets. It does
**not** measure a physical Galaxy S23. A green host run is not that measurement
and is not physical S23 qualification.

## Deliverable

Precision budget and CPU-GPU differential suite.

Machine-readable fixture:
[P067_VALIDATE_HALF_AND_FULL_PRECISION_BOUNDARIES.json](P067_VALIDATE_HALF_AND_FULL_PRECISION_BOUNDARIES.json)
(`schemaVersion` 1, `phase` `P067`, `mapId` `s23-precision-boundary-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

Each operation records a CPU double reference, a GPU output, the chosen and
required precision, a positive error budget, and whether any reduction was an
explicit graph decision. Absolute error is `|cpu − gpu|`. `framesProcessed` is
false. The suite reference is `cpu-double` and the compared output is
`gpu-output`.

The fixture keeps the named cases and the other differential probes:

- `highlight-kernel` is a bright narrow highlight convolved with a large
  kernel. The FP32 result is inside budget `0.001` after promotion
  (`18.75` versus `18.7502`, error `0.0002`).
- `matrix-cancellation` is a near-neutral residual. It is promoted to FP32
  and stays inside budget `0.00005` (`0.0004` versus `0.00041`).
- `signed-dark`, `bright-highlight`, and `long-accumulation` stay in the
  inventory. Signed dark values use FP32 without a reduction. Bright
  highlights and long accumulations are promoted.
- `overflow-guard` records an FP16 overflow and promotes to FP32.
  `denormal-guard` records an FP16 denormal and promotes to FP32.
- `texture-conversion` is an explicit FP16 reduction (`required` FP32) whose
  accumulated error was tested and stays inside budget `0.001`.

`scripts/gates/p067_validate_half_and_full_precision_boundaries.py` encodes
the phase method, fixture, oracle, and mutant:

- `assess` on the declared path decides `precision_bounded`. `rejectedClaims`
  is empty. `preservedResults` still contain every operation, the CPU and GPU
  values, and `frames-processed:false`. `precision_bounded` is not
  `qualified` and not `allowed`.
- The mutant path `fp16-everywhere` replaces every intermediate with FP16
  without testing accumulated error. It decides `rejected`, adds
  `fp16-without-accumulated-error`, and does not rewrite the recorded
  precisions or drop the highlight and cancellation rows. A test fails if
  that mutant returns `precision_bounded`.
- An over-budget sample, a silent reduction, untested FP16, unresolved
  overflow or denormal, or a silent texture conversion is `rejected`. The
  other operations stay in the inventory.
- An empty operation list is `withheld`. Claiming processed device frames
  is `rejected`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p067*.py' -v
```

The phase test loads the fixture, checks that the highlight kernel and the
matrix cancellation stay inside the declared budget or are promoted, and
checks that replacing every intermediate with FP16 without an accumulated-error
test does not accept the suite. Case modules TC-P067-01 through TC-P067-08
are separate files. This phase module does not call them. The command above
runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `precision_bounded` is a decimal comparison of authored CPU and GPU strings.
  It does not prove fixed cadence, sensor-derived Log, ten-bit fidelity,
  film-stock fidelity, or cinema-camera equivalence.
- Promotion is a graph decision inside the fixture. It is not a measured GPU
  result and not a recording frame rate.
- Replacing every intermediate with FP16 without testing accumulated error is
  rejected. A silent RGBA8 replacement of a high-precision format is not
  accepted by TC-P067-01.
- No Kotlin, Gradle, or workflow sources were changed.
