# P054 — implement denoising as an optional processing stage

Active phase: **P054**. Entry gate: **P053**.

This note publishes a host fixture for an optional denoise stage. It does **not**
measure a physical Galaxy S23. A green host run is not that measurement and is
not physical S23 qualification.

## Deliverable

Denoise module and detail-versus-noise evaluation protocol.

Machine-readable fixture:
[P054_IMPLEMENT_DENOISING_AS_AN_OPTIONAL_PROCESSING_ST.json](P054_IMPLEMENT_DENOISING_AS_AN_OPTIONAL_PROCESSING_ST.json)
(`schemaVersion` 1, `phase` `P054`, `mapId` `s23-optional-denoise-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture scores four scenes: low-light hair, moving fabric, a static wall,
and a slowly moving colored point light. The honest path is a conservative
spatial reference (`conservative-box-3`) at strength `0.25`, algorithm
`spatial-ref-1`. Texture retention stays at or above `0.85` and motion trail
stays at or below `0.02`. Noise characterization is `sensor-read-noise`, not
artistic grain. Residuals are inspectable and clean source storage is
untouched. The stage can be turned off.

Frame averaging without motion or occlusion handling is quieter on every scene
and still fails the gate on hair, fabric, and the point light. That mutant is
rejected even if its metrics are edited to sit inside the gate.

`scripts/gates/p054_implement_denoising_as_an_optional_processing_st.py` encodes
the phase method, fixture, oracle, and mutant:

- `assess` keeps scene metrics, frame-average counterexamples, strength, and
  the algorithm version in `preservedResults`. The fixture decision is
  `optional-stage`. That label is not `qualified` and not `allowed`.
- The mutant processing mode `frame-average-without-motion` is `rejected`
  with `frame-average-without-motion`. A test fails if that mutant is
  implemented as `frame_averaged`, `optional-stage`, `qualified`, or `allowed`.
- Texture smear, motion trails past the declared gate, grain conflated with
  noise, a contaminated clean source, hidden residuals, and strength above
  `0.35` are `rejected`. Disabling the stage is `disabled`, not a pass.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p054*.py' -v
```

The phase test loads the fixture, checks that quieter frame averages do not
pass, and checks that motion-unaware averaging is rejected. Case modules
TC-P054-01 through TC-P054-08 are separate files. This phase module does not
call them. The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- A lower noise figure does not prove fixed cadence, sensor-derived Log,
  ten-bit fidelity, or film-stock fidelity.
- The spatial reference and the scene numbers are not cinema-camera
  equivalence and are not a measured denoise from a physical capture.
- Artistic grain is not sensor-noise characterization.
- Frame averaging without motion or occlusion handling is not an accepted
  temporal candidate.
- No Kotlin, Gradle, or workflow sources were changed.
