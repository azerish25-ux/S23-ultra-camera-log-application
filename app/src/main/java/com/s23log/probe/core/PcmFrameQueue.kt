package com.s23log.probe.core

import java.nio.ByteBuffer
import java.util.ArrayDeque

/** Owns bounded PCM; only the final short block receives explicitly counted AAC end padding. */
class PcmFrameQueue(private val channels: Int, private val maxFrames: Int = 96_000) {
    init { require(channels in 1..2 && maxFrames >= 1024) }
    /** frames counts original PCM only; paddingFrames is added silence, never microphone input. */
    data class Batch(val firstFrame: Long, val frames: Int, val paddingFrames: Int, val bytes: Int, val endOfStream: Boolean)
    private data class Chunk(val bytes: ByteBuffer, var firstFrame: Long)
    private val chunks = ArrayDeque<Chunk>()
    private val bytesPerFrame = channels * 2
    private var nextFrame = 0L
    private var ended = false
    var frames = 0; private set
    fun offer(data: ByteBuffer, firstFrame: Long) {
        check(!ended) { "PCM input already ended" }
        require(data.hasRemaining() && data.remaining() % bytesPerFrame == 0)
        require(firstFrame == nextFrame) { "PCM sample positions are not contiguous" }
        val count = data.remaining() / bytesPerFrame
        check(count <= maxFrames - frames) { "Microphone encoder backlog exceeded two seconds" }
        val owned = ByteBuffer.allocate(data.remaining()).apply { put(data.duplicate()); flip() }
        chunks.addLast(Chunk(owned, firstFrame)); frames += count; nextFrame += count
    }
    fun ready(stopping: Boolean): Boolean = frames >= 1024 || (stopping && frames > 0)
    fun drainTo(destination: ByteBuffer, stopping: Boolean): Batch? {
        if (!ready(stopping)) return null
        val count = minOf(1024, frames)
        val padding = 1024 - count
        require(destination.remaining() >= 1024 * bytesPerFrame) { "AAC input cannot hold a complete PCM frame" }
        val first = chunks.first.firstFrame
        var remaining = count * bytesPerFrame
        while (remaining > 0) {
            val chunk = chunks.first
            val bytes = minOf(remaining, chunk.bytes.remaining())
            destination.put(chunk.bytes.duplicate().apply { limit(position() + bytes) })
            chunk.bytes.position(chunk.bytes.position() + bytes)
            chunk.firstFrame += bytes / bytesPerFrame
            if (!chunk.bytes.hasRemaining()) chunks.removeFirst()
            remaining -= bytes
        }
        frames -= count
        // Some AAC encoders assign a discontinuous flush timestamp to a short
        // input, even when EOS is on that buffer. Complete this last block with
        // at most 1023 silence frames. Preserve all original PCM and its clock;
        // report the added padding separately rather than rewriting output PTS.
        repeat(padding * bytesPerFrame) { destination.put(0.toByte()) }
        ended = stopping && frames == 0
        return Batch(first, count, padding, 1024 * bytesPerFrame, ended)
    }
    fun clear() { chunks.clear(); frames = 0; ended = true }
}
