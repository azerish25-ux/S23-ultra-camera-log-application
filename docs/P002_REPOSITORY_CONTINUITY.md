# P002 — repository continuity and minimal-change integration

Active work package: **P002**, including **TC-P002-01 through TC-P002-08**.
The [Master Directive](../MASTER_DIRECTIVE.md) remains authoritative; the original
package is unchanged. This is an executable, bounded source map, not a camera
rewrite or a declaration that the 160-phase programme is implemented.

## Inspected revision and coverage

The source baseline is `835f67aca7576397e11faafe71ecfb5c93be8a57`, Git tree
`86726832a2bc722ab7c0ae58e5b044cb21fdab89`. All 258 source-file blobs recovered from
its original CI source archive were checked against the recorded Git tree.
**Byte identity is not semantic review.** The continuity map records 1,297 reviewed
lines across 31 files, 13 ownership seams and 23 test references (22 unique tests).
Every other baseline file is enumerated as uninspected by this map, even where
another phase or earlier work inspected it. Unselected lines remain outside the
claimed review. Whole-file hashes deliberately require re-review when any part
of a selected file changes; they do not claim every line was audited.

[REPOSITORY_CONTINUITY.json](REPOSITORY_CONTINUITY.json) binds each source/test
reference to a Git blob, SHA-256 and reviewed line ranges. It maps all twenty
charter obligations to existing partial implementations, planned work,
conditional research or preserved prohibited/excluded scope. The reasons and
owning phases for each remaining gap are explicit. These are implementation-map
states, not evidence of completed features.

The existing [requirement/evidence index](REQUIREMENT_EVIDENCE.json) gains an
append-only P002 inspection, one historical source fixture and a bounded static
inspection receipt. P001 records remain unchanged. No product finding has been
promoted to `supported`; P003/P004 still own their separate acceptance work.

## Concrete path and ownership boundaries

| Boundary | Reusable implementation | Observed limit / integration decision |
| --- | --- | --- |
| Ordinary capture | `MainActivity` → `CameraController.startRecording` → existing recorder/finalizer | Preserve planned modes, applied manual-control checks and independent preview. No second camera engine. |
| Retained RAW acquisition | `CameraController` → `RawSequenceCapture`; `RawFrameMatcher` and `RawSequenceFormat` | Exact timestamp pairing and CRC-framed storage already exist. Requested cadence is not measured sustained throughput; acquisition-only benchmark mode does not retain RAW video. |
| Source reading | `RawDevelopmentStore.inspect` → `RawSourceReader.scan` / `RawSourceIndex.rows` | Reuse bounded row reads and strict checksums. Android rejects incomplete tails and cadence gaps instead of silently repairing/retiming them. |
| Profile and colour | `RawColourProfile.parse`, `RawFrameDeveloper`, `RawRowSource`, `LogRowSink` | Reuse source/profile applicability and CPU reference arithmetic. A scalar Log curve, imported measured label or manufacturer-metadata starting profile is not physical camera calibration. |
| Saved-RAW encoding | `RawDevelopmentStore.develop` → `LogP010Codec.qualify/encode/verify` | Keep codec qualification and every-frame pixel comparison. Output is currently video-only; orientation is sidecar metadata. An unavailable P010 route is not replaced with SDR. |
| Finalization/recovery | `SurfaceRecorder` → `VideoFinalizer`; `PendingMedia.recover` at application startup | Ordinary-capture publication, retention and report errors have separate outcomes. Do not apply its journal blindly to the separate RAW/developed directories. |
| Screen and worker lifetime | `RawDevelopActivity` → application-owned `RawDevelopmentStore` | Rotation reattaches to the worker. Other screen exits cancel it. This is not a durable, resumable background renderer. |
| Reports and live experiments | `ProbeReport`, recording validation reports and the separate `LiveLogSession` | Reuse existing report semantics; P003 should adapt them, not collapse advertised, received, decoded and physical stages into one flag. |

The retained-source development path branches into ordinary-camera, saved-RAW and
live-experiment ownership; these are related but are not one interchangeable
success state. The map deliberately keeps each seam and its tests separate.

## Minimal-change architecture decision

Continue within the existing application and packages. Keep `CameraController`,
`SurfaceRecorder`, RAW source format/readers, profile binding, finalization and
recovery as integration boundaries. No new module, renderer dependency, SDK
upgrade, package rename or signing change is justified by P002.

For **P003**, adapt current diagnostics and recording/development reports into
explicit evidence stages. The typed image/graph work in **P065** must branch a
clean master before creative film/optics operations. Future stock contracts
(**P073**) attach to declared working images, not to a UI label or arbitrary
encoded buffer. Depth-provider work (**P097**) remains separate from the capture
callback. Durable jobs/checkpoints (**P123–P124**) must preserve source identity
and account for the current screen-exit cancellation. A local movie evidence
schema (**P137**) cannot silently change acquisition settings. These are future
integration targets, not assertions that their dependencies are satisfied.

## Executable continuity gate

`python3 scripts/verify_repository_continuity.py --expected-head "$(git rev-parse HEAD)"`

The read-only checker reuses `verify_research_contract.py` for receipt provenance,
raw outcomes, measurement units, immutable history and unsupported-claim checks.
It additionally verifies the baseline tree and blobs, source/test anchors within
reviewed ranges, ownership and caller references, exact requirement coverage,
minimal-change decisions and historical JUnit test identities. Missing files,
changed inspected code, newly committed/untracked uninspected application files,
misbound test results and a moving HEAD block acceptance. Unrelated changes are
reported, not reset or overwritten. No command stored in evidence is executed.

An unrelated documentation commit does not invalidate untouched inspected blobs,
but is reported as an unreviewed change and never relabelled a full new audit.
To review changed source, append a new P001 inspection and update the map to that
revision; preserve prior records and receipts. Do not rewrite old hashes to turn
old evidence into evidence for new code.

The checks establish record consistency and inspected byte identity. They are
not a Kotlin parser, complete call-graph analysis, proof of measurement honesty
or cryptographic attestation of a person/device. Anchors support human review;
text that lies about behaviour is not made true by a matching hash.

## Historical CI evidence is not a new Android run

`docs/evidence/P002-baseline-ci.zip` retains original JUnit XML and two emulator
summary files from Android workflow **36944365855**, job **110642916580**, artifact
**11201464852**, for the inspected revision. The original artifact SHA-256 is
`72d4a4d5f2b6c73d75e0a7510fd05a95771032491ee93b7480358b38e6feccd1`.
A provenance manifest records each retained member hash. The capsule is a subset
of the original artifact, not a substitute for its videos or whole source ZIP.

The original XML contains **292 JVM cases and 53 emulator instrumentation cases**.
These are prior executions, not Android tests rerun by P002. The parser validates
both JUnit `testsuite` files and the nested `testsuites` instrumentation wrapper;
aggregate counts must match individual failed/error/skipped cases. Test mappings
must match the same member, class, method and evidence class. Missing execution
is `not_run`, not inferred from a source filename.

The separate original summaries explicitly say:

- Saved-RAW development: `codecRoute=unavailable`, `encodedPixelsTested=false`.
- Live lab: `backend=unavailable`, `liveCameraTested=false`.

Both retain `physicalCameraCertified=false`. A passing availability test can
correctly report no usable route. The checker preserves the raw summaries and
never promotes those JUnit passes into physical S23 or successful-codec claims.

## Tests and reproduction

Use Python 3.10 or newer and Git with the referenced history available. The new
gate needs no Android SDK, private cache or network. The existing wider host suite
keeps its separate NumPy/FFmpeg prerequisites.

```sh
python3 scripts/verify_master_directive.py
python3 scripts/verify_research_contract.py --expected-head "$(git rev-parse HEAD)"
python3 scripts/verify_repository_continuity.py --expected-head "$(git rev-parse HEAD)"
python3 -m unittest discover -s scripts/tests -p 'test_repository_continuity.py' -v
python3 -m unittest discover -s scripts/tests -v
python3 -m unittest discover -s docs/master-directive/reference -p 'test_reference.py' -v
```

The new suite has **22 test methods**. TC-P002-01 retains valid narrower findings
while rejecting unsupported physical certainty; -02 checks changed revisions,
new source and README-only/replacement-engine plans; -03 checks provenance,
missing/unreviewed references and archive safety; -04 checks raw outcomes,
JUnit summaries and misattributed execution; -05 delegates exact unit/domain
checks through retained receipts; -06 checks immutable threshold history;
-07 preserves collaborator bytes/index and detects head changes; -08 executes
an isolated CLI and verifies concrete missing-prerequisite rejection.

Set `S23_P002_EVIDENCE_DIR` to retain synthetic baseline/perturbed inputs and
outcomes. That variable only controls the test recorder, not the read-only
validator. The TDD record separates the original local experiment from fresh CI reproduction.
Original local red/green logs are retained in the conversation handoff bundle;
`docs/evidence/P002-tdd-evidence.tar.xz` contains independently rerun CI checks
and mutation inputs/results, not relabelled original local runs. Exact-commit CI
also retains fresh gate output; no future command is counted as already run.

## Remaining gates and next step

This closes the selected **bounded P002 continuity implementation**, not review
of every application file, every P002 repetition in every environment, or any
physical imaging requirement. Uninspected surfaces must be reviewed when the
next change touches them. The map does not claim firmware success, sustained
4K/8K, source precision, calibrated colour, film-stock fidelity or a finished
virtual-lens/catalogue system.

**Next: P003 production evidence adapters/classification**, using the existing
reports above and preserving their unavailable states. P004 application-baseline
acceptance follows its dependency gate; the historical CI capsule is useful
input, not a declaration that P004 is finished.
