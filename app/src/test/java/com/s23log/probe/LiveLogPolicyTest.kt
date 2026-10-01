package com.s23log.probe

import com.s23log.probe.core.*
import org.junit.Assert.*
import org.junit.Test
import java.nio.ByteBuffer

class LiveLogPolicyTest {
    @Test fun sensorIntervalsAreNotReplacedByCfr() {
        val c=LiveLogClock(30);assertEquals(0L,c.submit(8_000_000_000));assertEquals(33_334L,c.submit(8_033_334_123));assertEquals(100_004L,c.submit(8_100_004_456))
        assertEquals(listOf(0L,33334L,100004L),c.presentationTimes());assertEquals(1,c.largeGaps);assertFalse(c.withinTolerance)
    }
    @Test fun fullTwoSecondsHasMeasuredCadence() {val c=LiveLogClock(24);for(i in 0..48)c.submit(3_000_000_000L+i*1_000_000_000L/24);assertTrue(c.withinTolerance);assertEquals(24.0,c.measuredFps!!,1e-6)}
    @Test fun shortTakeDoesNotQualifyCadence() {val c=LiveLogClock(30);c.submit(1);c.submit(33333334);assertFalse(c.withinTolerance)}
    @Test(expected=IllegalArgumentException::class) fun duplicateSensorTimestampFails(){val c=LiveLogClock(30);c.submit(9);c.submit(9)}
    @Test(expected=IllegalArgumentException::class) fun collapsedMicrosecondsFail(){val c=LiveLogClock(30);c.submit(1000);c.submit(1001)}
    @Test(expected=IllegalArgumentException::class) fun boundedIndexStops(){val c=LiveLogClock(30,2);c.submit(1);c.submit(33333334);c.submit(66666667)}
    @Test fun outputCropIsExplicitAndDoesNotUpscale(){
        val choices=LiveLogOutput.choices(intArrayOf(0,0,4000,3000));val first=choices.first()
        assertEquals(1920,first.width);assertEquals(1080,first.height);assertEquals(3840,first.cropWidth);assertEquals(2160,first.cropHeight);assertEquals(80,first.left);assertEquals(420,first.top)
        assertTrue(choices.any{it.width==1000 && it.height==750});assertTrue(choices.all{it.left+it.cropWidth<=4000 && it.top+it.cropHeight<=3000})
    }
    @Test fun opticalBlackCropOffsetPreserved(){val c=LiveLogOutput.choices(intArrayOf(12,8,4000,3000)).first();assertEquals(92,c.left);assertEquals(428,c.top)}
    @Test(expected=IllegalArgumentException::class) fun oversizedInputRejected(){LiveLogOutput.memoryBytes(8000,6000,LiveLogOutput(0,0,3840,2160,2))}
    @Test(expected=IllegalArgumentException::class) fun biggerOutputIsNotEnabledByDroppingChecks(){LiveLogOutput(0,0,3840,2160,1)}
    @Test fun sourceMemoryIsIndependentOfOutputDimensions(){val o=LiveLogOutput(0,0,1920,1080,1);assertTrue(LiveLogOutput.memoryBytes(4000,3000,o)>LiveLogOutput.memoryBytes(1920,1080,o))}
    @Test fun precisionCheckerRejectsEightBitControl(){val original=DoubleArray(877){64.0+it};assertTrue(LivePrecision.assess(original,original).passed);assertFalse(LivePrecision.assess(original.map{kotlin.math.round(it/4)*4}.toDoubleArray(),original).passed)}
    @Test fun p010TightPackingAndPaddingCopiesAreExact(){
        val source=LiveP010.rows(ByteBuffer.allocate(8*4*3),8,4)
        for(y in 0 until 4)for(x in 0 until 8)source.y.put(x,y,64+x+y*8)
        for(y in 0 until 2)for(x in 0 until 4){source.u.put(x,y,100+x);source.v.put(x,y,700+y)}
        val target=P010Rows(TenBitPlane(ByteBuffer.allocate(4*24),8,4,24,2),TenBitPlane(ByteBuffer.allocate(2*24),4,2,24,4),TenBitPlane(ByteBuffer.allocate(2*24),4,2,24,4))
        LiveP010.copy(source,target)
        for(y in 0 until 4)for(x in 0 until 8)assertEquals(source.y.get(x,y),target.y.get(x,y))
        for(y in 0 until 2)for(x in 0 until 4){assertEquals(source.u.get(x,y),target.u.get(x,y));assertEquals(source.v.get(x,y),target.v.get(x,y))}
    }
    @Test(expected=IllegalArgumentException::class) fun truncatedPackingRejected(){LiveP010.rows(ByteBuffer.allocate(4),1920,1080)}
}
