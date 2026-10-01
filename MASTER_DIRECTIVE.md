# Master directive — S23 Cinema System

**Status: governing project specification, adopted 1 October 2026.**

The complete user-supplied [S23 Cinema Master Directive](docs/master-directive/S23_Cinema_Master_Directive_200000_Words.md) is the central specification for this entire repository. Its 200,208 words, 160 development phases and 1,280 acceptance-case specifications govern product scope, architecture, implementation order, research, testing and release decisions. This entry point does not replace or abridge that document.

## Authority and interpretation

1. Follow the user's latest explicit requirements. Record material changes to scope or acceptance criteria instead of silently changing the programme.
2. Apply the complete directive's governing charter, scientific and signal-domain contracts, test methodology, dependency gates and active phase requirements together.
3. Use [AGENTS.md](AGENTS.md) for repository-wide execution rules and [integration notes](docs/master-directive/INTEGRATION.md) for the relationship to existing code and documentation. Neither may silently weaken the full specification.
4. Existing READMEs, implementation reports and older phase documents remain historical or implementation evidence. Where their earlier scope conflicts with the new directive, the complete directive governs future work. A specification does not override measured failures or turn planned features into implemented ones.

The original package is preserved byte-for-byte under `docs/master-directive/`. Amendments belong in explicit, reviewed addenda with affected requirement IDs, rationale and renewed tests; do not silently edit the preserved source to fit an implementation.

## Product mandate

Continue the existing `azerish25-ux/S23-ultra-camera-log-application` application; do not replace it with a new repository, rewrite or disconnected demo. S23 Cinema System is a working programme title, not authorization to rename the repository, Android package or public product.

The capture goal remains genuine sensor-derived Log with the greatest usable, measured captured dynamic range and the maximum achievable S23 Ultra resolutions. Pursue RAW-derived LogC3/AWG3 and advanced capture through explicit capability discovery, independent precision checks and physical qualification. A flattened SDR filter, container tag or codec name is not proof of sensor-derived Log, ten-bit fidelity, additional dynamic range or ARRI-camera equivalence.

Extend that foundation with the directive's offline, non-destructive film laboratory: virtual Super 8, Super 16, 35mm, Super 35, five-perforation 65mm and horizontal fifteen-perforation large-format workflows; film-response, grain and optical processing; confidence-aware virtual depth of field; deferred development; source/result comparison; and a locally searchable, provenance-backed movie-recipe catalogue. Preserve clean sources whenever the selected workflow promises non-destructive processing. Keep physical capture controls distinct from adjustable virtual processing controls.

Firmware/HAL research remains a separate, evidence-driven track. This specification is not authorization to flash a phone, unlock a bootloader, disable protections or install unverified system images. No required cloud video generation and no silent replacement of the user's recorded scene are allowed.

## Reading and development order

Read the [governing charter](docs/master-directive/S23_Cinema_Master_Directive_200000_Words.md#agent-charter), scientific model, architecture, TDD method and implementation-agent operating instructions before planning work. Then use the complete document's phase index and [machine-readable dependency map](docs/master-directive/directive_manifest.json) to select a dependency-ready phase and its eight acceptance specifications. Retrieve only the active material rather than repeatedly loading the whole document.

Start by reconciling P001-P004 with the actual repository and baseline evidence. Map existing features and tests to the new requirement IDs; preserve useful implementation instead of restarting completed engineering. Older names such as Phase 3A or Phase 3D are not automatic completion of any P001-P160 phase.

## Mandatory acceptance discipline

For implementation work, retain the failing test or experiment, make the smallest correct change, demonstrate green against an independent oracle and relevant negative controls, then refactor and run adjacent regressions. Record the exact revision, inputs, environment, limits and untested conditions. Do not remove a failing check, lower a precision threshold or relabel an unavailable route to obtain a green badge.

Keep document integrity, host reference tests, Android builds/unit tests, emulator/GPU/codec tests and physical S23 evidence separate. The 1,280 catalogue cases are specifications, not 1,280 executed tests. This adoption does not certify physical S23 Log capture, sustained 4K/8K, dynamic range, thermal endurance, film-stock fidelity or cinema-camera equivalence.

## Verification and handoff

From the repository root:

```sh
python3 scripts/verify_master_directive.py
python3 -m unittest discover -s scripts/tests -p 'test_master_directive.py' -v
python3 -m unittest discover -s docs/master-directive/reference -p 'test_reference.py' -v
```

Run the separate Kotlin/JVM checks as documented in the [companion reference instructions](docs/master-directive/reference/README.md). Follow the existing Android workflow and [device test plan](docs/DEVICE_TEST_PLAN.md) for their distinct acceptance scopes.

Every development handoff must name the active phase/case IDs, changed files, commit, tests actually run, observed failures, unverified hardware assumptions and next dependency-ready step. Current implementation evidence remains in [IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md); new scope and acceptance remain governed here and by the complete directive.
