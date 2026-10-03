# P057 — LogC3 EI800 reference arithmetic

Active phase: **P057**. Dependencies: **P016**, **P049**, **P056**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a reversible LogC3 EI800 exposure-domain
reference. It does **not** measure a physical Galaxy S23. A green host run is
not that measurement and is not physical S23 qualification.

## Deliverable

Forward and inverse LogC3 functions with source attribution.

Machine-readable fixture:
[P057_IMPLEMENT_LOGC3_EI800_REFERENCE_ARITHMETIC.json](P057_IMPLEMENT_LOGC3_EI800_REFERENCE_ARITHMETIC.json)
(`schemaVersion` 1, `phase` `P057`, `mapId` `s23-logc3-ei800-reference-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

Coefficients are the published SUP 3.x EI800 tables from ARRI, *ALEXA Log C
Curve: Usage in VFX*, 2017-03. The exposure-domain table (scene linear, middle
grey at 0.18) is the reference. The normalised sensor-signal table is a
different input convention and is not applied to exposure-domain samples.
Encoding EI `800` is not the phone ISO (`200` on this fixture). The EI200
exposure intercept `0.092782` is recorded only so it is not selected.

`scripts/gates/p057_implement_logc3_ei800_reference_arithmetic.py` encodes the
phase method, fixture, oracle, and mutant:

- `encode` / `decode` use the exposure-domain cut, the signed linear branch at
  and below the cut, and the log branch above it. Values below zero and above
  scene-linear one are not clipped.
- `assess` checks black (`0` → `0.092809`), middle grey (`0.18` →
  `0.391006832034084`), branch continuity within `0.0000003`, monotonicity,
  and inverse round trips against an independent `math.log10` reference.
  The fixture decision is `reference_agreed`. That label is not `qualified`
  and not `allowed`.
- `apply_sensor_signal_coefficients` is the mutant. It is `rejected`, with
  claims `sensor-signal-on-exposure-domain`, `black`, `middle-grey`,
  `branch`, and `inverse`. Exposure-domain sample tokens stay in
  `preservedResults`. A test fails if `encode` itself used the sensor-signal
  table: black would no longer be `0.092809`.
- `select_by_phone_iso` is `rejected`. The phone ISO does not choose the curve.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p057*.py' -v
```

The phase test loads the fixture, checks the published anchors and the
unclipped signed and highlight samples, and checks that the sensor-signal
mutant is rejected without deleting the inventory. Case modules TC-P057-01
through TC-P057-08 are separate files. This phase module does not call them.
The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Agreement with the published EI800 curve is not sensor-derived Log, not
  fixed cadence, not ten-bit fidelity, and not film-stock fidelity.
- It is not cinema-camera equivalence and not an ARRI camera capture.
- The phone ISO is not the LogC3 encoding EI. Sensor-signal coefficients are
  not valid for exposure-domain input.
- No Kotlin, Gradle, or workflow sources were changed.
