# Repository-wide implementation instructions

These instructions apply to the entire repository.

## Required specification

Read [MASTER_DIRECTIVE.md](MASTER_DIRECTIVE.md) first. The complete [S23 Cinema Master Directive](docs/master-directive/S23_Cinema_Master_Directive_200000_Words.md) is the governing product and engineering specification. Read its charter, signal-domain contracts, TDD method and the active phase with its acceptance cases before changing code. Use `docs/master-directive/directive_manifest.json` for dependencies.

The preserved package is a source record, not a generated approximation. Run `python3 scripts/verify_master_directive.py` before and after relevant documentation changes. Do not rewrite its text, examples, manifest or historical red/green logs to fit the current implementation. Propose an explicit addendum for a genuine requirement change.

## Work in the existing application

Inspect the live branch, relevant production interfaces, tests and implementation evidence. Continue on `main` unless the user explicitly requests another branch; do not introduce a new repository, worktree, staging branch or force push. Preserve concurrent work and use fast-forward publication only. Reconcile any changed remote head before publishing.

Keep the existing Kotlin/XML application, Android package identity and pinned build. Minimize new modules, dependencies, caches and architecture. A directive workstream is not an instruction to create a Gradle module. Adapt the companion examples to tested production seams; they are not a replacement Android app.

## Tests and evidence

Name the active P001-P160 phase and TC-Pxxx-xx cases. Use red-green-refactor for implementation, independent oracles, adversarial tests and relevant regressions. Retain failures; never bypass checks, weaken numerical gates or misreport unavailable/untested hardware as passed.

Separate host, JVM, Android build, emulator, GPU/codec and physical-device results. The 1,280 catalogue cases are specifications only until implemented and executed. Check actual decoded precision, provenance and capture evidence; do not substitute successful compilation, a Log label or an eight-bit/SDR route for the user's sensor-derived Log goal.

Keep capture and development non-destructive where promised. Preserve existing SDR/HLG, saved-RAW and experimental live RAW-derived paths while extending the programme. Keep monitoring independent of the recorded master and distinguish physical controls from virtual processing controls.

No required cloud video generation. No firmware flashing, bootloader changes or protection changes without fresh, device-specific user authorization.

## Publication

Run the focused tests, the directive integrity checks and applicable existing suites. Publish a coherent commit, verify its remote SHA and inspect the workflow result for that exact commit. Report pending, failed and unavailable checks accurately. Do not invent a commit, tree, workflow run or successful push.

Handoffs must include the phase/case IDs, changed behavior, exact commit, test commands/results, remaining acceptance gaps and the next dependency-ready step. Do not claim a phase complete merely because it is now documented.
