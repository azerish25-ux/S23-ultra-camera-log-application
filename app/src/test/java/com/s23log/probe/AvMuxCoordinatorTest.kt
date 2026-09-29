package com.s23log.probe

import com.s23log.probe.core.AvMuxCoordinator
import com.s23log.probe.core.AvMuxCoordinator.Track
import com.s23log.probe.core.AvStartGate
import org.junit.Assert.*
import org.junit.Test
import java.nio.ByteBuffer

class AvMuxCoordinatorTest {
    private class Sink : AvMuxCoordinator.Sink<String> {
        var starts = 0
        var formats: Map<Track, String> = emptyMap()
        val written = mutableListOf<Triple<Track, Long, ByteArray>>()
        var failWrite = false
        override fun start(formats: Map<Track, String>) { starts++; this.formats = formats }
        override fun write(track: Track, buffer: ByteBuffer, ptsUs: Long, flags: Int) {
            check(!failWrite) { "Injected disk error" }
            written += Triple(track, ptsUs, ByteArray(buffer.remaining()).also { buffer.duplicate().get(it) })
        }
    }
    private fun data() = ByteBuffer.wrap(byteArrayOf(1, 2, 3))
    @Test fun neitherFormatAloneNorVideoAloneStartsAudioRecording() {
        val sink = Sink(); var calls = 0
        val gate = AvStartGate(true)
        val mux = AvMuxCoordinator(true, sink, { t, _, _ -> if (gate.written(t)) calls++ })
        mux.format(Track.VIDEO, "video"); mux.sample(Track.VIDEO, data(), 1_000_000, 0)
        assertEquals(0, sink.starts)
        mux.format(Track.AUDIO, "audio"); assertEquals(0, calls)
        mux.sample(Track.AUDIO, data(), 1_020_000, 0)
        assertEquals(1, sink.starts); assertEquals(1, calls)
        assertEquals(0L, sink.written[0].second); assertEquals(20_000L, sink.written[1].second)
    }
    @Test fun audioBeforeVideoPreservesTheOtherDirectionOfOffset() {
        val sink = Sink(); val mux = AvMuxCoordinator(true, sink, { _, _, _ -> })
        mux.format(Track.AUDIO, "audio"); mux.format(Track.VIDEO, "video")
        mux.sample(Track.AUDIO, data(), 900_000, 0); mux.sample(Track.VIDEO, data(), 1_000_000, 1)
        assertEquals(listOf(0L, 100_000L), sink.written.map { it.second })
    }
    @Test fun pendingPacketsOwnTheirBytesAfterCodecBufferReuse() {
        val sink = Sink(); val mux = AvMuxCoordinator(true, sink, { _, _, _ -> })
        mux.format(Track.VIDEO, "video"); val buffer = data()
        mux.sample(Track.VIDEO, buffer, 1, 1); buffer.put(0, 99)
        mux.format(Track.AUDIO, "audio"); mux.sample(Track.AUDIO, data(), 2, 0)
        assertArrayEquals(byteArrayOf(1,2,3), sink.written[0].third)
    }
    @Test fun videoOnlyDoesNotWaitForAnUnrequestedMicrophone() {
        val sink = Sink(); val mux = AvMuxCoordinator(false, sink, { _, _, _ -> })
        mux.format(Track.VIDEO, "video"); mux.sample(Track.VIDEO, data(), 1234, 1)
        assertEquals(setOf(Track.VIDEO), sink.formats.keys); assertEquals(0L, sink.written.single().second)
        assertFalse(mux.finish()); assertFalse(mux.finish()); assertEquals(1, sink.starts)
    }
    @Test fun missingAudioCanOnlyBeFlushedAsPartialRecovery() {
        val sink = Sink(); val gate = AvStartGate(true); var starts = 0
        val mux = AvMuxCoordinator(true, sink, { t, _, _ -> if (gate.written(t)) starts++ })
        mux.format(Track.VIDEO, "video"); mux.sample(Track.VIDEO, data(), 5, 1)
        gate.stop(); assertTrue(mux.finish())
        assertEquals(0, starts); assertEquals(setOf(Track.VIDEO), sink.formats.keys); assertEquals(1, sink.written.size)
    }
    @Test fun startupBufferIsBoundedAndAlreadyReceivedVideoCanBeRecovered() {
        val sink = Sink(); val mux = AvMuxCoordinator(true, sink, { _, _, _ -> }, maxPendingBytes = 4)
        mux.format(Track.VIDEO, "video"); mux.sample(Track.VIDEO, data(), 1, 1)
        try { mux.sample(Track.VIDEO, data(), 2, 0); fail("Expected bound") } catch (_: IllegalStateException) { }
        assertEquals(3, mux.pendingBytes); assertTrue(mux.finish()); assertEquals(0, mux.pendingBytes)
    }
    @Test(expected = IllegalStateException::class) fun packetCountAlsoBounded() {
        val mux = AvMuxCoordinator(true, Sink(), { _, _, _ -> }, maxPendingPackets = 1)
        mux.sample(Track.VIDEO, data(), 1, 1); mux.sample(Track.VIDEO, data(), 2, 0)
    }
    @Test(expected = IllegalArgumentException::class) fun duplicateTimestampsRejectedPerTrack() {
        val mux = AvMuxCoordinator(false, Sink(), { _, _, _ -> })
        mux.format(Track.VIDEO, "v"); mux.sample(Track.VIDEO, data(), 1, 1); mux.sample(Track.VIDEO, data(), 1, 1)
    }
    @Test(expected = IllegalStateException::class) fun secondFormatRejected() {
        val mux = AvMuxCoordinator(false, Sink(), { _, _, _ -> }); mux.format(Track.VIDEO, "v"); mux.format(Track.VIDEO, "v2")
    }
    @Test(expected = IllegalStateException::class) fun unwantedAudioRejected() {
        AvMuxCoordinator(false, Sink(), { _, _, _ -> }).format(Track.AUDIO, "a")
    }
    @Test(expected = IllegalStateException::class) fun lateSamplesCannotRestartFinalizedMuxer() {
        val mux = AvMuxCoordinator(false, Sink(), { _, _, _ -> }); mux.finish(); mux.sample(Track.VIDEO, data(), 1, 1)
    }
    @Test fun failedWritesNeverAcknowledgeSamples() {
        val sink = Sink(); sink.failWrite = true; var count = 0
        val mux = AvMuxCoordinator(false, sink, { _, _, _ -> count++ })
        mux.format(Track.VIDEO, "v")
        try { mux.sample(Track.VIDEO, data(), 1, 1); fail("Expected write failure") } catch (_: IllegalStateException) { }
        assertEquals(0, count)
    }
    @Test fun stoppingBeforeAudioArrivesCannotResurrectRecording() {
        val gate = AvStartGate(true)
        assertFalse(gate.written(Track.VIDEO)); gate.stop(); assertFalse(gate.written(Track.AUDIO))
    }
    @Test fun recordingIsAcknowledgedOnceOnly() {
        val gate = AvStartGate(true)
        assertFalse(gate.written(Track.AUDIO)); assertTrue(gate.written(Track.VIDEO)); assertFalse(gate.written(Track.AUDIO))
    }
}
