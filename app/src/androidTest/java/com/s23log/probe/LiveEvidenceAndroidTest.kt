package com.s23log.probe

import android.Manifest
import android.graphics.SurfaceTexture
import android.view.Surface
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.core.LiveLogOutput
import com.s23log.probe.core.LivePublication
import com.s23log.probe.live.LiveLogSession
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.io.IOException
import java.util.UUID
import java.util.concurrent.CancellationException
import java.util.concurrent.atomic.AtomicReference

/** Tests the real app worker. Injected faults and the default backend are explicitly separate. */
@RunWith(AndroidJUnit4::class)
class LiveEvidenceAndroidTest {
    @get:Rule val permission=GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val instrumentation=InstrumentationRegistry.getInstrumentation()
    private val context=instrumentation.targetContext
    private fun start(make:()->LiveLogSession,action:(LiveLogSession)->Unit):LiveLogSession {
        val ref=AtomicReference<LiveLogSession>()
        instrumentation.runOnMainSync{val owner=make();ref.set(owner);action(owner)}
        return ref.get()
    }
    private fun await(owner:LiveLogSession):JSONObject {
        val deadline=System.nanoTime()+120_000_000_000L
        while(System.nanoTime()<deadline) {
            val state=owner.state
            val file=state.attemptReport
            if(!state.busy && file!=null && file.isFile && file.length()>0) {
                val report=runCatching{JSONObject(file.readText())}.getOrNull()
                if(report?.optBoolean("closed")==true){
                    assertEquals(BuildConfig.SOURCE_REVISION,report.getString("sourceRevision"))
                    assertFalse(report.getJSONObject("classification").getBoolean("physicalCameraCertified"))
                    return report
                }
            }
            Thread.sleep(50)
        }
        instrumentation.runOnMainSync{owner.stop()}
        error("Actual live owner did not retain a closed attempt: ${owner.state}")
    }
    private fun stage(report:JSONObject,name:String):String {
        val rows=report.getJSONArray("stages")
        return (0 until rows.length()).map(rows::getJSONObject).single{it.getString("stage")==name}.getString("outcome")
    }
    private fun receipt(name:String,report:JSONObject,defaultBackend:Boolean=false) {
        val file=File(context.filesDir,"exports/live-evidence/integration-$name.json");file.parentFile!!.mkdirs()
        file.writeText(JSONObject().put("kind","live-attempt-integration-test").put("appCommit",BuildConfig.SOURCE_REVISION)
            .put("case",name).put("attemptId",report.getString("attemptId")).put("defaultBackendInvoked",defaultBackend)
            .put("faultInjected",!defaultBackend).put("physicalCameraTested",false).put("status","passed").toString(2))
    }
    @Test fun actualDefaultBackendProducesIndependentAttemptWithoutCamera(){
        val owner=start({LiveLogSession(context)}){it.testBackend(24)}
        val report=await(owner)
        assertEquals("backend_test",report.getString("attemptKind"));assertEquals("passed",stage(report,"gpu_reference"))
        assertTrue(stage(report,"codec_qualification") in listOf("passed","unavailable","inconclusive"))
        assertEquals("not_run",stage(report,"configured"));assertEquals("not_run",stage(report,"matched_raw_frames"))
        assertFalse(report.getBoolean("recordingRequested"));assertFalse(report.getJSONObject("classification").getBoolean("recordingSucceeded"))
        assertNotNull(owner.state.report);receipt("default-backend",report,true)
    }
    @Test fun actualWorkerSeparatesCancellationFromUnexpectedFault(){
        val cases=listOf("cancelled" to CancellationException("Injected before GPU qualification"),
            "io-failure" to IOException("Injected GPU observation IO failure"))
        for((name,fault) in cases){
            val owner=start({LiveLogSession(context,gpuProbe={throw fault})}){it.testBackend(24)}
            val report=await(owner)
            assertEquals(if(fault is CancellationException)"blocked" else "failed",stage(report,"gpu_reference"))
            assertEquals("not_run",stage(report,"codec_qualification"));assertEquals("not_run",stage(report,"configured"))
            receipt(name,report)
        }
    }
    @Test fun actualPrepareRejectsSyntheticAndStaleProfilesWithoutOpeningCamera(){
        for(name in listOf("synthetic-profile","stale-profile")){
            val json=JSONObject().put("calibration",JSONObject().put("status",if(name=="synthetic-profile")"synthetic" else "provisional"))
                .put("source",JSONObject().put("fingerprint","deliberately-not-this-firmware"))
            val texture=SurfaceTexture(false);val surface=Surface(texture)
            try {
                val owner=start({LiveLogSession(context)}){it.prepare(json,LiveLogOutput(0,0,1024,128,1),24,0f,true,false,surface,0)}
                val report=await(owner)
                assertEquals("failed",stage(report,"profile_validation"));assertEquals("not_run",stage(report,"gpu_reference"))
                assertEquals("not_run",stage(report,"configured"));assertEquals("not_run",stage(report,"matched_raw_frames"))
                assertFalse(report.getJSONObject("classification").getBoolean("publishedOutput"))
                assertNull(owner.state.media);receipt(name,report)
            } finally {surface.release();texture.release()}
        }
    }
    @Test fun actualPrivateFilesSurviveRenameFailureAndExistingDestination(){
        val root=File(context.cacheDir,"live-publication-${UUID.randomUUID()}").apply{mkdirs()}
        try {
            val source=File(root,"take.partial.mp4").apply{writeText("Authored non-video bytes for the file-operation test")}
            val original=source.readBytes();val target=File(root,"take.mp4")
            val failed=LivePublication.publish(source,target){_,_->false}
            assertNull(failed.published);assertEquals(source,failed.retained);assertArrayEquals(original,source.readBytes());assertFalse(target.exists())
            target.writeText("Existing unrelated fixture")
            val collision=LivePublication.publish(source,target){_,_->error("Must not move over an existing destination")}
            assertNull(collision.published);assertArrayEquals(original,source.readBytes());assertEquals("Existing unrelated fixture",target.readText())
            val r=File(context.filesDir,"exports/live-evidence/publication-file-test.json");r.parentFile!!.mkdirs()
            r.writeText(JSONObject().put("kind","live-publication-file-test").put("appCommit",BuildConfig.SOURCE_REVISION)
                .put("status","passed").put("sourceBytesPreserved",true).put("existingDestinationPreserved",true)
                .put("failedRenameNotPublished",true).put("validVideoTested",false).put("physicalCameraTested",false).toString(2))
        } finally {root.deleteRecursively()}
    }
}
