package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test
import kotlin.math.round

class ColourPipelineTest {
    private fun mode() = RecordingMode(1920,1080,30,DynamicRange.HLG10,"test.encoder","video/hevc",10_000_000,false,true)
    @Test fun directModeIdentityStaysCompatible() {
        val old=mode(); assertEquals("1920:1080:30:HLG10:test.encoder:video/hevc:AE_FIXED",old.key)
        val gpu=old.copy(processing=ProcessingPath.GPU_HLG10,previewDuringRecording=true)
        assertNotEquals(old.key,gpu.key);assertEquals(old.colour.inputProfile,gpu.colour.inputProfile)
        assertEquals("HLG",gpu.colour.recordingTransfer);assertFalse(gpu.colour.describe()["customLog"] as Boolean)
    }
    @Test fun processingDoesNotExpandDirectCapabilityOrCertifyEightK() {
        assertNull(ProcessingPolicy.rejection(33,mode(),true,true,false))
        assertNull(ProcessingPolicy.rejection(35,mode(),true,false,true))
        assertNotNull(ProcessingPolicy.rejection(34,mode(),true,false,true))
        assertNotNull(ProcessingPolicy.rejection(33,mode(),true,false,false))
        assertNotNull(ProcessingPolicy.rejection(33,mode(),false,true,false))
        assertNotNull(ProcessingPolicy.rejection(32,mode(),true,true,true))
        assertNotNull(ProcessingPolicy.rejection(36,mode().copy(width=7680,height=4320),true,true,true))
        assertNotNull(ProcessingPolicy.rejection(36,mode().copy(fps=60),true,true,true))
    }
    @Test(expected=IllegalArgumentException::class) fun gpuCannotRelabelSdr() {
        mode().copy(range=DynamicRange.SDR,processing=ProcessingPath.GPU_HLG10,previewDuringRecording=true)
    }
    @Test fun hlgReferenceBreakpointsAndInverse() {
        assertEquals(0.0,ColourMath.hlgDecode(0.0),0.0)
        assertEquals(1.0/12,ColourMath.hlgDecode(0.5),1e-12)
        assertEquals(1.0,ColourMath.hlgDecode(1.0),1e-6)
        for(i in -1000..2000) { val x=i/2000.0; assertEquals(x,ColourMath.hlgEncode(ColourMath.hlgDecode(x)),1e-7) }
    }
    @Test fun limitedYuvOffsetsAndColourMatrix() {
        val black=ColourMath.limitedYuv10ToHlg(64.0/1023,512.0/1023,512.0/1023)
        black.forEach { assertEquals(0.0,it,1e-12) }
        ColourMath.limitedYuv10ToHlg(940.0/1023,512.0/1023,512.0/1023).forEach { assertEquals(1.0,it,1e-12) }
        for(rgb in listOf(doubleArrayOf(1.0,0.0,0.0),doubleArrayOf(0.0,1.0,0.0),doubleArrayOf(0.0,0.0,1.0),doubleArrayOf(.18,.5,.9))) {
            val yuv=ColourMath.hlgToLimitedYuv10(rgb[0],rgb[1],rgb[2])
            assertArrayEquals(rgb,ColourMath.limitedYuv10ToHlg(yuv[0],yuv[1],yuv[2]),1e-9)
        }
    }
    @Test fun fullRangeIsNotMistakenForLimited() {
        ColourMath.limitedYuv10ToHlg(0.0,512.0/1023,512.0/1023,true).forEach { assertEquals(0.0,it,1e-12) }
        ColourMath.limitedYuv10ToHlg(1.0,512.0/1023,512.0/1023,true).forEach { assertEquals(1.0,it,1e-12) }
        assertTrue(ColourMath.limitedYuv10ToHlg(0.0,512.0/1023,512.0/1023)[0]<0)
    }
    @Test fun referenceLogIsMonotonicReversibleAndBounded() {
        assertEquals(0.0,ColourMath.referenceLogEncode(0.0),0.0);assertEquals(1.0,ColourMath.referenceLogEncode(1.0),1e-12)
        var previous=-1.0
        for(i in 0..10000) { val x=i/10000.0;val y=ColourMath.referenceLogEncode(x)
            assertTrue(y>previous);assertEquals(x,ColourMath.referenceLogDecode(y),1e-12);previous=y }
    }
    @Test(expected=IllegalArgumentException::class) fun customLogRejectsInvalidDomain() { ColourMath.referenceLogEncode(-0.1) }
    @Test(expected=IllegalArgumentException::class) fun transferRejectsNan() { ColourMath.hlgDecode(Double.NaN) }
    @Test fun precisionCheckerRejectsEightBitUpscaling() {
        assertTrue(ColourPrecision.assessRamp(DoubleArray(1024){it/1023.0}).passed)
        assertFalse(ColourPrecision.assessRamp(DoubleArray(1024){round(it/1023.0*255)/255}).passed)
        assertFalse(ColourPrecision.assessRamp(DoubleArray(1024){0.5}).passed)
    }
    @Test fun processingPreservesClockAndExposesGaps() {
        val c=ProcessingFrameClock(30);assertTrue(c.accept(10_000_000_000,10_010_000_000))
        assertTrue(c.accept(10_100_000_000,10_110_000_000));assertEquals(1L,c.largeIntervals)
        assertEquals(false,c.describe()["presentationTimestampsRewritten"]);assertEquals(10_000_000_000,c.describe()["firstNs"])
        c.stop();assertFalse(c.accept(10_200_000_000,10_210_000_000))
    }
    @Test(expected=IllegalArgumentException::class) fun rejectsUnknownTimestampEpoch() { ProcessingFrameClock(30).accept(1,10_000_000_000) }
    @Test(expected=IllegalArgumentException::class) fun rejectsRepeatedFramesInsteadOfMakingNewTimes() {
        val c=ProcessingFrameClock(24);c.accept(10_000_000_000,10_000_000_000);c.accept(10_000_000_000,10_010_000_000)
    }
}
