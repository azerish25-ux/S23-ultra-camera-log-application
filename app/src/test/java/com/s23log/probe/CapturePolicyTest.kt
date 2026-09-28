package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test
import java.io.IOException

class CapturePolicyTest {
    @Test fun standardIsNotTenBit() { assertFalse(CapturePolicy.isTenBitProfile(1)) }
    @Test fun dolbyEightBitIsNotTenBit() { for (p in listOf(256L, 512L, 1024L, 2048L)) assertFalse(CapturePolicy.isTenBitProfile(p)) }
    @Test fun unknownProfileIsNotAssumedTenBit() { assertFalse(CapturePolicy.isTenBitProfile(4096)) }
    @Test fun documentedTenBitProfilesAreRecognized() { for (p in listOf(2L, 4L, 8L, 16L, 32L, 64L, 128L)) assertTrue(CapturePolicy.isTenBitProfile(p)) }
    @Test fun hlgRequiresCapabilityFlag() { assertFalse(CapturePolicy.supportsHlg(false, setOf(1, 2))) }
    @Test fun hlgRequiresExactProfile() { assertFalse(CapturePolicy.supportsHlg(true, setOf(1, 4, 256))) }
    @Test fun hlgDoesNotRequireP010ByteBufferSupport() { assertTrue(CapturePolicy.supportsHlg(true, setOf(1, 2))) }
    @Test fun unknownTimingIsCandidateNotProof() { assertTrue(CapturePolicy.nominalRateFits(0, 30)) }
    @Test fun timingTooSlowIsRejected() { assertFalse(CapturePolicy.nominalRateFits(40_000_000, 30)) }
    @Test fun invalidRatesAndTimingsAreRejected() { assertFalse(CapturePolicy.nominalRateFits(1, 0)); assertFalse(CapturePolicy.nominalRateFits(-1, 30)) }
    @Test fun nanosecondRoundingIsAccepted() { assertTrue(CapturePolicy.nominalRateFits(33_333_334, 30)) }
    @Test fun dynamicRangeConstraintsAreSymmetric() { assertFalse(CapturePolicy.allowsPair(setOf(2), setOf(2), 1, 2)) }
    @Test fun unconstrainedProfilesMayMix() { assertTrue(CapturePolicy.allowsPair(emptySet(), emptySet(), 1, 2)) }
    @Test fun restrictedProfilesMayMixWhenMutual() { assertTrue(CapturePolicy.allowsPair(setOf(1, 2), setOf(1, 2), 1, 2)) }
    @Test fun videoExposureIsBoundedByFrameInterval() { assertEquals(33_333_333L, CapturePolicy.exposureForRate(1_000_000_000, 1000, 2_000_000_000, 30)) }
    @Test fun exposureRespectsSensorLowerBound() { assertEquals(1000L, CapturePolicy.exposureForRate(1, 1000, 1_000_000_000, 30)) }
    @Test(expected = IllegalArgumentException::class) fun impossibleExposureIntervalIsRejected() { CapturePolicy.exposureForRate(1, 50_000_000, 100_000_000, 30) }
    @Test fun orientationHandlesFrontAndBack() {
        assertEquals(90, CapturePolicy.orientation(90, 0, false))
        assertEquals(0, CapturePolicy.orientation(90, 90, false))
        assertEquals(180, CapturePolicy.orientation(90, 270, false))
        assertEquals(0, CapturePolicy.orientation(270, 90, true))
        assertEquals(180, CapturePolicy.orientation(270, 270, true))
    }
    @Test fun staleCallbacksAreInvalidated() { val epoch = SessionEpoch(); val old = epoch.next(); assertTrue(epoch.isCurrent(old)); epoch.next(); assertFalse(epoch.isCurrent(old)) }
    @Test fun onlyPreviewMayStartRecording() { EngineState.entries.forEach { assertEquals(it == EngineState.PREVIEW, CapturePolicy.canStartRecording(it)) } }
    @Test fun busyStatesCannotSwitchCamera() { listOf(EngineState.OPENING, EngineState.STARTING, EngineState.RECORDING, EngineState.STOPPING, EngineState.RAW).forEach { assertFalse(CapturePolicy.canChangeCamera(it)) } }
    @Test fun saveFailurePreservesSuccessfulScan() {
        val result = scanAndSave({ "complete report" }) { throw IOException("disk full") }
        assertEquals("complete report", result.value); assertNull(result.scanError); assertTrue(result.saveError!!.contains("disk full"))
    }
    @Test fun scanFailureDoesNotAttemptSave() {
        var saved = false
        val result = scanAndSave<String>({ throw IllegalStateException("camera failed") }) { saved = true }
        assertNull(result.value); assertNotNull(result.scanError); assertFalse(saved)
    }
    @Test fun successHasNoError() { val result = scanAndSave({ 42 }) {}; assertEquals(42, result.value); assertNull(result.scanError); assertNull(result.saveError) }
    @Test fun timestampsPairImageFirst() { val m = TimestampMatcher<String, Int>(2) {}; assertNull(m.image(10, "image")); assertEquals("image" to 8, m.result(10, 8)) }
    @Test fun timestampsPairResultFirst() { val m = TimestampMatcher<String, Int>(2) {}; assertNull(m.result(10, 8)); assertEquals("image" to 8, m.image(10, "image")) }
    @Test fun mismatchedTimestampsAreNeverPaired() { val m = TimestampMatcher<String, Int>(2) {}; m.image(10, "image"); assertNull(m.result(11, 8)) }
    @Test fun rawQueueIsBoundedAndReleasesImages() { val released = mutableListOf<String>(); val m = TimestampMatcher<String, Int>(1) { released.add(it) }; m.image(1, "first"); m.image(2, "second"); assertEquals(listOf("first"), released); m.clear(); assertEquals(listOf("first", "second"), released) }
    @Test fun duplicateImageReleasesOldOwnership() { val released = mutableListOf<String>(); val m = TimestampMatcher<String, Int>(2) { released.add(it) }; m.image(1, "old"); m.image(1, "new"); assertEquals(listOf("old"), released); assertEquals("new" to 2, m.result(1, 2)) }
    @Test fun emptyOrSingleFrameDoesNotInventRate() { val s = FrameStatistics(30); assertNull(s.summary().measuredFps); s.add(0); assertNull(s.summary().measuredFps) }
    @Test fun measuredRateUsesIntervalsNotFrameCount() { val s = FrameStatistics(30); for (n in 0..30) s.add(n * 1_000_000L / 30); assertEquals(30.0, s.summary().measuredFps!!, 0.001) }
    @Test fun duplicateOrDecreasingTimestampsAreInvalid() { val s = FrameStatistics(30); s.add(100); s.add(100); s.add(50); assertEquals(2, s.summary().invalidTimestamps); assertNull(s.summary().measuredFps) }
    @Test fun frameGapsAreReported() { val s = FrameStatistics(30); s.add(0); s.add(33_333); s.add(100_000); assertEquals(1, s.summary().largeGaps) }
}
