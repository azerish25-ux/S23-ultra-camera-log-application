# P065 — define a typed render graph

Active phase: **P065**. Entry gate: **P049, P056, P060**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a typed render graph. It does **not** measure a
physical Galaxy S23. A green host run is not that measurement and is not
physical S23 qualification.

## Deliverable

Render graph schema and static compatibility validator.

Machine-readable fixture:
[P065_DEFINE_A_TYPED_RENDER_GRAPH.json](P065_DEFINE_A_TYPED_RENDER_GRAPH.json)
(`schemaVersion` 1, `phase` `P065`, `mapId` `s23-typed-render-graph-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

Each node declares inputs, outputs, a precision requirement, a spatial halo,
temporal context, deterministic parameters, and whether it alters geometry,
exposure, color, texture, or time. Edges are checked before allocation.
`framesProcessed` and `allocated` are false on the fixture.

The fixture keeps one compatible edge and two illegal edges:

- `working-to-density` connects `scene-linear` `rgba16f` to `film-density`.
  That edge is typed and compatible. It stays in the inventory.
- `density-to-yuv` connects the film-density output directly to an encoded
  YUV surface. Domain `film-density` is not `encoded-yuv`, and `rgba16f` is
  not `yuv420`.
- `overlay-to-master` connects a display overlay to clean-master export.
  Domain, precision, and geometry all disagree (`overlay-plane` versus
  `export-plane`).

`scripts/gates/p065_define_a_typed_render_graph.py` encodes the phase method,
fixture, oracle, and mutant:

- `assess` on the typed path decides `rejected`. `rejectedClaims` are
  `density-to-yuv` and `overlay-to-master`. `preservedResults` still contain
  every node, every port, the compatible edge, and `frames-processed:false`.
  `rejected` is not `qualified` and not `allowed`.
- The mutant path `untyped-handles` represents intermediates as untyped
  texture handles. It still decides `rejected`, adds
  `untyped-texture-handles`, and does not erase the two domain failures. A
  test fails if that mutant returns `edges_validated`.
- A graph that contains only `working-to-density` decides `edges_validated`
  on the typed path. The same graph on the mutant path stays `rejected`.
- Untyped ports, a short halo, a temporal mismatch, a nondeterministic node,
  or frames marked processed before validation are `rejected`. An empty edge
  list is `withheld`. Nodes are not deleted.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p065*.py' -v
```

The phase test loads the fixture, checks that both invalid connections are
rejected before frames, and checks that untyped texture handles do not make
those connections legal. Case modules TC-P065-01 through TC-P065-08 are
separate files. This phase module does not call them. The command above runs
their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- Rejecting a host graph does not prove fixed cadence, sensor-derived Log,
  ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- `edges_validated` is a static descriptor check. It is not a GPU backend
  qualification, a measured frame rate, or an on-device render.
- Untyped texture handles are not a compatible intermediate. A silent RGBA8
  replacement of a high-precision format is not accepted by TC-P065-01.
- No Kotlin, Gradle, or workflow sources were changed.
