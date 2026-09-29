package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicInteger

class CaptureTimingTest {
    private class Input(private val total: Int, private val batch: Int = 1024) : MicrophoneReader.Source {
        var position = 0
        val closes = AtomicInteger(); val starts = AtomicInteger()
        override fun start() { starts.incrementAndGet() }
        override fun read(samples: ShortArray, count: Int): Int {
            val n = minOf(count, batch, total - position)
            repeat(n) { samples[it] = ((position + it) % 32767).toShort() }
            position += n
            return n
        }
        override fun timestamp(): MicrophoneReader.Stamp? = null
        override fun inspect() = Unit
        override fun close() { closes.incrementAndGet() }
    }
    private fun await(predicate: () -> Boolean) {
        val deadline = System.nanoTime() + 2_000_000_000
        while (!predicate() && System.nanoTime() < deadline) Thread.sleep(2)
        assertTrue("Reader did not make bounded progress", predicate())
    }
    @Test fun readerAcquiresWhileConsumerIsCompletelyPaused() {
        val source = Input(5000, 137); val pipe = PcmHandoff(1)
        val reader = MicrophoneReader(1, 9600, source, pipe, PcmClock(48000, true), {})
        try {
            reader.start()
            await { pipe.describe()["acceptedFrames"] == 5000L }
            assertEquals(0L, pipe.describe()["consumedFrames"])
            reader.requestStop(); await { reader.done }
            assertNull(reader.failure)
            var index = 0
            while (pipe.ready()) {
                val dst = ByteBuffer.allocate(2048).order(ByteOrder.nativeOrder())
                val batch = requireNotNull(pipe.drain(dst)); dst.flip()
                repeat(batch.frames) { assertEquals((index++ % 32767).toShort(), dst.short) }
                repeat(batch.paddingFrames) { assertEquals(0.toShort(), dst.short) }
            }
            assertEquals(5000, index); assertTrue(pipe.exhausted()); assertEquals(1, source.closes.get())
            assertEquals("available_buffer_drain_unverified", reader.stopPolicy)
        } finally { reader.cancel(); await { reader.done } }
    }
    @Test fun overloadRetainsEarlierPcmAndReportsRejectedRead() {
        val source = Input(4096); val pipe = PcmHandoff(1, 2048)
        val reader = MicrophoneReader(1, 9600, source, pipe, PcmClock(48000), {})
        reader.start(); await { reader.done }
        assertNotNull(reader.failure); assertEquals(1, pipe.describe()["overflowCount"])
        assertEquals(3072L, reader.framesRead); assertEquals(2048L, pipe.describe()["acceptedFrames"])
        assertEquals("capture_failed", reader.continuity())
        assertEquals(1024, pipe.drain(ByteBuffer.allocate(2048))?.frames)
        assertEquals(1024, pipe.drain(ByteBuffer.allocate(2048))?.frames)
        assertTrue(pipe.exhausted()); assertEquals(1, source.closes.get())
    }
    @Test fun cancellingBeforeStartReleasesOwnerWithoutOpeningMicrophone() {
        val source = Input(20)
        val reader = MicrophoneReader(1, 9600, source, PcmHandoff(1), PcmClock(48000), {})
        reader.cancel(); await { reader.done }; reader.cancel()
        assertEquals(0, source.starts.get()); assertEquals(1, source.closes.get()); assertEquals(0L, reader.framesRead)
    }
    @Test fun stopBeforeStartDoesNotProduceLateSamples() {
        val source = Input(20)
        val reader = MicrophoneReader(1, 9600, source, PcmHandoff(1), PcmClock(48000), {})
        reader.requestStop(); reader.start(); await { reader.done }
        assertEquals(0, source.starts.get()); assertEquals(0L, reader.framesRead); assertEquals(1, source.closes.get())
    }
    @Test fun handoffOwnsBytesAndOnlyPadsFinalTail() {
        val pipe = PcmHandoff(2)
        val data = ByteBuffer.wrap(ByteArray(512 * 4) { 12 })
        pipe.offer(data, 0); data.put(0, 99)
        assertFalse(pipe.ready()); pipe.finish()
        val dst = ByteBuffer.allocate(4096); val batch = requireNotNull(pipe.drain(dst))
        assertEquals(512, batch.frames); assertEquals(512, batch.paddingFrames)
        assertEquals(12.toByte(), dst[0]); assertEquals(0.toByte(), dst[2048])
        assertTrue(batch.endOfStream); assertTrue(pipe.exhausted())
    }
    @Test fun shortDestinationDoesNotConsumeOrCorruptAcceptedData() {
        val pipe = PcmHandoff(1); pipe.offer(ByteBuffer.allocate(2048), 0)
        assertTrue(runCatching { pipe.drain(ByteBuffer.allocate(32)) }.isFailure)
        assertEquals(0L, pipe.describe()["consumedFrames"]); assertEquals(1024, pipe.describe()["pendingFrames"])
    }
    @Test fun finishedHandoffRejectsFurtherInput() {
        val pipe = PcmHandoff(1); pipe.finish()
        assertTrue(runCatching { pipe.offer(ByteBuffer.allocate(2), 0) }.isFailure)
    }
    @Test fun startupClockRequiresProgressAndStableOrigin() {
        val clock = PcmClock(48000, true)
        clock.observe(0, 1_000_000_000); assertFalse(clock.anchored)
        clock.observe(0, 1_001_000_000); assertFalse(clock.anchored)
        clock.observe(2400, 1_050_000_000); assertFalse(clock.anchored)
        clock.observe(4800, 1_100_000_000); assertTrue(clock.anchored)
        assertEquals("stable_nominal_clock", clock.quality()); assertEquals(4800L, clock.frameAt(1_100_000_000))
    }
    @Test fun noisyStartupDoesNotPretendFirstTimestampIsReliable() {
        val clock = PcmClock(48000, true)
        clock.observe(0, 1_000_000_000); clock.observe(2400, 1_200_000_000); clock.observe(4800, 1_350_000_000)
        assertFalse(clock.anchored)
        clock.estimate(0, 1_000_000_000)
        assertEquals("read_completion_estimate_unverified", clock.source)
        assertEquals("timestamp_discontinuity_suspected", clock.quality())
    }
    @Test fun gradualDeviationAndAbruptTimestampChangesAreDifferent() {
        val smooth = PcmClock(48000); smooth.observe(0, 1_000_000_000)
        for (second in 1L..60) smooth.observe(second * 48000, 1_000_000_000 + second * 1_001_000_000)
        assertEquals("clock_rate_deviation", smooth.quality())
        assertEquals(61_000_000L, smooth.timestampUs(60 * 48000L))
        val jump = PcmClock(48000); jump.observe(0, 1_000_000_000); jump.observe(4800, 1_150_000_000)
        assertEquals("timestamp_discontinuity_suspected", jump.quality())
    }
    @Test fun regressionNeverReanchorsOrClaimsSync() {
        val clock = PcmClock(48000); clock.observe(100, 2_000_000_000); clock.observe(90, 1_900_000_000)
        assertEquals("timestamp_regression", clock.quality()); assertEquals(2_000_000L, clock.timestampUs(100))
        assertEquals(false, clock.describe()["physicalLipSyncVerified"])
    }
}
