package com.s23log.probe.core

import java.nio.ByteBuffer
import java.util.ArrayDeque

/** Called exclusively by the recorder's encoder handler. No Android dependency, no unbounded queues. */
class AvMuxCoordinator<F>(
    audioRequired: Boolean,
    private val sink: Sink<F>,
    private val onWritten: (Track, Int, Long) -> Unit,
    private val maxPendingBytes: Int = 32 * 1024 * 1024,
    private val maxPendingPackets: Int = 512
) {
    enum class Track { VIDEO, AUDIO }
    interface Sink<F> {
        fun start(formats: Map<Track, F>)
        fun write(track: Track, buffer: ByteBuffer, ptsUs: Long, flags: Int)
    }
    private data class Packet(val track: Track, val buffer: ByteBuffer, val ptsUs: Long, val flags: Int)
    private val required = if (audioRequired) setOf(Track.VIDEO, Track.AUDIO) else setOf(Track.VIDEO)
    private val formats = linkedMapOf<Track, F>()
    private val first = mutableMapOf<Track, Long>()
    private val latest = mutableMapOf<Track, Long>()
    private val pending = ArrayDeque<Packet>()
    var pendingBytes = 0; private set
    var originUs: Long? = null; private set
    var started = false; private set
    var partial = false; private set
    private var closed = false
    val ready: Boolean get() = required.all { it in formats && it in first }

    fun format(track: Track, format: F) {
        check(!closed && !started) { "Late encoder format change" }
        check(track in required && track !in formats) { "Unexpected/duplicate track" }
        formats[track] = format
        if (ready) start(false)
    }
    fun sample(track: Track, buffer: ByteBuffer, ptsUs: Long, flags: Int) {
        check(!closed && track in required)
        require(buffer.hasRemaining() && ptsUs >= 0) { "Empty sample or invalid timestamp" }
        require(latest[track]?.let { ptsUs > it } != false) { "Non-monotonic $track timestamps" }
        if (!started) {
            check(buffer.remaining() <= maxPendingBytes - pendingBytes && pending.size < maxPendingPackets) {
                "Encoder startup buffering limit exceeded; footage needs recovery"
            }
            val copy = ByteBuffer.allocate(buffer.remaining()).apply { put(buffer.duplicate()); flip() }
            pending.addLast(Packet(track, copy, ptsUs, flags)); pendingBytes += copy.remaining()
        }
        latest[track] = ptsUs; first.putIfAbsent(track, ptsUs)
        if (started) write(Packet(track, buffer.duplicate(), ptsUs, flags))
        else if (ready) start(false)
    }
    private fun start(recovery: Boolean) {
        var selected = if (recovery) formats.filterKeys { it in first } else formats.toMap()
        val clocksRelated = first.size < 2 || requireNotNull(first.values.maxOrNull()) - requireNotNull(first.values.minOrNull()) <= 5_000_000
        if (!clocksRelated) {
            check(recovery) { "Audio/video clocks differ by over five seconds; refusing a fabricated synchronization" }
            selected = selected.filterKeys { it == Track.VIDEO }
        }
        if (selected.isEmpty()) return
        val origin = first.filterKeys { it in selected }.values.minOrNull() ?: return
        sink.start(selected)
        originUs = origin; started = true; partial = recovery && (!ready || !clocksRelated)
        while (pending.isNotEmpty()) {
            val packet = pending.removeFirst(); pendingBytes -= packet.buffer.remaining()
            if (packet.track in selected) write(packet)
        }
    }
    private fun write(packet: Packet) {
        val pts = packet.ptsUs - requireNotNull(originUs)
        require(pts >= 0) { "Sample precedes common recording epoch" }
        val size = packet.buffer.remaining()
        sink.write(packet.track, packet.buffer, pts, packet.flags)
        onWritten(packet.track, size, pts)
    }
    /** Flush already received footage on failure/early stop; never call it a successful A/V recording. */
    fun finish(): Boolean {
        if (closed) return partial
        try { if (!started) start(true) } finally { closed = true; pending.clear(); pendingBytes = 0 }
        return partial
    }
}

/** First successfully written samples from every requested track are required, not just formats. */
class AvStartGate(private val audioRequired: Boolean) {
    private var video = false; private var audio = false; private var stopped = false; private var notified = false
    fun written(track: AvMuxCoordinator.Track): Boolean {
        if (track == AvMuxCoordinator.Track.VIDEO) video = true else audio = true
        if (stopped || notified || !video || (audioRequired && !audio)) return false
        notified = true; return true
    }
    fun stop() { stopped = true }
}
