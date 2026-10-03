# P066 — select and qualify the first GPU backend

Active phase: **P066**. Entry gate: **P065**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for a GPU backend decision record and capability
probe. It does **not** measure a physical Galaxy S23. A green host run is not
that measurement and is not physical S23 qualification.

## Deliverable

Backend decision record and capability probe.

Machine-readable fixture:
[P066_SELECT_AND_QUALIFY_THE_FIRST_GPU_BACKEND.json](P066_SELECT_AND_QUALIFY_THE_FIRST_GPU_BACKEND.json)
(`schemaVersion` 1, `phase` `P066`, `mapId` `s23-gpu-backend-decision-fixture`,
implementation base `d4deac8fc82832fd23396a01065c5f0bf9da6670`).

The fixture says OpenGL ES `3.2` is supported and that `rgba16f` is not
renderable. `GL_EXT_color_buffer_half_float` is required and absent. Image
import is unavailable. The surface is compatible. Precision is not silently
lowered. The CPU reference stays retained. Kernels `box-blur` and
`luma-accumulate` are not executed on the GPU and are not marked matched.
Texture and buffer lifetimes complete before recycle. The maintained GLES
candidate is not selected. Vulkan is recorded as a second backend and is not
selected, because it shows neither a coverage nor a performance benefit.

`scripts/gates/p066_select_and_qualify_the_first_gpu_backend.py` encodes the
phase method, fixture, oracle, and mutant:

- `assess` on `capability-probe` decides `route_unavailable`. `rejectedClaims`
  are `gles-rgba16f`. `preservedResults` still contain `format:rgba16f`,
  `format-renderable:false`, `api-version:3.2`, `api-version-supported:true`,
  `cpu-reference:retained`, both kernels, both lifetimes, and all three
  backends. `route_unavailable` is not `qualified` and not `allowed`.
- The mutant path `version-implies-capability` assumes an API version number
  guarantees every required texture and surface capability. It still decides
  `rejected`, adds `api-version-implies-capability`, and does not rewrite the
  missing format as renderable or drop the CPU reference. A test fails if
  that mutant returns `backend_selected`.
- Silent precision lowering is `rejected` with `silent-precision-drop`. The
  required format stays in the inventory.
- A fully probed route, matched kernels, observed lifetimes, and one
  maintained candidate decide `backend_selected`. That label is a host
  record only. The same document on the mutant path stays `rejected`.
- A second selected backend without a demonstrated benefit is `rejected`.
  Selecting either GPU backend while the probed route is unavailable is
  `rejected`. An empty selection on a complete probe is `withheld`.

## Test command

From the repository root `/workspace/s23`:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p066*.py' -v
```

The phase test loads the fixture, checks that the high-precision route is
unavailable while the CPU reference remains, and checks that API version
support does not imply texture or surface capability. Case modules TC-P066-01
through TC-P066-08 are separate files. This phase module does not call them.
The command above runs their host tests as well.

## Non-claims

- This note and the JSON fixture are an authored host fixture, not a device
  probe and not a physical S23 measurement or qualification.
- `route_unavailable` and `backend_selected` do not certify fixed cadence,
  sensor-derived Log, ten-bit fidelity, film-stock fidelity, cinema-camera
  equivalence, or an on-device GPU backend.
- OpenGL ES 3.2 and `GL_EXT_color_buffer_half_float` in the fixture are
  authored constraints, not a phone capability report.
- An API version number does not guarantee every required texture or surface
  capability. A silent RGBA8 or other precision drop is not accepted.
- No Kotlin, Gradle, or workflow sources were changed.
