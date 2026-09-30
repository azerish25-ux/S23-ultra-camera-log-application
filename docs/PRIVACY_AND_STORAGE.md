# Local data and permission behavior

The Android app has no Internet permission, account system, advertising SDK or application analytics integration. Camera and optional Microphone are runtime permissions. Microphone refusal does not silently substitute a muted take: video-only is a separate explicit choice. No location or broad storage permission is requested.

Preview processing remains within the device. Accepted settings and the capture index are app-private. Thumbnails are bounded application cache data. Camera/codec diagnostics, validation reports, DNG exports, recovery footage and colour-reference assets are kept under the app's export area. Android backup is disabled for the app. Successful modern-Android recordings are published through MediaStore; older supported Android versions use private files with temporary share grants.

Reports can include the phone/build identity, camera/codec metadata, requested and reported controls, timestamps, recording properties and byte identities. Media and DNG files can contain normal camera/format metadata. Review them before sharing. The app's share action opens a user-selected target and grants access only to selected content URIs. FileProvider is not a general export of app storage.

Recovery prioritizes nonempty footage. Unverified or unfinished recordings are not labelled checked gallery media. Removing app data or uninstalling can remove private captures, reports, settings and recovery files; export anything needed first. Files already published to MediaStore follow the platform's media behavior. This implementation note is not a legal privacy policy for a released service.
