# P073 — define stock profiles and evidence levels

Active phase: **P073**. Entry gate: **P007, P049, P056**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for stock profiles and evidence levels. It does
**not** measure a physical Galaxy S23. A green host run is not that
measurement and is not physical S23 qualification.

## Deliverable

Stock schema and evidence-level validator.

Machine-readable fixture:
[P073_DEFINE_STOCK_PROFILES_AND_EVIDENCE_LEVELS.json](P073_DEFINE_STOCK_PROFILES_AND_EVIDENCE_LEVELS.json)
(`schemaVersion` 1, `phase` `P073`, `mapId` `s23-stock-profiles-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

Each profile stores family, balance, response model, parameter units, source
references, licence state, and confidence. Display name `Vision 400` is shared.
Stable identifiers `vision-400-a` and `vision-400-b` are not. Density curves
differ. Evidence is `reconstructed` and `synthetic` because the sources are
uncertain. Artistic controls are not measured parameters. `virtualFormat` and
`appearanceId` are `none`, so the stock record is not a virtual format or a
final appearance.

`scripts/gates/p073_define_stock_profiles_and_evidence_levels.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` on the catalogued path decides `versioned_interpretations`.
  `rejectedClaims` is empty. `preservedResults` still contain both profiles,
  both curves, and both evidence labels. That decision is not `qualified` and
  not `allowed`.
- The mutant path `marketing-as-measured` uses the marketing name as proof
  that every numerical parameter was physically measured. It decides
  `rejected`, adds `marketing-name-as-measurement`, and does not rewrite the
  stored evidence to `measured`. A test fails if that mutant returns
  `versioned_interpretations`.
- The same profile identifier and version with a different density curve is
  `rejected` as `unversioned-numerical-change`. A new version of that
  identifier stays `versioned_interpretations`.
- Identical measured curves under one display name are
  `falsely-identical-calibrated`. A non-monotonic curve, a virtual-format
  binding, or measured parameters on an unmeasured interpretation are
  `rejected`. The profile inventory is kept.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p073*.py' -v
```

The phase test loads the fixture, checks that the two interpretations stay
distinct, and checks that a marketing name does not prove physical
measurement. Case modules TC-P073-01 through TC-P073-08 are separate files.
This phase module does not call them. The command above runs their host tests
as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- A host pass does not establish film-stock fidelity, cinema-camera
  equivalence, sensor-derived Log, ten-bit fidelity, or fixed cadence without
  measured evidence.
- `versioned_interpretations` means the catalogue kept two different curves
  under separate identifiers. It is not a calibrated stock measurement and
  not a Kodak or other manufacturer profile.
- A marketing display name is not proof that numerical parameters were
  physically measured. Uncertain sources stay reconstructed or synthetic.
- No Kotlin, Gradle, or workflow sources were changed.
