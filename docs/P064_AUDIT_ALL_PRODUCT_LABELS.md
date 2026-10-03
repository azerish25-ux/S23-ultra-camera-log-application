# P064 — audit all product labels

Active phase: **P064**. Entry gate: **P063**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for source-aware product wording. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and is
not physical S23 qualification.

## Deliverable

Claim linter and source-aware product wording.

Machine-readable fixture:
[P064_AUDIT_ALL_PRODUCT_LABELS.json](P064_AUDIT_ALL_PRODUCT_LABELS.json)
(`schemaVersion` 1, `phase` `P064`, `mapId` `s23-product-label-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture source is a rendered SDR import (`SDR-derived`, Rec.709). The
export uses recipe `large-format`, preset name `Large Format Log`, and codec
`Main10` at container depth 10. The picture may be visually flat. Those facts
do not make the source native large-format or sensor-derived Log.

Centralized wording covers RAW-derived, HLG-derived, SDR-derived, provisional
calibration, virtual format, and processed look. The SDR phrase is
`SDR-derived simulated look; not native large-format or sensor-derived Log`.
The same wording is what select, export, and share must show. Marketing flags
for sensor enlargement, guaranteed ARRI equivalence, and recovered clipped
detail are false.

`scripts/gates/p064_audit_all_product_labels.py` encodes the phase method,
fixture, oracle, and mutant:

- `assess` on the source-aware path decides `simulated_look`.
  `preservedResults` keep the SDR acquisition, the recipe, the preset name,
  the Main10 codec, the container depth, and the centralized wording.
  `simulated_look` is not `qualified` and not `allowed`.
- The mutant interpretation `preset-only` builds the export label from
  `Large Format Log` alone. It decides `rejected` with `preset-only-label`,
  `native-large-format`, and `sensor-derived-log`. The SDR acquisition stays
  in the inventory. A test fails if that mutant is accepted as
  `simulated_look`, `qualified`, or `allowed`.
- Sensor enlargement, guaranteed ARRI equivalence, recovered clipped detail,
  a native-sensor format claim, or a UI label that misses machine-readable
  evidence are `rejected`. Missing select, export, or share surfaces are
  `rejected` without dropping the surfaces that were present.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p064*.py' -v
```

The phase test loads the fixture, checks that the interface calls the export a
simulated look from an SDR source, and checks that the preset-only mutant is
rejected. Case modules TC-P064-01 through TC-P064-08 are separate files. This
phase module does not call them. The command above runs their host tests as
well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `simulated_look` does not establish sensor-derived Log, native large-format
  capture, sensor enlargement, or cinema-camera equivalence.
- A ten-bit Main10 container does not establish ten-bit image fidelity,
  film-stock fidelity, or recovered clipped detail.
- Provisional calibration is not a measured camera profile and is not
  guaranteed ARRI equivalence.
- A flat picture and a large-format recipe do not upgrade an SDR import.
- No fixed cadence is claimed. No Kotlin, Gradle, or workflow sources were
  changed.
