package com.s23log.probe

import android.content.Intent
import android.graphics.Bitmap
import android.os.Build
import android.widget.Button
import android.view.View
import android.view.ViewGroup
import androidx.core.content.FileProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.core.*
import com.s23log.probe.develop.*
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

@RunWith(AndroidJUnit4::class)
class RawDevelopmentAndroidTest {
    private val instrumentation get()=InstrumentationRegistry.getInstrumentation()
    private val context get()=instrumentation.targetContext
    private fun evidence(name:String,json:JSONObject){val f=File(context.filesDir,"exports/raw-development/$name.json");f.parentFile!!.mkdirs();f.writeText(json.put("appCommit",BuildConfig.SOURCE_REVISION).put("physicalCameraCertified",false).toString(2))}
    private fun fixture():File {
        val file=File(context.filesDir,"exports/raw-sequences/raw-${UUID.randomUUID()}.s23raw");file.parentFile!!.mkdirs()
        val h=JSONObject().put("schemaVersion",1).put("kind","continuous-raw").put("source","RAW_SENSOR").put("sampleEncoding","uint16le")
            .put("width",128).put("height",128).put("rowBytes",256).put("cfa",0).put("fpsRequested",24).put("logicalCamera","0").put("physicalCamera",JSONObject.NULL)
            .put("device",JSONObject().put("model","SYNTHETIC_FIXTURE").put("fingerprint","synthetic-development-test"))
        file.outputStream().use { out -> RawSequenceFormat.header(out,h.toString().toByteArray())
            repeat(8){i->val m=JSONObject().put("sensorTimestampNs",1_000_000_000L+i*1_000_000_000L/24).put("iso",100).put("exposureNs",10_000_000)
                .put("blackLevels",JSONArray(listOf(64,64,64,64))).put("whiteLevel",4095).put("neutralColorPoint",JSONArray(listOf(1,1,1)))
                val bytes=ByteBuffer.allocate(128*128*2).order(ByteOrder.LITTLE_ENDIAN);repeat(128*128){bytes.putShort(790)}
                RawSequenceFormat.frame(out,m.toString().toByteArray(),bytes.array()) }
        };return file
    }
    private fun profile(index:RawSourceIndex):JSONObject=JSONObject().put("schemaVersion",1).put("kind","raw-colour-profile").put("source",index.binding())
        .put("calibration",JSONObject().put("status","synthetic").put("evidence","Android software fixture").put("illuminant","synthetic"))
        .put("cameraToXyzD65",RawJson.matrixJson(RawDevelopMath.inverse(RawDevelopMath.XYZ_TO_AWG3))).put("bayerWhiteBalance",JSONArray(listOf(1,1,1,1)))
        .put("sceneScale",1).put("crop",JSONArray(listOf(0,0,128,128))).put("iso",100).put("exposureNs",10_000_000)
    private fun await(store:RawDevelopmentStore){for(i in 0..400){instrumentation.waitForIdleSync();if(!store.state.busy)return;Thread.sleep(25)};fail("Development worker did not finish")}
    @Test fun androidParserProfileImportAndScreenRecreationPreserveSource(){
        val source=fixture();val original=RawJson.hash(source);val index=RawSourceReader.scan(source)
        val imported=File(context.filesDir,"exports/raw-development/import-fixture.json").apply{parentFile!!.mkdirs();writeText(profile(index).toString())}
        val app=context.applicationContext as S23Application;val store=app.rawDevelopment
        try {
            ActivityScenario.launch<RawDevelopActivity>(Intent(context,RawDevelopActivity::class.java).putExtra("sourceName",source.name)).use { scenario ->
                await(store);assertNull(store.state.error);assertEquals(8,store.state.index!!.frames.size)
                val uri=FileProvider.getUriForFile(context,"${context.packageName}.files",imported)
                instrumentation.runOnMainSync{store.importProfile(uri)};await(store);assertNull(store.state.error);assertNotNull(store.state.profileFile)
                scenario.recreate();instrumentation.waitForIdleSync();assertNotNull(store.state.profile)
                fun hasButton(view:View,label:String):Boolean=if(view is Button && view.text.toString()==label)true else if(view is ViewGroup)(0 until view.childCount).any{hasButton(view.getChildAt(it),label)}else false
                scenario.onActivity { a -> assertTrue(hasButton(a.window.decorView,"Develop as LogC3"));assertTrue(hasButton(a.window.decorView,"Share selected profile")) }
                val drawn=CountDownLatch(1);scenario.onActivity{a->a.window.decorView.postOnAnimation{a.window.decorView.postOnAnimation{drawn.countDown()}}};assertTrue(drawn.await(10,TimeUnit.SECONDS))
                val image=instrumentation.uiAutomation.takeScreenshot();assertNotNull(image)
                val destination=File(context.filesDir,"exports/raw-development/developer-screen.png")
                destination.outputStream().use{assertTrue(image.compress(Bitmap.CompressFormat.PNG,100,it))};image.recycle()
                evidence("native-ui",JSONObject().put("status","passed").put("sourceCrcChecked",true).put("profileImported",true).put("activityRecreated",true).put("sourceHashUnchanged",original==RawJson.hash(source)).put("realCameraFootage",false))
            }
            assertEquals(original,RawJson.hash(source))
        } finally { source.delete();imported.delete();store.state.profileFile?.delete() }
    }
    @Test fun androidColourArithmeticUsesMoreThanEightBitsAndRejectsBadSource(){
        val source=fixture();try {
            val index=RawSourceReader.scan(source);val p=RawColourProfile.parse(profile(index),index,false);var pairs=0
            index.rows(index.frames[0]).use{rows->RawFrameDeveloper().develop(rows,p.parameters(index,index.frames[0]),sink=object:LogRowSink{override fun pair(y:Int,first:DoubleArray,second:DoubleArray){pairs++;assertEquals(RawDevelopMath.logC3(726.0/4031),first[0],2e-7)}})}
            assertEquals(64,pairs)
            val full=(0..1023).map{RawDevelopMath.logC3(it/1023.0)}.toSet();assertEquals(1024,full.size)
            java.io.RandomAccessFile(source,"rw").use{it.seek(index.frames[0].offset);it.write(0)}
            var rejected=false;try{RawSourceReader.scan(source)}catch(_:IllegalArgumentException){rejected=true};assertTrue(rejected);assertTrue(source.exists())
            evidence("android-math",JSONObject().put("status","passed").put("referenceGreyMatched",true).put("distinctMathLevels",full.size).put("corruptionRejected",true).put("sourceRetained",true))
        }finally{source.delete()}
    }
    @Test fun actualP010CodecRouteIsQualifiedOrExplicitlyUnavailable(){
        if(Build.VERSION.SDK_INT<33){evidence("p010-codec",JSONObject().put("status","unavailable").put("reason","API 33 required").put("encodedPixelsTested",false));return}
        val candidates=LogP010Codec.candidates(128,128,24)
        if(candidates.isEmpty()){evidence("p010-codec",JSONObject().put("status","unavailable").put("reason","No advertised HEVC Main10 P010 Image encoder").put("encodedPixelsTested",false));return}
        val choice=LogP010Codec.qualify(context.cacheDir,128,128,24,{}, {})
        val destination=File(context.filesDir,"exports/raw-development/colour-p010-${UUID.randomUUID()}.mp4");destination.parentFile!!.mkdirs()
        fun row(y:Int,frame:Int)=DoubleArray(128*3){i->val channel=i%3;val x=i/3
            val value=when(channel){0->.12+x*.001;1->.18+y*.0005;else->.08+frame*.01};RawDevelopMath.logC3(value)}
        LogP010Codec.encode(destination,choice.name,128,128,24,8,{}){f,p->for(y in 0 until 128 step 2)p.pair(y,row(y,f),row(y+1,f))}
        val verification=LogP010Codec.verify(destination,128,128,24,8,{}){f,p->val comparison=LogFrameComparison(p);for(y in 0 until 128 step 2)comparison.pair(y,row(y,f),row(y+1,f));comparison.result()}
        evidence("p010-codec",JSONObject().put("status","passed").put("qualification",choice.qualification).put("verification",verification).put("file",destination.name).put("encodedPixelsTested",true).put("realCameraFootage",false))
    }
}
