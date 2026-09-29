package com.s23log.probe

import android.Manifest
import android.hardware.camera2.CameraManager
import android.opengl.EGL14
import android.opengl.GLES30
import android.os.Build
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.camera.CameraControls
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.ProcessingPath
import com.s23log.probe.gpu.GlEnvironment
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** A missing HDR camera is recorded explicitly; synthetic tests cannot stand in for this gate. */
@RunWith(AndroidJUnit4::class)
class ColourCameraTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private fun save(data:JSONObject) {
        val dir=File(context.filesDir,"exports/colour");check(dir.isDirectory||dir.mkdirs())
        File(dir,"camera.json").writeText(data.put("kind","colour-camera").put("appCommit",BuildConfig.SOURCE_REVISION)
            .put("physicalS23UltraCertified",false).put("colourAccuracyCertified",false).toString(2))
    }
    private fun unavailable(reason:String) = save(JSONObject().put("status","unavailable").put("reason",reason))
    private fun await(s:ActivityScenario<MainActivity>,label:String,predicate:(MainActivity)->Boolean) {
        val until=System.nanoTime()+TimeUnit.SECONDS.toNanos(45);val ok=AtomicBoolean()
        while(System.nanoTime()<until) { s.onActivity { ok.set(predicate(it)) };if(ok.get())return;Thread.sleep(100) }
        var status="";s.onActivity { status=it.findViewById<TextView>(R.id.cameraStatus).text.toString() }
        fail("$label: $status")
    }
    @Test fun supportedCameraRecordsThroughProcessorAndIndependentMonitor() {
        if(Build.VERSION.SDK_INT<33) { unavailable("API 33 required");return }
        val manager=context.getSystemService(CameraManager::class.java)
        val pair=CameraCatalog.discover(manager).targets.asSequence().flatMap { target ->
            CameraCatalog.plan(target).modes.filter { it.processing==ProcessingPath.GPU_HLG10 && !it.ratePlan.requiresManual }
                .map { target to it }.asSequence()
        }.firstOrNull()
        if(pair==null) { unavailable("No advertised non-manual HLG camera plus rendered Main10 encoder candidate");return }
        val gate=try { GlEnvironment.create(rgb10=true) } catch(e:Exception) { unavailable("RGB10 EGL unavailable: ${e.message}");return }
        gate.use {
            if("EGL_EXT_gl_colorspace_bt2020_hlg" !in EGL14.eglQueryString(it.display,EGL14.EGL_EXTENSIONS).orEmpty().split(' ') ||
                "GL_EXT_YUV_target" !in GLES30.glGetString(GLES30.GL_EXTENSIONS).orEmpty().split(' ')) {
                unavailable("HLG EGL colourspace or explicit YUV import extension unavailable");return
            }
        }
        val (target,mode)=pair
        val oldAudio=CameraSettings.audio(context);val oldCamera=CameraSettings.camera(context)
        val oldMode=CameraSettings.mode(context,target.key);val oldControls=CameraSettings.controls(context,target.key)
        CameraSettings.saveAudio(context,AudioMode.OFF);CameraSettings.select(context,target.key)
        CameraSettings.saveMode(context,target.key,mode.key);CameraSettings.saveControls(context,target.key,CameraControls())
        try {
            ActivityScenario.launch(MainActivity::class.java).use { s ->
                await(s,"GPU candidate selected") { it.findViewById<Button>(R.id.record).isEnabled &&
                    it.findViewById<TextView>(R.id.colourStatus).text.contains("GPU") }
                val previous=CaptureHistory.latest(context).report?.name
                s.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(s,"Processed frames acknowledged") { it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Recording ") }
                Thread.sleep(2000)
                s.onActivity { assertTrue(it.findViewById<Button>(R.id.monitorTransform).isEnabled);it.findViewById<Button>(R.id.monitorTransform).performClick() }
                Thread.sleep(2000)
                s.onActivity { it.findViewById<Button>(R.id.monitorTransform).performClick() }
                Thread.sleep(1500);s.onActivity { it.findViewById<Button>(R.id.record).performClick() }
                await(s,"Processed file finalized") { CaptureHistory.latest(context).report?.name != previous }
                val report=JSONObject(requireNotNull(CaptureHistory.latest(context).report).readText())
                assertEquals(report.toString(),"checked",report.getString("status"))
                val processor=report.getJSONObject("processing")
                assertTrue(processor.getBoolean("cleanupConfirmed"));assertTrue(processor.isNull("error"))
                assertTrue(processor.getLong("submittedFrames")>2)
                assertTrue(processor.getJSONObject("monitor").getLong("displayedFrames")>2)
                assertEquals(10,report.getJSONObject("verification").getInt("lumaBitDepth"))
                save(JSONObject().put("status","recorded").put("modeKey",mode.key).put("monitorToggled",true)
                    .put("validation",report).put("scope","Short camera integration capture; not sustained or calibrated colour acceptance"))
            }
        } finally {
            CameraSettings.saveAudio(context,oldAudio);oldCamera?.let { CameraSettings.select(context,it) }
            CameraSettings.saveMode(context,target.key,oldMode);CameraSettings.saveControls(context,target.key,oldControls)
        }
    }
}
