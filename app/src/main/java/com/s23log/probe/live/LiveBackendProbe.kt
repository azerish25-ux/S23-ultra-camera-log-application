package com.s23log.probe.live

import android.annotation.TargetApi
import android.media.MediaCodecInfo
import com.s23log.probe.core.*
import com.s23log.probe.develop.LogP010Codec
import com.s23log.probe.gpu.GlEnvironment
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import kotlin.math.abs
import kotlin.math.roundToInt

/** Standalone: no camera permission, RAW file, colour profile or grey chart needed. */
@TargetApi(33)
object LiveBackendProbe {
    data class Result(val selected:LiveLogEncoder.Route?,val report:JSONObject)
    fun run(cache:File,width:Int,height:Int,fps:Int,check:()->Unit={},progress:(String)->Unit={}):Result {
        require(width>0 && height>0 && width%2==0 && height%2==0 && fps in listOf(24,30))
        val routes=JSONArray();val decoders=JSONArray();var selected:LiveLogEncoder.Route?=null
        val report=JSONObject().put("schemaVersion",1).put("kind","live-log-backend-probe")
            .put("width",width).put("height",height).put("fps",fps).put("routes",routes).put("decoders",decoders)
            .put("sensorPrecisionMeasured",false).put("syntheticInputs",true).put("hlgTransferRequested",false)
        try {
            for(info in LiveLogEncoder.inventory(false)) {
                val entry=JSONObject().put("name",info.name)
                try {entry.put("p010Advertised",MediaCodecInfo.CodecCapabilities.COLOR_FormatYUVP010 in info.getCapabilitiesForType("video/hevc").colorFormats)}
                catch(e:Exception){entry.put("queryError",e.message)}
                decoders.put(entry)
            }
            for(info in LiveLogEncoder.inventory(true).take(8)) for(input in LiveLogEncoder.Input.entries) {
                check();val route=LiveLogEncoder.Route(info.name,input);val entry=JSONObject().put("codec",info.name).put("input",input.name)
                routes.put(entry)
                try {LiveLogEncoder.format(route,width,height,fps);LiveLogEncoder.format(route,1024,128,fps)}
                catch(e:Exception){entry.put("status","not_advertised_for_configuration").put("reason",e.message);continue}
                entry.put("advertised",true)
                if(selected!=null){entry.put("status","not_tested_after_qualified_route");continue}
                progress("Testing ${route.label}; source and capture settings are not involved")
                try {
                    val positive=test(cache,route,1024,128,fps,4,false,check)
                    entry.put("positive",positive);require(positive.getBoolean("passed")){"Positive ten-bit ramp failed"}
                    val negative=test(cache,route,1024,128,fps,4,true,check)
                    entry.put("eightBitNegative",negative);require(!negative.getBoolean("passed")){"Degraded eight-bit control incorrectly passed"}
                    val sizeTest=test(cache,route,width,height,fps,2,false,check)
                    entry.put("selectedSize",sizeTest);require(sizeTest.getBoolean("passed")){"Selected output dimensions failed precision/colour verification"}
                    selected=route;entry.put("status","qualified")
                } catch(e:Exception){check();entry.put("status","rejected").put("reason",e.message ?: e.javaClass.simpleName)}
            }
            report.put("status",if(selected!=null)"qualified" else "unavailable")
                .put("selectedCodec",selected?.codec ?: JSONObject.NULL).put("selectedInput",selected?.input?.name ?: JSONObject.NULL)
        } catch(e:Exception){check();report.put("status","query_failed").put("error",e.message)}
        return Result(selected,report)
    }
    private fun test(cache:File,route:LiveLogEncoder.Route,w:Int,h:Int,fps:Int,count:Int,degraded:Boolean,check:()->Unit):JSONObject {
        val file=File(cache,"live-precision-${UUID.randomUUID()}.mp4")
        try {
            GlEnvironment.create(rgb10=route.input==LiveLogEncoder.Input.RGB10_SURFACE).use { env ->
                RawLogGpu(env,w,h,w,h).use { gpu ->
                    LiveLogEncoder(file,route,w,h,fps).use { encoder ->
                        for(frame in 0 until count){check();gpu.fixture(fixture(w,h,frame,degraded));encoder.submit(gpu,frame*1_000_000L/fps,check)}
                        encoder.finish()
                    }
                }
            }
            var mean=0.0;var peak=0.0;var levels=1024;var colourPeak=0
            val decoded=LogP010Codec.verify(file,w,h,fps,count,check) { frame,p ->
                val n=minOf(877,w);val from=minOf(16,h/8);val until=maxOf(from+1,h*3/4-8)
                val values=DoubleArray(n){x -> (from until until).sumOf {y -> p.y.get(x,y).toDouble()}/(until-from)}
                val expected=DoubleArray(n){x -> (64+(x+frame)%877).toDouble()}
                // Small outputs cannot demonstrate 600 levels. They are not offered by the live UI.
                require(n>=600){"Precision proof requires at least 600 output columns"}
                val result=LivePrecision.assess(values,expected)
                mean=maxOf(mean,result.mean);peak=maxOf(peak,result.peak);levels=minOf(levels,result.levels)
                for(patchIndex in 0..3) {
                    val x=((patchIndex+.5)*w/4).toInt().coerceIn(0,w-1) and -2
                    val y=(h*7/8).coerceAtMost(h-2) and -2
                    val rgb=patch(patchIndex)
                    val yExpected=RawDevelopMath.lumaCode(RawDevelopMath.y(rgb[0],rgb[1],rgb[2]))
                    val uExpected=RawDevelopMath.chromaCode(RawDevelopMath.cb(rgb[0],rgb[1],rgb[2]))
                    val vExpected=RawDevelopMath.chromaCode(RawDevelopMath.cr(rgb[0],rgb[1],rgb[2]))
                    colourPeak=maxOf(colourPeak,abs(p.y.get(x,y)-yExpected),abs(p.u.get(x/2,y/2)-uExpected),abs(p.v.get(x/2,y/2)-vExpected))
                }
            }
            return decoded.put("meanCodeError",mean).put("maximumCodeError",peak).put("distinctRampLevels",levels)
                .put("colourPatchPeakCodeError",colourPeak).put("passed",mean<=.75 && peak<=2.0 && levels>=600 && colourPeak<=12)
                .put("deliberatelyDegraded",degraded)
        } finally {file.delete()}
    }
    fun patch(index:Int)=when(index){0->doubleArrayOf(.8,.15,.15);1->doubleArrayOf(.15,.8,.15);2->doubleArrayOf(.15,.15,.8);else->doubleArrayOf(.5,.5,.5)}
    fun fixture(w:Int,h:Int,frame:Int,degraded:Boolean):FloatArray {
        val a=FloatArray(w*h*4)
        val colours=Array(4){patch(it)}
        for(y in 0 until h)for(x in 0 until w) {
            var code=64+(x+frame)%877;if(degraded)code=((code/4.0).roundToInt()*4).coerceIn(64,940)
            val i=(y*w+x)*4
            if(y<h*3/4){val v=((code-64)/876.0).toFloat();a[i]=v;a[i+1]=v;a[i+2]=v}
            else{val rgb=colours[minOf(3,x*4/w)];for(c in 0..2)a[i+c]=rgb[c].toFloat()}
            a[i+3]=1f
        }
        return a
    }
}

/** Same GPU kernel used by live capture, compared against the existing CPU developer. */
object RawLogGpuProbe {
    fun run(check:()->Unit={}):JSONObject {
        val w=64;val h=48
        val raw=ByteBuffer.allocateDirect(w*h*2).order(ByteOrder.LITTLE_ENDIAN)
        for(i in 0 until w*h)raw.putShort(((i*31+i/w*7)%4096).toShort());raw.flip()
        val source=object:RawRowSource {
            override val width=w;override val height=h
            override fun readRow(y:Int,into:ShortArray){for(x in 0 until w)into[x]=raw.getShort((y*w+x)*2)}
        }
        var peak=0.0;var codePeak=0;var cases=0
        GlEnvironment.create().use {env ->
            for(cfa in 0..3)for(d in listOf(1,2,4)) {
                check()
                val p=RawDevelopParameters(cfa,intArrayOf(8,8,48,32),doubleArrayOf(64.0,65.0,66.0,67.0),4095.0,
                    doubleArrayOf(1.05,1.0,.98,1.1),RawDevelopMath.inverse(RawDevelopMath.XYZ_TO_AWG3),2.0,d)
                val expected=Array(p.height){DoubleArray(p.width*3)}
                RawFrameDeveloper().develop(source,p,true,check,object:LogRowSink {
                    override fun pair(y:Int,first:DoubleArray,second:DoubleArray){expected[y]=first.copyOf();expected[y+1]=second.copyOf()}
                })
                RawLogGpu(env,w,h,p.width,p.height).use {gpu ->
                    gpu.render(raw.duplicate().order(ByteOrder.LITTLE_ENDIAN),p,true)
                    val pixels=gpu.referencePixels();val packed=LiveP010.rows(gpu.p010(),p.width,p.height)
                    val expectedBuffer=ByteBuffer.allocate(p.width*p.height*3).order(ByteOrder.LITTLE_ENDIAN)
                    val rows=LiveP010.rows(expectedBuffer,p.width,p.height)
                    for(y in 0 until p.height step 2)rows.pair(y,expected[y],expected[y+1])
                    for(y in 0 until p.height)for(x in 0 until p.width) {
                        for(c in 0..2)peak=maxOf(peak,abs(pixels[(y*p.width+x)*4+c].toDouble().coerceIn(0.0,1.0)-expected[y][x*3+c]))
                        codePeak=maxOf(codePeak,abs(rows.y.get(x,y)-packed.y.get(x,y)))
                    }
                    for(y in 0 until p.height/2)for(x in 0 until p.width/2)codePeak=maxOf(codePeak,abs(rows.u.get(x,y)-packed.u.get(x,y)),abs(rows.v.get(x,y)-packed.v.get(x,y)))
                    require(peak<=.001 && codePeak<=2){"GPU/CPU RAW disagreement: RGB=$peak, P010=$codePeak"}
                    cases++
                }
            }
        }
        return JSONObject().put("status","passed").put("synthetic",true).put("bayerReductionCases",cases)
            .put("maximumLogRgbError",peak).put("maximumP010CodeError",codePeak).put("sensorPrecisionMeasured",false)
    }
}
