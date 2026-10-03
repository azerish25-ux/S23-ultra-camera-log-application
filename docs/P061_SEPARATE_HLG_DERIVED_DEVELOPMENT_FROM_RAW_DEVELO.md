# P061 — separate HLG-derived development from RAW development

Active phase: **P061**. Entry gate: **P060**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a source-normalization router. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and
is not physical S23 qualification.

## Deliverable

Source normalization router and lineage assertions.

Machine-readable fixture:
[P061_SEPARATE_HLG_DERIVED_DEVELOPMENT_FROM_RAW_DEVELO.json](P061_SEPARATE_HLG_DERIVED_DEVELOPMENT_FROM_RAW_DEVELO.json)
(`schemaVersion` 1, `phase` `P061`, `mapId`
`s23-source-normalization-router-fixture`, implementation base
`d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The same visible code `0.5` is supplied three ways: declared HLG
(Rec.2020, video range, ISP-processed), declared SDR (Rec.709, video range,
ISP-processed), and an untagged import whose transfer and primaries are
unknown. `ispInvertible` is false on every supply. Upstream ISP processing is
not treated as invertible, and flattened SDR does not grow scene values.

`scripts/gates/p061_separate_hlg_derived_development_from_raw_develo.py`
encodes the phase method, fixture, oracle, and mutant:

- `assess` on `inspect` decides `routed` when the three paths are
  `hlg-derived`, `sdr-derived`, and `unresolved`. Recipes and outputs keep
  the acquisition. `inverse:not-applied` stays in the inventory. `routed` is
  not `qualified` and not `allowed`, and it is not RAW-derived Log.
- The mutant route `one-inverse` applies `display-to-scene-guess` to every
  source and attempts `RAW-derived-Log`. It decides `rejected` with
  `one-inverse-curve` and `silent-raw-log-promotion`. Decoded tags remain in
  `preservedResults`. A test fails if that mutant is what `inspect` returns.
- Contradictory tags and a claim that ISP processing is invertible are
  `rejected`. The other supplies stay in the inventory.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p061*.py' -v
```

The phase test loads the fixture, checks that HLG, SDR, and untagged stay
distinct, and checks that one inverse curve is rejected. Case modules
TC-P061-01 through TC-P061-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Routing a declared HLG tag does not prove sensor-derived Log, fixed cadence,
  ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `ispInvertible: false` records a limit of this fixture. It is not a
  measurement that a physical ISP can or cannot be inverted.
- An equal visible code is not shared scene-linear data. SDR is not promoted
  by inventing highlights, and an untagged file is not a native-camera
  capture.
- Case decisions such as `layout_checked`, `within_tolerance`, and
  `lineage_kept` are host labels. They are not accepted exports, ten-bit
  qualification, or interoperability certificates.
- No Kotlin, Gradle, or workflow sources were changed.
