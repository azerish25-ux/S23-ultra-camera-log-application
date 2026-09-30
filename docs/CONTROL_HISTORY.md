# Recording control history

Original validation reports retain the initial requested/effective controls and a bounded `controlHistory` journal. Each successfully submitted, changed repeating request adds requested and effective values, with callback-side monotonic reception time. Unchanged requests are deduplicated; rejected requests are not recorded as accepted. This evidence says the API accepted a request, not that the physical sensor achieved it.

Applied capture-result values are sampled at most once per second, retaining ISO, shutter, focus, white-balance and manual-match evidence. Their original sensor timestamps remain separate from observation time. The report includes the advertised sensor timestamp source; no offset, synchronization, or frame-accurate correspondence to encoded media is inferred. Exact per-frame metadata is not claimed.

The journal retains up to 256 changed requests and 1024 sampled results (approximately 17 minutes at the sampling interval). Both caps are explicit, overflow counts are reported, and the latest accepted request and latest result remain available even after the history fills. Missing/null sensor fields remain unmeasured. The data is protected against concurrent snapshot access and caller mutation of nested input maps.

Unit tests cover bounded storage, loss accounting, independent clocks, deduplication, snapshots and invalid observation clocks. The native recording test changes auto-exposure control intent during a take, then verifies both request history and multiple real capture-result samples in the original report. It deliberately does not claim that changing the stored ISO while AE is on changes the sensor's ISO.
