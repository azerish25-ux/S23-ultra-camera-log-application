package com.s23log.probe.core

import java.nio.ByteBuffer
import java.util.ArrayDeque

/** Owns bounded interleaved PCM and emits complete AAC-LC frames, except the final tail. */
class PcmFrameQueue(private val channels: Int, private val maxFrames: Int = 96_000) {
    init { require(channels in 1..2 && maxFrames >= 1024) }
    data class Batch(val firstFrame: Long, val frames: Int, val bytes: Int)
    private data class Chunk(val bytes: ByteBuffer, var firstFrame: Long)
    private val chunks = ArrayDeque<Chunk>()
    private val bytesPerFrame = channels * 2
    private var nextFrame = 0L
    var frames = 0; private set
    fun offer(data: ByteBuffer, firstFrame: Long) {
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
        require(destination.remaining() >= count * bytesPerFrame) { "AAC input cannot hold a complete PCM frame" }
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
        return Batch(first, count, count * bytesPerFrame)
    }
    fun clear() { chunks.clear(); frames = 0 }
}
