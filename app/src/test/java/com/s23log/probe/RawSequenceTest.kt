package com.s23log.probe

import com.s23log.probe.core.RawFrameMatcher
import com.s23log.probe.core.RawSequenceFormat
import com.s23log.probe.core.RawSequencePlan
import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.zip.CRC32

class RawSequenceTest {
    @Test fun highResolutionIsMemoryBoundNotTwentyFourMegapixelBound() {
        val plan = RawSequencePlan(7680, 4320, 24, 5, true, 2)
        assertEquals(66_355_200, plan.frameBytes)
        assertNull(plan.rejection(2L * 1024 * 1024 * 1024, 100L * 1024 * 1024 * 1024))
        assertNotNull(plan.rejection(128L * 1024 * 1024, Long.MAX_VALUE))
        assertNotNull(plan.rejection(Long.MAX_VALUE, 100))
    }
    @Test fun acquisitionBenchmarkDoesNotPretendToSavePixels() {
        val plan = RawSequencePlan(8000, 6000, 30, 5, false)
        assertEquals(0L, plan.poolBytes); assertEquals(0L, plan.expectedPayloadBytes)
    }
    @Test(expected = IllegalArgumentException::class) fun overflowDimensionsAreRejected() {
        RawSequencePlan(Int.MAX_VALUE - 1, Int.MAX_VALUE - 1, 30, 5, true)
    }
    @Test fun eitherArrivalOrderMatchesTheExactTimestamp() {
        val matched = mutableListOf<String>()
        val join = RawFrameMatcher<String, String>(2, { _, _ -> fail() }, { fail() }, { t, i, m -> matched += "$t:$i:$m" })
        join.image(10, "a"); join.result(11, "B"); join.result(10, "A"); join.image(11, "b")
        assertEquals(listOf("10:a:A", "11:b:B"), matched)
    }
    @Test fun overflowAndStopReleaseEveryOwnedImageOnce() {
        val discarded = mutableListOf<String>()
        val join = RawFrameMatcher<String, String>(2, { image, _ -> discarded += image }, {}, { _, _, _ -> fail() })
        join.image(1, "one"); join.image(2, "two"); join.image(3, "three")
        join.clear(); join.clear()
        assertEquals(listOf("one", "two", "three"), discarded)
    }
    @Test fun missingImagesAreCountedNotSilentlyIgnored() {
        var missing = 0
        val join = RawFrameMatcher<String, String>(1, { _, _ -> fail() }, { missing++ }, { _, _, _ -> fail() })
        join.result(1, "one"); join.result(2, "two"); join.clear()
        assertEquals(2, missing)
    }
    @Test fun recordsHaveIndependentLittleEndianLengthAndCrc() {
        val stream = ByteArrayOutputStream()
        RawSequenceFormat.header(stream, "{}".toByteArray())
        val metadata = "{\"sensorTimestampNs\":1}".toByteArray()
        val pixels = byteArrayOf(0, 0, -1, 15)
        RawSequenceFormat.frame(stream, metadata, pixels)
        val bytes = stream.toByteArray()
        assertEquals("S23RAW01", String(bytes, 0, 8, Charsets.US_ASCII))
        val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(2, b.getInt(8))
        assertEquals("FRM1", String(bytes, 14, 4, Charsets.US_ASCII))
        assertEquals(metadata.size, b.getInt(18)); assertEquals(4L, b.getLong(22))
        val crc = CRC32().apply { update(bytes, 18, 12 + metadata.size + pixels.size) }
        assertEquals(crc.value, b.getInt(bytes.size - 4).toLong() and 0xffffffffL)
    }
    @Test(expected = IllegalArgumentException::class) fun invalidRecordPayloadRejected() {
        RawSequenceFormat.frame(ByteArrayOutputStream(), "{}".toByteArray(), byteArrayOf(1))
    }
}
