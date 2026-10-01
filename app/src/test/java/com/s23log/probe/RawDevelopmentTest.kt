package com.s23log.probe

import com.s23log.probe.core.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class RawDevelopmentTest {
    private val identity=RawDevelopMath.IDENTITY
    private val toXyz=RawDevelopMath.inverse(RawDevelopMath.XYZ_TO_AWG3)
    private fun rejects(action:()->Unit) { try { action();fail("Expected rejection") } catch(e:IllegalArgumentException) { } catch(e:IllegalStateException) { } }
    private fun header()=JSONObject().put("schemaVersion",1).put("kind","continuous-raw").put("source","RAW_SENSOR")
        .put("sampleEncoding","uint16le").put("rowBytes",16).put("width",8).put("height",8).put("cfa",0).put("fpsRequested",24)
        .put("device",JSONObject().put("fingerprint","test-firmware").put("model","SYNTHETIC_FIXTURE"))
        .put("logicalCamera","0").put("physicalCamera",JSONObject.NULL)
    private fun meta(i:Int)=JSONObject().put("sensorTimestampNs",1_000_000_000L+i*1_000_000_000L/24).put("iso",100).put("exposureNs",10_000_000)
        .put("blackLevels",JSONArray(listOf(64,64,64,64))).put("whiteLevel",4095).put("neutralColorPoint",JSONArray(listOf(1,1,1)))
    private fun source():RawSourceIndex {
        val f=File.createTempFile("raw-development-",".s23raw");f.deleteOnExit()
        f.outputStream().use { stream -> RawSequenceFormat.header(stream,header().toString().toByteArray())
            repeat(4) { i -> val pixels=ByteBuffer.allocate(128).order(ByteOrder.LITTLE_ENDIAN);repeat(64){pixels.putShort(790)}
                RawSequenceFormat.frame(stream,meta(i).toString().toByteArray(),pixels.array()) } }
        return RawSourceReader.scan(f)
    }
    private fun profile(index:RawSourceIndex)=JSONObject().put("schemaVersion",1).put("kind","raw-colour-profile").put("source",index.binding())
        .put("calibration",JSONObject().put("status","synthetic").put("evidence","test fixture").put("illuminant","synthetic"))
        .put("cameraToXyzD65",RawJson.matrixJson(toXyz)).put("bayerWhiteBalance",JSONArray(listOf(1,1,1,1)))
        .put("sceneScale",1).put("crop",JSONArray(listOf(0,0,8,8))).put("iso",100).put("exposureNs",10_000_000)
    @Test fun publishedLogValuesAndSignedToe() {
        assertEquals(.092809,RawDevelopMath.logC3(0.0),1e-12)
        assertEquals(.391006832,RawDevelopMath.logC3(.18),1e-8)
        assertEquals(.570631558,RawDevelopMath.logC3(1.0),1e-8)
        assertEquals(.092809-5.367655*.01,RawDevelopMath.logC3(-.01),1e-12)
        assertTrue(RawDevelopMath.logC3(4.0)>RawDevelopMath.logC3(1.0))
    }
    @Test fun inverseOverExposureRange(){for(i in -100..10000){val x=i/200.0;assertEquals(x,RawDevelopMath.inverseLogC3(RawDevelopMath.logC3(x)),1e-5)}}
    @Test fun nonfiniteAndSingularMatricesRejected(){rejects{RawDevelopMath.logC3(Double.NaN)};rejects{RawDevelopMath.inverse(DoubleArray(9))}}
    @Test fun bradfordMapsD50WhiteToD65(){val w=RawDevelopMath.apply(RawDevelopMath.D50_TO_D65,doubleArrayOf(.964295676,1.0,.825104603));assertArrayEquals(doubleArrayOf(.950455927,1.0,1.089057751),w,2e-6)}
    @Test fun metadataUsesInverseActualCalibrationNotDirectMatrix(){
        val f=doubleArrayOf(.4360747,.3850649,.1430804,.2225045,.7168786,.0606169,.0139322,.0971045,.7141733)
        val cc=doubleArrayOf(1.05,.02,0.0,.01,1.0,.01,0.0,.02,.92)
        val (matrix,wb)=RawDevelopMath.metadataMatrix(f,cc,doubleArrayOf(.7,1.0,.6))
        assertArrayEquals(doubleArrayOf(1/.7,1.0,1/.6),wb,1e-9)
        val white=RawDevelopMath.apply(matrix,doubleArrayOf(1.0,1.0,1.0));assertEquals(1.0,white[1],.001)
        assertEquals(.95045,white[0]/white[1],.001);assertEquals(1.08906,white[2]/white[1],.001)
    }
    @Test fun everyBayerArrangementPreservesKnownSamplesAndEdges(){
        for(cfa in 0..3){
            val colours=doubleArrayOf(.1,.25,.6)
            val src=object:RawRowSource{override val width=8;override val height=8
                override fun readRow(y:Int,into:ShortArray){for(x in 0 until width)into[x]=(colours["RGB".indexOf(RawDevelopMath.BAYER[cfa][(y%2)*2+x%2])]*10000).toInt().toShort()}}
            val p=RawDevelopParameters(cfa,intArrayOf(0,0,8,8),DoubleArray(4),10000.0,DoubleArray(4){1.0},toXyz,1.0)
            var rows=0
            RawFrameDeveloper().develop(src,p,sink=object:LogRowSink{override fun pair(y:Int,first:DoubleArray,second:DoubleArray){
                for(row in listOf(first,second))for(i in row.indices)assertEquals(RawDevelopMath.logC3(colours[i%3]),row[i],2e-7);rows+=2}})
            assertEquals(8,rows)
        }
    }
    @Test fun boxReductionIsBeforeLog(){
        val index=source();val p=RawColourProfile.parse(profile(index),index,false);var rows=0
        index.rows(index.frames.first()).use { input -> RawFrameDeveloper().develop(input,p.parameters(index,index.frames.first(),2),sink=object:LogRowSink{
            override fun pair(y:Int,first:DoubleArray,second:DoubleArray){assertEquals(12,first.size);assertEquals(RawDevelopMath.logC3(726.0/4031),first[0],1e-7);rows+=2}}) }
        assertEquals(4,rows)
    }
    @Test fun negativeSourceSamplesAreNotClampedBeforeLog(){
        val input=object:RawRowSource{override val width=4;override val height=4;override fun readRow(y:Int,into:ShortArray){into.fill(0)}}
        val p=RawDevelopParameters(0,intArrayOf(0,0,4,4),DoubleArray(4){10.0},1010.0,DoubleArray(4){1.0},toXyz,1.0)
        RawFrameDeveloper().develop(input,p,sink=object:LogRowSink{override fun pair(y:Int,first:DoubleArray,second:DoubleArray){assertEquals(RawDevelopMath.logC3(-.01),first[0],1e-7)}})
    }
    @Test fun outputClippingRequiresExplicitConsent(){
        val index=source();val json=profile(index).put("sceneScale",1e5);val p=RawColourProfile.parse(json,index,false)
        index.rows(index.frames.first()).use { src ->rejects{RawFrameDeveloper().develop(src,p.parameters(index,index.frames.first()),sink=object:LogRowSink{override fun pair(y:Int,first:DoubleArray,second:DoubleArray)=Unit})} }
    }
    @Test fun p010PlaneRespectsStrideSliceAndTopTenBits(){
        val data=ByteBuffer.allocate(256).order(ByteOrder.LITTLE_ENDIAN);data.position(10)
        val plane=TenBitPlane(data,5,4,24,4);plane.put(4,3,777);assertEquals(777,plane.get(4,3));assertEquals(777 shl 6,data.getShort(10+3*24+4*4).toInt() and 65535)
        assertEquals(0,data.getShort(0).toInt());rejects{TenBitPlane(ByteBuffer.allocate(10),5,4,24,4)}
    }
    @Test fun p010GreyUsesLimitedRangeAndNeutralChroma(){
        val yy=TenBitPlane(ByteBuffer.allocate(32),4,4,8,2);val u=TenBitPlane(ByteBuffer.allocate(8),2,2,4,2);val v=TenBitPlane(ByteBuffer.allocate(8),2,2,4,2)
        P010Rows(yy,u,v).pair(0,DoubleArray(12){.5},DoubleArray(12){.5});assertEquals(502,yy.get(0,0));assertEquals(512,u.get(0,0));assertEquals(512,v.get(0,0))
    }
    @Test fun scansChecksumsAndCadenceWithoutChangingSource(){val s=source();val hash=RawJson.hash(s.file);assertEquals(4,s.frames.size);assertEquals(24,s.timing().getInt("outputFps"));assertEquals(hash,RawJson.hash(s.file))}
    @Test fun checksumCorruptionIsNotTailRecovery(){val s=source();java.io.RandomAccessFile(s.file,"rw").use{it.seek(s.frames[0].offset);it.write(0)};rejects{RawSourceReader.scan(s.file)}}
    @Test fun truncatedSourceIsRetained(){val s=source();java.io.RandomAccessFile(s.file,"rw").use{it.setLength(it.length()-2)};val n=s.file.length();rejects{RawSourceReader.scan(s.file)};assertEquals(n,s.file.length())}
    @Test fun cadenceGapRefusesImplicitRetime(){val s=source();s.frames[2].metadata.put("sensorTimestampNs",2_000_000_000L);rejects{s.timing()}}
    @Test fun profileBindingAndExposureAreEnforced(){val s=source();val j=profile(s);j.getJSONObject("source").put("fingerprint","wrong");rejects{RawColourProfile.parse(j,s,false)}
        val p=profile(s).put("iso",800);rejects{RawColourProfile.parse(p,s,false)}}
    @Test fun syntheticProfileCannotCalibrateRealPhone(){val s=source();s.header.getJSONObject("device").put("model","SM-S918B");rejects{RawColourProfile.parse(profile(s),s,true)}}
    @Test fun provisionalProfileNeedsConsent(){val s=source();val p=profile(s);p.getJSONObject("calibration").put("status","provisional");rejects{RawColourProfile.parse(p,s,false)};assertEquals("provisional",RawColourProfile.parse(p,s,true).status)}
    @Test fun legacySourceNeedsImportedProfileNotInventedMetadata(){val s=source();rejects{RawColourProfile.fromMetadata(s,1,intArrayOf(0,0,8,8),"test")};assertNotNull(RawColourProfile.parse(profile(s),s,false))}
    @Test fun metadataProfileUsesUserGreyButRemainsProvisional(){
        val s=source();val fm=doubleArrayOf(.4360747,.3850649,.1430804,.2225045,.7168786,.0606169,.0139322,.0971045,.7141733)
        s.header.put("rawCalibration",JSONObject().put("forwardMatrix1",RawJson.matrixJson(fm)).put("calibrationTransform1",RawJson.matrixJson(identity)).put("referenceIlluminant1",21))
        val j=RawColourProfile.fromMetadata(s,1,intArrayOf(0,0,8,8),RawJson.hash(s.file));assertEquals("provisional",j.getJSONObject("calibration").getString("status"))
        val p=RawColourProfile.parse(j,s,true);assertTrue(p.scale>0);assertFalse(j.getJSONObject("calibration").getBoolean("independentlyMeasuredColour"))
    }
    @Test fun hevcReauthoringPreservesTenBitAndRejectsEight(){
        fun fixture(bits:Int)=javaClass.classLoader!!.getResourceAsStream("hevc$bits.annexb.hex")!!.bufferedReader().use{it.readText()}.filterNot(Char::isWhitespace).chunked(2).map{it.toInt(16).toByte()}.toByteArray()
        val input=fixture(10);val output=LogHevc.rewrite(input);assertTrue(LogHevc.signal(output).isLogContract)
        assertEquals(HevcSps.bitDepth(input),HevcSps.bitDepth(output));assertArrayEquals(output,LogHevc.rewrite(output));rejects{LogHevc.rewrite(fixture(8))}
    }
    @Test fun malformedHevcFailsClosed(){rejects{LogHevc.rewrite(byteArrayOf(0,0,1,0x42,1,0))}}
    @Test fun cancellationIsCheckedInsideRows(){val s=source();val p=RawColourProfile.parse(profile(s),s,false);var checks=0
        try{s.rows(s.frames[0]).use{src->RawFrameDeveloper().develop(src,p.parameters(s,s.frames[0]),check={if(++checks==3)throw java.util.concurrent.CancellationException()},sink=object:LogRowSink{override fun pair(y:Int,first:DoubleArray,second:DoubleArray)=Unit})};fail("Expected cancel")}catch(_:java.util.concurrent.CancellationException){}
        assertEquals(3,checks)
    }
    @Test fun matchesFrozenOfflineReferenceForAllMosaicsAndLinearReduction(){
        val vectors=JSONArray(javaClass.classLoader!!.getResourceAsStream("raw-development-vectors.json")!!.bufferedReader().use{it.readText()})
        for(n in 0 until vectors.length()){
            val v=vectors.getJSONObject(n);val values=v.getJSONArray("raw");val expected=v.getJSONArray("expected")
            val src=object:RawRowSource{override val width=12;override val height=8
                override fun readRow(y:Int,into:ShortArray){for(x in 0 until width)into[x]=values.getInt(y*width+x).toShort()}}
            val p=RawDevelopParameters(v.getInt("cfa"),intArrayOf(0,0,12,8),RawJson.array(v,"black",4),v.getDouble("white"),
                RawJson.array(v,"wb",4),RawJson.matrix(v,"matrix"),1.0,v.getInt("divisor"))
            RawFrameDeveloper().develop(src,p,true,sink=object:LogRowSink{override fun pair(y:Int,first:DoubleArray,second:DoubleArray){
                for((r,row) in listOf(first,second).withIndex())for(i in row.indices)assertEquals("case $n",expected.getDouble((y+r)*row.size+i),row[i],2e-6)
            }})
        }
    }

}
