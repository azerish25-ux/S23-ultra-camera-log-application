# P110 — Render depth-ordered foreground and background blur

Active phase: **P110**.

The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative. This note
publishes a host fixture for "Occlusion-aware bokeh reference and layer-compositing tests". It does **not** measure a
physical Galaxy S23. A green host run is not that measurement.

## Deliverable

Occlusion-aware bokeh reference and layer-compositing tests

- Goal: Implement an occlusion-aware lens renderer rather than a single per-pixel Gaussian blur.
- Method: Start with layered or scatter-gather reference rendering using signed defocus, coverage, and normalized kernels. Test foreground spread, background leakage, point-light energy, and image borders. Document the treatment of missing background samples.
- Fixture: A strongly defocused foreground branch crossing an in-focus face and a bright background light.
- Oracle: The branch spreads appropriately without leaking background color through the opaque focused face.
- Mutant that must fail: Apply one gather blur radius per pixel without any depth-order reasoning.

Machine-readable fixture: [P110_RENDER_DEPTH_ORDERED_FOREGROUND_AND_BACKGROUND_BLUR.json](P110_RENDER_DEPTH_ORDERED_FOREGROUND_AND_BACKGROUND_BLUR.json).

`scripts/gates/p110_render_depth_ordered_foreground_and_background_blur.py` renders a depth-ordered gather on a 1D strip of `{depth, value, layer}`. Radius is `DEFOCUS_RADIUS_SCALE * abs(depth - focus)`. Samples within `FOCUS_EPSILON` of the focus plane stay sharp: neighbour mix weight is 0. Background samples mix only with background samples. Foreground samples mix only with foreground samples and must not enter a background output bin. Unknown depth stays unknown and is not treated as far. A uniform gaussian labelled `optical_bokeh` is rejected. Border kernels are renormalized over in-strip admitted samples. Missing background behind the opaque focus face is not invented. The evidence id stays in `preservedResults`. The decision is never `qualified` or `allowed`.

## Test command

```sh
python3 -m unittest discover -s scripts/tests -p 'test_p110*.py' -v
```

## Non-claims

- This is an authored host fixture, not a device probe and not a physical S23 measurement.
- It does not certify fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, or cinema-camera equivalence.
- TC-P110-01 through TC-P110-08 are host checks of the stated negatives. They were not run on hardware.
- No Kotlin sources were changed.
- Missing background behind the opaque focus face is not invented. Off-strip samples are not fabricated.
