# Capture library

The capture library keeps an app-private index of capture results so a newer take does not replace access to older footage. Open **Controls → Capture library** while the camera is idle. Tap a row to open media in an installed player/editor, share the selected capture files, or share the original validation JSON. RAW sequences offer an individual-file picker for opening and a grouped share action.

## Storage and evidence boundaries

Each capture has a separate atomic JSON index record. Repeated completion callbacks reuse the same record. The existing latest-capture preferences stay compatible. On first opening after an upgrade, the previous latest result is imported; older captures never indexed by the previous version cannot be reconstructed from those preferences. “Added” is the indexing time, not a claim about the original recording time.

The index references original media and reports. It does not copy, rewrite, delete or relabel them. The original result message is retained, including any unverified recovery warning. Missing media or reports remain visible as unavailable. An unreadable index record is counted and does not hide readable captures. Recovery retention and confirmed deletion remain in **Recover captures**.

Reading the list does not certify codec correctness, colour precision, physical lip-sync, thermal stability or S23 Ultra support. Validation sharing sends the recorded evidence, not a new verification result. Playback availability depends on a compatible installed app; an absent player is reported without modifying media.

Only MediaStore and the app's FileProvider content URIs are accepted. No broad storage permission is requested. The library activity is not exported. Opening and sharing grant read access to the explicitly selected URIs. Work is performed off the UI thread; stale callbacks are discarded after leaving or recreating the screen.

## Verification

`CaptureLibraryTest` covers multiple captures, idempotent completion, missing media/report handling, corrupt-record isolation, rejection of foreign/file URIs, preservation of unverified labels and activity recreation without camera permission. It saves a native screenshot in `files/exports/library-ui/library.png` for visual inspection. These checks are software/storage evidence, not physical camera acceptance.

The first library version does not provide an in-app video decoder, thumbnail cache, editing, ratings, user albums or a full-device gallery scan. None is implied by external playback.
