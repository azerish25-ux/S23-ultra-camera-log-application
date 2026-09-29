package com.s23log.probe.core

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.locks.LockSupport

/** Owns ONLY acquisition. Never calls a codec, muxer, UI listener, or waits for the consumer. */
class MicrophoneReader(
    private val channels: Int,
    private val nativeBufferFrames: Int,
    private val source: Source,
    val pipe: PcmHandoff,
    val clock: PcmClock,
    private val wakeConsumer: () -> Unit,
    private val initializeThread: () -> Unit = {}
) {
    data class Stamp(val frame: Long, val ns: Long)
    interface Source {
        fun start()
        /** Nonblocking; return interleaved sample count, zero when no data is available. */
        fun read(samples: ShortArray, count: Int): Int
        fun timestamp(): Stamp?
        fun inspect()
        fun close()
    }
    private val launched = AtomicBoolean()
    private val abort = AtomicBoolean()
    private val stopAt = AtomicLong()
    @Volatile var done = false; private set
    @Volatile var failure: Exception? = null; private set
    @Volatile var framesRead = 0L; private set
    @Volatile var maxReadIntervalUs = 0L; private set
    @Volatile var lateReads = 0; private set
    @Volatile var stopPolicy = "not_stopped"; private set
    @Volatile var drainDeadlineHit = false; private set
    @Volatile var cutoffFrame: Long? = null; private set
    @Volatile var finishedAtNs = 0L; private set
    @Volatile var levels: List<ChannelLevel> = emptyList(); private set
    @Volatile var clippingBlocks = 0; private set
    private val worker = Thread({ run() }, "S23Log-microphone").apply { isDaemon = true }
    init { require(channels in 1..2 && nativeBufferFrames > 0) }
    fun start() { check(launched.compareAndSet(false, true)); worker.start() }
    fun requestStop(cutoffNs: Long = System.nanoTime()) {
        require(cutoffNs > 0)
        stopAt.compareAndSet(0, cutoffNs); LockSupport.unpark(worker)
    }
    /** No join on encoder/UI threads. Even pre-start cancellation releases the native input on its owner. */
    fun cancel() {
        abort.set(true)
        if (launched.compareAndSet(false, true)) worker.start()
        LockSupport.unpark(worker)
    }
    private fun run() {
        val samples = ShortArray(4096 * channels)
        var firstReadNs = 0L; var firstReadFrames = 0L
        var lastPollNs = 0L; var lastPcmNs = System.nanoTime(); var lastInspectNs = 0L
        var drainUntilNs = 0L
        val startNs = System.nanoTime()
        try {
            initializeThread()
            if (abort.get() || stopAt.get() > 0) return
            source.start()
            while (!abort.get()) {
                val now = System.nanoTime()
                if (lastPollNs > 0) {
                    val delay = (now - lastPollNs) / 1000
                    maxReadIntervalUs = maxOf(maxReadIntervalUs, delay)
                    if (delay > nativeBufferFrames * 1_000_000L / AudioMode.SAMPLE_RATE) lateReads++
                }
                lastPollNs = now
                val cutoff = stopAt.get()
                if (cutoff > 0 && drainUntilNs == 0L) {
                    drainUntilNs = now + 200_000_000L
                    cutoffFrame = if (clock.quality() == "stable_nominal_clock" && lateReads == 0) clock.frameAt(cutoff) else null
                    stopPolicy = if (cutoffFrame != null) "qualified_sample_cutoff" else "available_buffer_drain_unverified"
                }
                if (cutoff > 0 && cutoffFrame?.let { framesRead >= it } == true) break
                if (drainUntilNs > 0 && now >= drainUntilNs) { drainDeadlineHit = true; break }
                val wanted = cutoffFrame?.let { minOf(4096L, (it - framesRead).coerceAtLeast(0)).toInt() } ?: 4096
                if (wanted == 0) break
                val count = source.read(samples, wanted * channels)
                check(count >= 0 && count <= wanted * channels && count % channels == 0) { "Microphone read failed or returned unaligned PCM ($count)" }
                if (count > 0) {
                    val first = framesRead
                    framesRead += count / channels
                    if (firstReadNs == 0L) { firstReadNs = System.nanoTime(); firstReadFrames = framesRead }
                    val pcm = ByteBuffer.allocate(count * 2).order(ByteOrder.nativeOrder())
                    pcm.asShortBuffer().put(samples, 0, count)
                    pipe.offer(pcm, first)
                    lastPcmNs = System.nanoTime()
                }
                // Inspect independently of receiving PCM, including privacy/route failures in silence.
                source.timestamp()?.let { clock.observe(it.frame, it.ns) }
                if (!clock.anchored && firstReadNs > 0 && (now - startNs >= 750_000_000L || cutoff > 0)) clock.estimate(firstReadFrames, firstReadNs)
                if (now - lastInspectNs >= 125_000_000L) {
                    source.inspect()
                    if (count > 0) {
                        levels = PcmLevels.measure(samples, count, channels)
                        if (levels.any { it.clipped }) clippingBlocks++
                    }
                    lastInspectNs = now
                }
                if (count > 0 || cutoff > 0) wakeConsumer()
                if (cutoff > 0 && count == 0 && cutoffFrame == null) break
                check(now - lastPcmNs <= 5_000_000_000L) { "Microphone produced no PCM for five seconds" }
                if (count == 0) LockSupport.parkNanos(2_000_000L) // Catch up immediately while data is available.
            }
        } catch (e: Exception) { failure = e }
        finally {
            if (!clock.anchored && firstReadNs > 0) clock.estimate(firstReadFrames, firstReadNs)
            try { source.close() } catch (e: Exception) { if (failure == null) failure = e }
            pipe.finish()
            finishedAtNs = System.nanoTime(); done = true
            wakeConsumer()
        }
    }
    fun continuity(): String = when {
        failure != null -> "capture_failed"
        lateReads > 0 -> "reader_starvation_risk"
        drainDeadlineHit -> "stop_drain_incomplete"
        clock.quality() != "stable_nominal_clock" -> clock.quality()
        else -> "no_discontinuity_observed"
    }
    fun describe(): Map<String, Any?> = mapOf(
        "dedicatedReader" to true, "readerTerminated" to done, "nativeBufferFrames" to nativeBufferFrames,
        "maxReadIntervalUs" to maxReadIntervalUs, "readerLatePolls" to lateReads,
        "continuityStatus" to continuity(), "failure" to failure?.message,
        "stopRequestedNs" to stopAt.get().takeIf { it > 0 }, "stopPolicy" to stopPolicy,
        "cutoffFrame" to cutoffFrame, "stopDrainDeadlineHit" to drainDeadlineHit,
        "framesBeyondEstimatedCutoff" to cutoffFrame?.let { (framesRead - it).coerceAtLeast(0) },
        "stopDrainLimitUs" to 200_000, "readerFinishedNs" to finishedAtNs,
        "handoff" to pipe.describe(), "missingInputFramesKnown" to false,
        "physicalLipSyncVerified" to false
    )
}
