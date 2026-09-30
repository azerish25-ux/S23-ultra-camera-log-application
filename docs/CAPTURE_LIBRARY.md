# Capture library

The capture library keeps an app-private index of capture results so a newer take does not replace access to older footage. Open **Clips** while the camera is idle. Tap a row to open media in an installed player/editor, share the selected capture files, or share the original validation JSON. RAW sequences offer an individual-file picker for opening and a grouped share action.

## Storage and evidence boundaries

Each capture has a separate atomic JSON index record. Repeated completion callbacks reuse the same record. The existing latest-capture preferences stay compatible. On first opening after an upgrade, the previous latest result is imported; older captures never indexed by the previous version cannot be reconstructed from those preferences. “Added” is the indexing time, not a claim about the original recording time.

The index references original media and reports. It does not copy, rewrite, delete or relabel them. The original result message is retained, including any unverified recovery warning. Missing media or reports remain visible as unavailable. An unreadable index record is counted and does not hide readable captures. Recovery retention and confirmed deletion remain in **Recover captures**.

Reading the list does not certify codec correctness, colour precision, physical lip-sync, thermal stability or S23 Ultra support. Validation sharing sends the recorded evidence, not a new verification result. Playback availability depends on a compatible installed app; an absent player is reported without modifying media.

Only MediaStore and the app's FileProvider content URIs are accepted. No broad storage permission is requested. The library activity is not exported. Opening and sharing grant read access to the explicitly selected URIs. Work is performed off the UI thread; stale callbacks are discarded after leaving or recreating the screen.

## Verification

`CaptureLibraryTest` covers multiple captures, idempotent completion, missing media/report handling, corrupt-record isolation, rejection of foreign/file URIs, preservation of unverified labels and activity recreation without camera permission. It saves a native screenshot in `files/exports/library-ui/library.png` for visual inspection. These checks are software/storage evidence, not physical camera acceptance.

The library keeps a bounded 4 MiB in-memory cache of scaled video thumbnails on API 27+. Missing/undecodable thumbnails and API 26 remain explicit placeholders; they do not change the original media or report status. Recorded dimensions, codec, colour tags and measured cadence are read from the original validation evidence. Requested frame rate is labelled separately, and missing bit-depth evidence remains unmeasured. The full original result remains available under **Original capture result**.

There is no in-app video editor, ratings, user albums or full-device gallery scan. Playback uses an installed compatible player/editor.

## Matched video and validation export

Newly verified recordings carry a SHA-256 digest and exact byte count for the finalized MP4 container. This identity is measured before publication, and the gallery copy retains those original bytes. **Share matched video + validation** re-reads the current video and compares its identity with the selected original report before opening a two-file share chooser. Reading uses bounded buffers, and leaving the library cancels further hashing and prevents stale sharing.

The check establishes byte identity at export preparation time, not an immutable external copy, physical image quality or a trusted third-party attestation. Original reports without an identity, changed/missing media and RAW sequences do not receive a matched-video claim; separate original-file sharing remains available. No media is rewritten or deleted on failure.

Current CI independently hashes fully decoded movies and requires one-to-one digest/length agreement with their device reports. Missing, mismatched and ambiguous duplicate identities fail that gate even if all file/report counts match. Historical evidence can still be inspected without the new flag, but explicitly reports that identities were not matched.
