# P026 — qualify video encoder startup

Active phase: **P026**. Entry gate: **P025**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes the encoder-startup fixture and the host gate that checks the emitted
signal. It does **not** measure a physical Galaxy S23. A green host run is not
that measurement and is not physical S23 qualification.

## Deliverable

Encoder startup owner and output-signal checks.

Machine-readable fixture: [P026_QUALIFY_VIDEO_ENCODER_STARTUP.json](P026_QUALIFY_VIDEO_ENCODER_STARTUP.json)
(`schemaVersion` 1, `phase` `P026`, `contractId` `s23-encoder-startup-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture is a Main10 request. Configure succeeds and the requested
MediaFormat says ten-bit Main10. The emitted SPS is eight-bit. Profile name,
3840×2160 size, unspecified transfer, and limited range otherwise match.
Format change, codec-config, keyframe request, startup timeout, and the output
sample are separate events. The codec name `c2.android.hevc.encoder` is an
authored label, not a device probe. Nothing is relabelled as acceptable Log.

`scripts/gates/p026_qualify_video_encoder_startup.py` encodes the method,
fixture, oracle, and mutant:

- `bit_depth(..., "emitted-stream")` reads the SPS. `requested-mediaformat` is
  the mutant and is not the startup gate.
- `ten_bit_route_ok` is true for the mutant source on this fixture and false
  for the emitted stream.
- `assess_startup` decides `rejected` with `ten-bit-route-failed`. The oracle
  text is retained. `startup_ready` is not used.
- `preservedResults` keeps the inventory, the advertised codec name, and the
  SPS depth token.
- A real emitted ten-bit match can decide `startup_ready`. That label is not
  `qualified` and not `allowed`.
- Configure failure text and wrong-signal text stay in `reasons`.

`assess_startup` does not call TC-P026-01 through TC-P026-08. Those case
modules are separate host checks.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p026*.py' -v
```

The phase test loads the fixture, checks that the eight-bit SPS fails the
ten-bit route, and checks that trusting the requested MediaFormat would have
passed. That assertion fails if the mutant is implemented.

## Non-claims

- This fixture and note are not a device probe and not a physical S23
  measurement or qualification.
- The host result does not certify fixed cadence without measured evidence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera
  equivalence.
- `startup_ready` is a software label for a matching host fixture. It is not
  `qualified` and not `allowed`.
- Main10 in the requested MediaFormat is not ten-bit fidelity and is not Log.
- No Android or Kotlin sources were changed.
- `docs/evidence/P026-handoff.json` leaves `commit` null. This phase does not
  invent a git revision.
