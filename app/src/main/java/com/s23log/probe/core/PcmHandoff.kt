package com.s23log.probe.core

import java.nio.ByteBuffer

/** Bounded producer/consumer ownership. A full queue fails, never evicts earlier microphone data. */
class PcmHandoff(channels: Int, val capacityFrames: Int = 96_000) {
    private val queue = PcmFrameQueue(channels, capacityFrames)
    private val bytesPerFrame = channels * 2
    private var producerEnded = false
    private var cancelled = false
    private var accepted = 0L
    private var consumed = 0L
    private var highWater = 0
    private var overflows = 0
    @Synchronized fun offer(data: ByteBuffer, firstFrame: Long) {
        check(!producerEnded && !cancelled) { "Microphone handoff is closed" }
        val frames = data.remaining() / bytesPerFrame
        if (frames > capacityFrames - queue.frames) { overflows++; error("Audio queue overload: two-second PCM budget exhausted; no silent eviction") }
        queue.offer(data, firstFrame)
        accepted += frames
        highWater = maxOf(highWater, queue.frames)
    }
    @Synchronized fun finish() { producerEnded = true }
    @Synchronized fun drain(destination: ByteBuffer): PcmFrameQueue.Batch? =
        if (cancelled) null else queue.drainTo(destination, producerEnded)?.also { consumed += it.frames }
    @Synchronized fun ready(): Boolean = !cancelled && queue.ready(producerEnded)
    @Synchronized fun exhausted(): Boolean = producerEnded && queue.frames == 0
    @Synchronized fun cancel() { cancelled = true; producerEnded = true; queue.clear() }
    @Synchronized fun describe(): Map<String, Any> = mapOf(
        "capacityFrames" to capacityFrames, "highWaterFrames" to highWater,
        "acceptedFrames" to accepted, "consumedFrames" to consumed,
        "pendingFrames" to queue.frames, "overflowCount" to overflows,
        "unsubmittedAcceptedFrames" to (accepted - consumed), "producerEnded" to producerEnded
    )
}
