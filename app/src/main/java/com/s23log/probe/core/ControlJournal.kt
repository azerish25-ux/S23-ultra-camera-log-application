package com.s23log.probe.core

/** Bounded recording-side evidence. Sampled metadata is not a per-frame sensor trace. */
class ControlJournal(private val sampleCapacity: Int = 1024, private val requestCapacity: Int = 256,
                     private val sampleIntervalNs: Long = 1_000_000_000L) {
    init { require(sampleCapacity > 0 && requestCapacity > 0 && sampleIntervalNs > 0) }
    private val samples = mutableListOf<Map<String, Any?>>()
    private val requests = mutableListOf<Map<String, Any?>>()
    private var lastSampleAt: Long? = null
    private var lastObservedAt: Long? = null
    private var lastRequestAt: Long? = null
    private var previousRequest: Map<String, Any?>? = null
    private var latestRequest: Map<String, Any?>? = null
    private var latest: Map<String, Any?>? = null
    private var samplesDropped = 0L
    private var requestsDropped = 0L
    private var invalidClocks = 0L
    private fun freeze(value: Any?): Any? = when (value) {
        is Map<*, *> -> value.entries.associate { it.key.toString() to freeze(it.value) }
        is List<*> -> value.map(::freeze)
        else -> value
    }
    private fun copy(values: Map<String, Any?>) = values.mapValues { freeze(it.value) }
    @Synchronized fun noteRequest(monotonicNs: Long, values: Map<String, Any?>) {
        if (monotonicNs <= 0 || lastRequestAt?.let { monotonicNs < it } == true) { invalidClocks++; return }
        lastRequestAt = monotonicNs
        val snapshot = copy(values)
        if (snapshot == previousRequest) return
        previousRequest = snapshot
        latestRequest = mapOf("observedMonotonicNs" to monotonicNs, "controls" to snapshot)
        if (requests.size < requestCapacity) requests += requireNotNull(latestRequest)
        else requestsDropped++
    }
    @Synchronized fun noteApplied(monotonicNs: Long, values: Map<String, Any?>) {
        val previous = lastSampleAt
        if (monotonicNs <= 0 || lastObservedAt?.let { monotonicNs < it } == true) { invalidClocks++; return }
        lastObservedAt = monotonicNs
        val snapshot = mapOf("observedMonotonicNs" to monotonicNs, "values" to copy(values))
        latest = snapshot
        if (previous != null && monotonicNs - previous < sampleIntervalNs) return
        lastSampleAt = monotonicNs
        if (samples.size < sampleCapacity) samples += snapshot else samplesDropped++
    }
    @Synchronized fun describe(): Map<String, Any?> = mapOf(
        "schemaVersion" to 1, "sampleIntervalNs" to sampleIntervalNs,
        "sampleCapacity" to sampleCapacity, "requestCapacity" to requestCapacity,
        "requests" to requests.toList(), "latestRequest" to latestRequest, "appliedSamples" to samples.toList(), "latestApplied" to latest,
        "samplesDropped" to samplesDropped, "requestsDropped" to requestsDropped, "invalidClockObservations" to invalidClocks,
        "scope" to "Accepted repeating-request changes and sampled capture-result metadata; not every frame or proof of physical control accuracy",
        "clock" to "observedMonotonicNs is callback-reception time; sensorTimestampNs keeps the camera clock without an assumed offset")
}
