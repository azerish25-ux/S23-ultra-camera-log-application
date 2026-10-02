package com.s23log.probe

import android.content.Intent
import android.graphics.Bitmap
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.live.LiveBackendProbe
import com.s23log.probe.live.RawLogGpuProbe
import com.s23log.probe.live.RawLogGpu
import com.s23log.probe.gpu.GlEnvironment
import com.s23log.probe.core.LiveP010
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import com.s23log.probe.diagnostics.ModeEvidence
import com.s23log.probe.diagnostics.jsonValue
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class LiveLogAndroidTest {
    private val instrumentation=InstrumentationRegistry.getInstrumentation()
    private val context=instrumentation.targetContext
    private fun save(name:String,report:JSONObject){
        val file=File(context.filesDir,"exports/live-log/$name");file.parentFile!!.mkdirs()
        report.put("appCommit",BuildConfig.SOURCE_REVISION).put("device",jsonValue(ModeEvidence.device()))
        file.writeText(report.toString(2))
    }
    @Test fun actualGpuMatchesCpuAcrossBayerCropsAndReductions(){
        val report=RawLogGpuProbe.run();assertEquals("passed",report.getString("status"));assertEquals(12,report.getInt("bayerReductionCases"));save("gpu-test.json",report)
    }
    @Test fun packedP010PreservesRampsChromaPaddingAndRepeatedReadback(){
        var peak=0;var cases=0;var rampLevels=0
        GlEnvironment.create().use { env ->
            for((w,h) in listOf(1024 to 4,12 to 8,2 to 2)) {
                RawLogGpu(env,w,h,w,h).use { gpu ->
                    for(frame in 0..2) {
                        val values=FloatArray(w*h*4)
                        for(y in 0 until h)for(x in 0 until w) {
                            val at=(y*w+x)*4
                            for(c in 0..2)values[at+c]=if(y<2) ((x+frame*73)%877)/876f
                                else ((x*(c*6+1)+y*(17-c*7)+frame*73)%877)/876f
                            values[at+3]=1f
                        }
                        gpu.fixture(values)
                        // Compare the actual FP16 source with independent CPU YUV math.
                        // Reading floats first also exercises framebuffer-state changes.
                        val pixels=gpu.referencePixels()
                        val expected=LiveP010.rows(ByteBuffer.allocate(w*h*3).order(ByteOrder.LITTLE_ENDIAN),w,h)
                        for(y in 0 until h step 2)expected.pair(y,
                            DoubleArray(w*3){j->pixels[(y*w+j/3)*4+j%3].toDouble()},
                            DoubleArray(w*3){j->pixels[((y+1)*w+j/3)*4+j%3].toDouble()})
                        repeat(2) {
                            val bytes=gpu.p010()
                            assertEquals(w*h*3,bytes.remaining())
                            assertEquals(ByteOrder.LITTLE_ENDIAN,bytes.order())
                            for(j in 0 until bytes.limit() step 2)
                                assertEquals("P010 low six bits at $j",0,bytes.getShort(j).toInt() and 63)
                            val actual=LiveP010.rows(bytes,w,h)
                            for(y in 0 until h)for(x in 0 until w)
                                peak=maxOf(peak,abs(expected.y.get(x,y)-actual.y.get(x,y)))
                            for(y in 0 until h/2)for(x in 0 until w/2)
                                peak=maxOf(peak,abs(expected.u.get(x,y)-actual.u.get(x,y)),abs(expected.v.get(x,y)-actual.v.get(x,y)))
                            assertTrue("Packed P010 differs from CPU: $peak",peak<=1)
                            if(w==1024) {
                                val levels=(0 until w).map{actual.y.get(it,0)}.toSet().size
                                assertTrue("Ten-bit ramp collapsed to $levels levels",levels>=800)
                                rampLevels=maxOf(rampLevels,levels)
                            }
                            cases++
                        }
                    }
                }
            }
        }
        save("byte-pack-test.json",JSONObject().put("status","passed").put("synthetic",true)
            .put("cases",cases).put("maximumP010CodeError",peak).put("rampLevels",rampLevels)
            .put("transport","rgba8-packed-bytes").put("sensorPrecisionMeasured",false))
    }
    @Test fun actualEncoderRoutesAreQualifiedOrExplicitlyUnavailable(){
        val result=LiveBackendProbe.run(context.cacheDir,1024,128,24)
        save("backend-test.json",result.report)
        if(result.selected==null){assertTrue(result.report.getString("status") in listOf("unavailable","query_failed"))}
        else{
            assertEquals("qualified",result.report.getString("status"))
            val routes=result.report.getJSONArray("routes")
            val accepted=(0 until routes.length()).map{routes.getJSONObject(it)}.single{it.optString("status")=="qualified"}
            assertTrue(accepted.getJSONObject("positive").getBoolean("passed"));assertFalse(accepted.getJSONObject("eightBitNegative").getBoolean("passed"));assertTrue(accepted.getJSONObject("selectedSize").getBoolean("passed"))
        }
    }
    @Test fun liveScreenNeverStartsCameraOrRecordingImplicitly(){
        fun button(root:View,text:String):Button? {if(root is Button && root.text.toString()==text)return root;if(root is ViewGroup)for(i in 0 until root.childCount)button(root.getChildAt(i),text)?.let{return it};return null}
        ActivityScenario.launch<LiveLogActivity>(Intent(context,LiveLogActivity::class.java)).use{scenario->
            scenario.onActivity{a->assertNotNull(button(a.window.decorView,"Test Log recording backend"));assertNotNull(button(a.window.decorView,"Live attempt reports"));assertFalse(requireNotNull(button(a.window.decorView,"Record LogC3")).isEnabled)}
            scenario.recreate();instrumentation.waitForIdleSync()
            scenario.onActivity{a->assertFalse(requireNotNull(button(a.window.decorView,"Record LogC3")).isEnabled)}
            val image=instrumentation.uiAutomation.takeScreenshot();assertNotNull(image)
            val file=File(context.filesDir,"exports/live-log/live-screen.png");file.parentFile!!.mkdirs();file.outputStream().use{image!!.compress(Bitmap.CompressFormat.PNG,100,it)};image?.recycle()
            save("screen-test.json",JSONObject().put("status","passed").put("implicitRecording",false))
        }
    }
}
