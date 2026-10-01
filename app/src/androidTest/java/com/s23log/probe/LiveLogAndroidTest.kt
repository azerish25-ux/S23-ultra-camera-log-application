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
            scenario.onActivity{a->assertNotNull(button(a.window.decorView,"Test Log recording backend"));assertFalse(requireNotNull(button(a.window.decorView,"Record LogC3")).isEnabled)}
            scenario.recreate();instrumentation.waitForIdleSync()
            scenario.onActivity{a->assertFalse(requireNotNull(button(a.window.decorView,"Record LogC3")).isEnabled)}
            val image=instrumentation.uiAutomation.takeScreenshot();assertNotNull(image)
            val file=File(context.filesDir,"exports/live-log/live-screen.png");file.parentFile!!.mkdirs();file.outputStream().use{image!!.compress(Bitmap.CompressFormat.PNG,100,it)};image?.recycle()
            save("screen-test.json",JSONObject().put("status","passed").put("implicitRecording",false))
        }
    }
}
