package com.s23log.probe

import com.s23log.probe.core.PcmFrameQueue
import org.junit.Assert.*
import org.junit.Test
import java.nio.ByteBuffer

class PcmFrameQueueTest {
    @Test fun partialReadsWaitAndCoalesceAtExactSamplePositions() {
        val queue = PcmFrameQueue(1)
        val input = ByteBuffer.allocate(2048)
        queue.offer(ByteBuffer.wrap(ByteArray(400) { 1 }), 0)
        assertFalse(queue.ready(false)); assertNull(queue.drainTo(input, false))
        queue.offer(ByteBuffer.wrap(ByteArray(2000) { 2 }), 200)
        val batch = requireNotNull(queue.drainTo(input, false))
        assertEquals(0L, batch.firstFrame); assertEquals(1024, batch.frames)
        assertEquals(176, queue.frames)
        assertTrue(input.array().take(400).all { it == 1.toByte() })
        assertTrue(input.array().drop(400).all { it == 2.toByte() })
        assertFalse(queue.ready(false)); assertTrue(queue.ready(true))
        input.clear()
        val tail = requireNotNull(queue.drainTo(input, true))
        assertEquals(1024L, tail.firstFrame); assertEquals(176, tail.frames)
        assertEquals(0, queue.frames)
    }
    @Test fun mutableReadBuffersCannotChangeQueuedPcm() {
        val queue = PcmFrameQueue(2)
        val data = ByteBuffer.wrap(ByteArray(4096) { 7 })
        queue.offer(data, 0); data.put(0, 99)
        val output = ByteBuffer.allocate(4096)
        assertEquals(4096, queue.drainTo(output, false)?.bytes)
        assertEquals(7.toByte(), output.get(0))
    }
    @Test fun irregularReadsProduceContinuous1024FrameBatches() {
        val queue = PcmFrameQueue(2)
        var offered = 0L; var drained = 0L
        repeat(500) { i ->
            val count = 1 + i * 37 % 1300
            queue.offer(ByteBuffer.allocate(count * 4), offered); offered += count
            while (queue.ready(false)) {
                val batch = requireNotNull(queue.drainTo(ByteBuffer.allocate(4096), false))
                assertEquals(drained, batch.firstFrame); assertEquals(1024, batch.frames); drained += batch.frames
            }
        }
        queue.drainTo(ByteBuffer.allocate(4096), true)?.let { assertEquals(drained, it.firstFrame); drained += it.frames }
        assertEquals(offered, drained)
    }
    @Test(expected = IllegalArgumentException::class) fun missingInputFramesRejected() {
        PcmFrameQueue(1).offer(ByteBuffer.allocate(16), 1)
    }
    @Test(expected = IllegalArgumentException::class) fun partialChannelFrameRejected() {
        PcmFrameQueue(2).offer(ByteBuffer.allocate(6), 0)
    }
    @Test(expected = IllegalStateException::class) fun backlogBounded() {
        PcmFrameQueue(1, 1024).offer(ByteBuffer.allocate(2050), 0)
    }
    @Test fun undersizedEncoderInputDoesNotDropQueuedSamples() {
        val queue = PcmFrameQueue(1); queue.offer(ByteBuffer.allocate(2048), 0)
        try { queue.drainTo(ByteBuffer.allocate(8), false); fail() } catch (_: IllegalArgumentException) { }
        assertEquals(1024, queue.frames)
    }
    @Test fun onlyLastValidBufferCarriesEosWhenStopping() {
        for (channels in 1..2) for (tail in listOf(1, 128, 512, 640, 1023, 1024)) {
            val queue = PcmFrameQueue(channels)
            val total = 2048 + tail
            queue.offer(ByteBuffer.allocate(total * channels * 2), 0)
            var consumed = 0L
            var eosCount = 0
            while (queue.ready(true)) {
                val batch = requireNotNull(queue.drainTo(ByteBuffer.allocate(4096), true))
                assertEquals(consumed, batch.firstFrame)
                consumed += batch.frames
                assertEquals(consumed == total.toLong(), batch.endOfStream)
                if (batch.endOfStream) eosCount++
            }
            assertEquals(total.toLong(), consumed)
            assertEquals(1, eosCount)
            assertNull(queue.drainTo(ByteBuffer.allocate(4096), true))
        }
    }
    @Test fun liveInputNeverSignalsEndAndEmptyStopDoesNotInventPcm() {
        val queue = PcmFrameQueue(1)
        queue.offer(ByteBuffer.allocate(2048), 0)
        assertFalse(requireNotNull(queue.drainTo(ByteBuffer.allocate(2048), false)).endOfStream)
        assertFalse(queue.ready(true))
        assertNull(queue.drainTo(ByteBuffer.allocate(2048), true))
    }
}
