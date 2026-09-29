package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test

class ModePlanningTest {
    @Test fun eightKIsAnExplicitTargetEvenWhenNotAdvertised() {
        assertTrue(ModePlanning.eightK in ModePlanning.sizes(listOf(VideoSize(1280, 720))))
    }
    @Test fun retainsAllOrdinaryAdvertisedSizesWithoutDuplicates() {
        val special = VideoSize(4096, 2160)
        val sizes = ModePlanning.sizes(listOf(special, ModePlanning.eightK, special))
        assertTrue(special in sizes); assertEquals(1, sizes.count { it == ModePlanning.eightK })
    }
    @Test fun includesTwentyFourThirtyAndOrdinarySixtyButNotHighSpeed() {
        val rates = ModePlanning.rates(listOf(FpsRange(15, 15), FpsRange(120, 120)))
        assertTrue(rates.containsAll(listOf(24, 30, 25, 50, 60, 15))); assertFalse(120 in rates)
    }
    @Test fun hevcSdrIsIndependentFromHlg() {
        assertEquals(listOf("video/avc", "video/hevc"), ModePlanning.mimes(DynamicRange.SDR))
        assertEquals(listOf("video/hevc"), ModePlanning.mimes(DynamicRange.HLG10))
    }
    @Test fun fixedAePreferredOverVariableAe() {
        val plan = ModePlanning.timing(30, listOf(FpsRange(15, 30), FpsRange(30, 30)), true, 1_000_000_000, 1000)!!
        assertEquals(RateControl.AE_FIXED, plan.control); assertEquals(FpsRange(30, 30), plan.aeRange)
    }
    @Test fun variableAeRemainsExplicitlyVariable() {
        val plan = ModePlanning.timing(30, listOf(FpsRange(15, 30), FpsRange(10, 30)), false, null, null)!!
        assertEquals(RateControl.AE_VARIABLE, plan.control); assertEquals(15, plan.aeRange!!.lower)
    }
    @Test fun containingAeRangeIsNotTwentyFourFpsProof() {
        assertNull(ModePlanning.timing(24, listOf(FpsRange(15, 30)), false, null, null))
    }
    @Test fun manualSensorCanProvideIndependentTwentyFourFpsCandidate() {
        val plan = ModePlanning.timing(24, listOf(FpsRange(15, 30)), true, 100_000_000, 1000)!!
        assertTrue(plan.requiresManual); assertNull(plan.aeRange)
    }
    @Test fun manualNeedsKnownFrameDurationAndExposureLimits() {
        assertNull(ModePlanning.timing(24, emptyList(), true, null, 1000))
        assertNull(ModePlanning.timing(24, emptyList(), true, 100_000_000, null))
        assertNull(ModePlanning.timing(24, emptyList(), true, 30_000_000, 1000))
        assertNull(ModePlanning.timing(24, emptyList(), true, 100_000_000, 50_000_000))
    }
    @Test fun manualModeCannotStartWithUnappliedManualIntent() {
        val mode = mode(RatePlan(RateControl.MANUAL_SENSOR))
        assertFalse(ModePlanning.recordingAllowed(EngineState.PREVIEW, mode, false))
        assertTrue(ModePlanning.recordingAllowed(EngineState.PREVIEW, mode, true))
        EngineState.entries.filter { it != EngineState.PREVIEW }.forEach {
            assertFalse(ModePlanning.recordingAllowed(it, mode, true))
        }
        assertFalse(ModePlanning.recordingAllowed(EngineState.PREVIEW, null, true))
    }
    @Test fun modeIdentityAndExportIncludeTimingAndCodec() {
        val fixed = mode(RatePlan(RateControl.AE_FIXED, FpsRange(24, 24)))
        val manual = mode(RatePlan(RateControl.MANUAL_SENSOR))
        assertNotEquals(fixed.key, manual.key)
        assertTrue(fixed.label.contains("HEVC")); assertTrue(manual.label.contains("manual timing"))
        assertEquals("advertised_candidate", manual.describe()["evidence"])
        assertEquals(false, manual.describe()["customLog"])
    }
    @Test fun rejectionRetainsExactRequestedConfigurationAndReason() {
        val r = ModeRejection(ModePlanning.eightK, 24, DynamicRange.SDR, "video/hevc", "Not exposed").describe()
        assertEquals(7680, r["width"]); assertEquals(24, r["fps"]); assertEquals("Not exposed", r["reason"])
    }
    @Test fun startAcknowledgementRequiresActualMuxedPayload() {
        val gate = RecordingStartGate()
        assertFalse(gate.sampleWritten(0, false, 0)); assertFalse(gate.sampleWritten(50, true, 0))
        assertFalse(gate.sampleWritten(50, false, -1)); assertTrue(gate.sampleWritten(50, false, 0))
        assertFalse(gate.sampleWritten(50, false, 33333))
    }
    @Test fun stoppingBeforeFirstFramePreventsRecordingResurrection() {
        val gate = RecordingStartGate(); gate.stop(); assertFalse(gate.sampleWritten(100, false, 0))
    }
    @Test fun stoppedRecordingCannotAcknowledgeAgain() {
        val gate = RecordingStartGate(); assertTrue(gate.sampleWritten(100, false, 0)); gate.stop()
        assertFalse(gate.sampleWritten(100, false, 33333))
    }
    @Test fun cadenceDoesNotCertifyShortClip() {
        assertEquals("insufficient_duration", FrameSummary(10, 300000, 30.0, 0, 0).cadenceStatus(30))
    }
    @Test fun cadenceFlagsSlowOrGappedRecording() {
        assertEquals("warning", FrameSummary(300, 10_000_000, 28.83, 0, 0).cadenceStatus(30))
        assertEquals("warning", FrameSummary(300, 10_000_000, 30.0, 1, 0).cadenceStatus(30))
        assertEquals("within_tolerance", FrameSummary(301, 10_000_000, 30.0, 0, 0).cadenceStatus(30))
    }
    @Test fun badTimestampsCannotPassCadence() {
        assertEquals("invalid_timestamps", FrameSummary(300, 10_000_000, null, 0, 1).cadenceStatus(30))
    }
    private fun mode(rate: RatePlan) = RecordingMode(7680, 4320, 24, DynamicRange.SDR,
        "test.hevc", "video/hevc", 160_000_000, true, true, rate)
}
