package com.s23log.probe

import com.s23log.probe.core.PreviewAnalyzer
import com.s23log.probe.core.PreviewLevel
import org.junit.Assert.*
import org.junit.Test

class PreviewAnalysisTest {
    @Test fun whiteHasExpectedHistogramAndZebras() {
        val result = PreviewAnalyzer.analyze(IntArray(12) { -1 }, 4, 3)
        assertEquals(12, result.validPixels); assertEquals(12, result.histogram[63])
        assertEquals(12, result.waveform.sum()); assertEquals(255.0, result.meanCode!!, 0.0)
        assertTrue(result.zebras.all { it != 0 }); assertTrue(result.peaking.all { it == 0 })
    }
    @Test fun transparentPaddingDoesNotBiasScopes() {
        val result = PreviewAnalyzer.analyze(intArrayOf(0, -1), 2, 1)
        assertEquals(1, result.validPixels); assertEquals(1, result.histogram.sum())
        assertEquals(0, result.falseColour[0]); assertEquals(0, result.zebras[0])
    }
    @Test fun unavailablePixelsStayUnknown() {
        val result = PreviewAnalyzer.analyze(IntArray(4), 2, 2)
        assertEquals(0, result.validPixels); assertNull(result.meanCode)
    }
    @Test fun zebraThresholdIsNotAnExposureCalibration() {
        val result = PreviewAnalyzer.analyze(intArrayOf(0xfff2f2f2.toInt(), 0xfff3f3f3.toInt()), 2, 1)
        assertEquals(0, result.zebras[0]); assertNotEquals(0, result.zebras[1])
    }
    @Test fun peakingFindsEdgesWithoutChangingSourcePixels() {
        val pixels = IntArray(15) { if (it % 5 < 2) 0xff000000.toInt() else -1 }
        val original = pixels.clone(); val result = PreviewAnalyzer.analyze(pixels, 5, 3)
        assertNotEquals(0, result.peaking[6]); assertArrayEquals(original, pixels)
    }
    @Test(expected = IllegalArgumentException::class) fun refusesFullResolutionAnalysis() {
        PreviewAnalyzer.analyze(IntArray(1), 3840, 2160)
    }
    @Test fun levelTransformsDisplayAxes() {
        assertEquals(0f, PreviewLevel.degrees(0f, 9.81f, 0f, 0)!!, 0.01f)
        assertEquals(0f, PreviewLevel.degrees(-9.81f, 0f, 0f, 1)!!, 0.01f)
        assertEquals(0f, PreviewLevel.degrees(0f, -9.81f, 0f, 2)!!, 0.01f)
        assertEquals(0f, PreviewLevel.degrees(9.81f, 0f, 0f, 3)!!, 0.01f)
    }
    @Test fun flatMissingOrMovingGravityCannotShowFalseZero() {
        assertNull(PreviewLevel.degrees(0f, 0f, 9.81f, 0))
        assertNull(PreviewLevel.degrees(Float.NaN, 9f, 0f, 0))
        assertNull(PreviewLevel.degrees(0f, 20f, 0f, 0))
        assertNull(PreviewLevel.degrees(0f, 9.81f, 0f, 4))
    }
}
