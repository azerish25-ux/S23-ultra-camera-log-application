package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test

class AudioPolicyTest {
    @Test fun unavailableStoredModeNeverSilentlyMutes() {
        assertEquals(AudioMode.MONO, AudioMode.fromStored(null))
        assertEquals(AudioMode.MONO, AudioMode.fromStored("unknown"))
        assertEquals(AudioMode.OFF, AudioMode.fromStored("OFF"))
    }
    @Test fun timestampMapsEarlierBufferedAudioWithoutResettingIt() {
        val clock = PcmClock(48_000)
        clock.observe(4800, 2_100_000_000)
        assertEquals(2_000_000L, clock.timestampUs(0))
        assertEquals(2_100_000L, clock.timestampUs(4800))
        assertEquals(2_500_000L, clock.timestampUs(24000))
    }
    @Test fun timestampMathDoesNotAccumulateRoundingError() {
        val clock = PcmClock(48_000); clock.observe(0, 1_000_000_000)
        assertEquals(601_000_000L, clock.timestampUs(48_000L * 600))
        assertEquals(1_021_333L, clock.timestampUs(1024))
        assertEquals(1_042_666L, clock.timestampUs(2048))
    }
    @Test fun hoursOfAudioDoNotOverflowFrameArithmetic() {
        val clock = PcmClock(48_000); clock.observe(0, 1_000_000_000)
        assertEquals(86_401_000_000L, clock.timestampUs(48_000L * 86_400))
    }
    @Test fun hardwareDriftIsObservedWithoutAnAbruptReanchor() {
        val clock = PcmClock(48_000); clock.observe(0, 1_000_000_000)
        clock.observe(48_000, 2_005_000_000)
        assertEquals(5000L, clock.maxDriftUs)
        assertEquals(2_000_000L, clock.timestampUs(48_000))
    }
    @Test fun clockFallbackRemainsExplicitEvenIfTimestampsArriveLater() {
        val clock = PcmClock(48_000); clock.estimate(4800, 2_100_000_000)
        clock.observe(48_000, 3_050_000_000)
        assertEquals("read_completion_estimate_unverified", clock.source)
        assertEquals(2_000_000L, clock.timestampUs(0))
        assertEquals(false, clock.describe()["physicalLipSyncVerified"])
    }
    @Test fun repeatedAndRegressingClockObservationsAreNotGoodEvidence() {
        val clock = PcmClock(48_000); clock.observe(1000, 2_000_000_000)
        clock.observe(1000, 2_000_000_000); clock.observe(999, 1_999_999_000)
        assertEquals(1, clock.observations); assertEquals(1, clock.regressions)
    }
    @Test(expected = IllegalArgumentException::class) fun invalidClockRejected() { PcmClock(0) }
    @Test(expected = IllegalArgumentException::class) fun negativeFrameRejected() { PcmClock(48000).observe(-1, 1) }
    @Test(expected = IllegalArgumentException::class) fun zeroTimestampRejected() { PcmClock(48000).observe(1, 0) }
    @Test fun silenceIsFiniteAndNotClipping() {
        val level = PcmLevels.measure(ShortArray(64), 64, 1).single()
        assertEquals(-96.0, level.peakDb, 0.0); assertEquals(0, level.meter); assertFalse(level.clipped)
    }
    @Test fun stereoMeterSeparatesChannelsAndHandlesMinimumShort() {
        val levels = PcmLevels.measure(shortArrayOf(Short.MIN_VALUE, 0, Short.MAX_VALUE, 0), 4, 2)
        assertTrue(levels[0].clipped); assertEquals(100, levels[0].meter)
        assertEquals(0, levels[1].meter); assertFalse(levels[1].clipped)
    }
    @Test(expected = IllegalArgumentException::class) fun partialPcmFrameRejected() { PcmLevels.measure(shortArrayOf(1,2,3), 3, 2) }
    @Test fun realAacLcHeadersAreMatchedToTheSelection() {
        assertTrue(AacLcConfig.matches(byteArrayOf(0x11, 0x90.toByte()), 48000, 2))
        assertTrue(AacLcConfig.matches(byteArrayOf(0x11, 0x88.toByte()), 48000, 1))
        assertFalse(AacLcConfig.matches(byteArrayOf(0x11, 0x90.toByte()), 48000, 1))
        assertFalse(AacLcConfig.matches(byteArrayOf(0x12, 0x10), 48000, 2)) // 44.1 kHz
    }
    @Test fun aacOtherProfilesTruncatedAnd960FrameModesRejected() {
        assertFalse(AacLcConfig.matches(byteArrayOf(0x11), 48000, 2))
        assertFalse(AacLcConfig.matches(byteArrayOf(0x29, 0x90.toByte()), 48000, 2))
        assertFalse(AacLcConfig.matches(byteArrayOf(0x11, 0x94.toByte()), 48000, 2))
    }
}
