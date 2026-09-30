# Explicit camera routes and reported lens metadata

The capture dock exposes a horizontal route rail with camera-facing labels, advertised focal lengths in millimetres and route IDs. The adjacent all-routes menu retains the full logical/physical route description. This does not infer marketing zoom labels, calibrated angle of view or cross-camera equivalence from focal length alone. Duplicate millimetre values can belong to distinct routes.

Selecting a different route immediately disables Record before the asynchronous camera switch. Controls remain disabled until the new preview is ready; a route cannot change during an active take. The current route is selected and persisted using its stable logical/physical key. The new route's settings and available modes are independently revalidated.

If a previously selected recording format is no longer advertised, preview can still open but Record stays disabled with an explicit format-selection placeholder. The saved intent is retained across recreation until the user chooses an available format. A first-run default is distinct from replacing an existing choice. Ambiguous legacy identifiers are not guessed, and changing bitrate cannot bypass a missing saved-format choice.

The APPLIED overlay and sampled recording journal retain capture-result focal length and, from API 29 when reported, the active physical-camera ID of a logical multi-camera route. Requested/advertised route metadata is not substituted for unavailable result metadata. These fields describe what the API reported, not independent optical calibration.

Landscape has a separately scrolling metadata region and a non-scrolling action dock, so Record, Controls, Info (mode evidence), the explicit 5-second test and preview Aids remain reachable. Tests switch exposed emulator routes, assert the immediate recording lockout, preserve selection across recreation, and retain portrait/landscape screenshots. The packaged adaptive icon has a separately rendered native PNG, including an API 33 monochrome variant. Physical lens transitions, framing and quality remain part of the S23 Ultra acceptance matrix.
