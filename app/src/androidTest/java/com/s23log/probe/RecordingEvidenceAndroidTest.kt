package com.s23log.probe

import android.Manifest
import android.content.Context
import android.hardware.camera2.CameraManager
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.camera.SurfaceRecorder
import com.s23log.probe.core.DynamicRange
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Actual SurfaceRecorder creation/cleanup, not injected JSON. No camera session is opened in these controls. */
@RunWith(AndroidJUnit4::class)
class RecordingEvidenceAndroidTest {
    @get:Rule val permission = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context: Context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private val directory get() = File(context.filesDir, "exports/recording-evidence")
    private fun existing() = directory.listFiles().orEmpty().map { it.name }.toSet()
    private fun mode() = CameraCatalog.discover(context.getSystemService(CameraManager::class.java)).targets
        .flatMap { CameraCatalog.plan(it).modes }.first { it.range == DynamicRange.SDR && !it.ratePlan.requiresManual && it.width <= 1280 && it.fps <= 30 }
    private fun awaitReport(before: Set<String>): JSONObject {
        val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(15)
        while (System.nanoTime() < end) {
            for (file in directory.listFiles().orEmpty().filter { it.name !in before }) {
                val report = runCatching { JSONObject(file.readText()) }.getOrNull()
                if (report?.optBoolean("closed") == true) return report
            }
            Thread.sleep(50)
        }
        error("No closed production recording-attempt report")
    }
    private fun stage(report: JSONObject, name: String): String {
        val rows = report.getJSONArray("stages")
        return (0 until rows.length()).map(rows::getJSONObject).first { it.getString("stage") == name }.getString("outcome")
    }
    @Test fun missingEncoderProducesEarlyFailureWithoutInventingCameraSession() {
        val candidate = mode().copy(encoder = "s23log.deliberately.missing.encoder")
        val before = existing()
        try {
            SurfaceRecorder.prepare(context, candidate, 0, mapOf("testKind" to "P003-missing-encoder-control")) { fail("Preparation must throw, not report a successful recording") }
            fail("Missing encoder should be rejected")
        } catch (_: Exception) { /* Real framework creation rejection, retained separately from unavailable advertisements. */ }
        val report = awaitReport(before)
        assertEquals(BuildConfig.SOURCE_REVISION, report.getString("sourceRevision"))
        assertEquals("failed", stage(report, "preparation")); assertEquals("not_run", stage(report, "configured"))
        assertFalse(report.getJSONObject("classification").getBoolean("recordingSucceeded"))
    }
    @Test fun cancelledPreparedEncoderWithoutCameraFramesIsNotARecording() {
        val candidate = mode(); val before = existing(); val ended = CountDownLatch(1)
        val recorder = SurfaceRecorder.prepare(context, candidate, 0, mapOf("testKind" to "P003-no-camera-no-frames-control")) { ended.countDown() }
        recorder.cancel("Deliberate stop before a camera session or first frame")
        assertTrue("Real recorder cleanup must complete", ended.await(15, TimeUnit.SECONDS))
        val report = awaitReport(before)
        assertEquals("passed", stage(report, "preparation")); assertEquals("not_run", stage(report, "configured"))
        assertEquals("blocked", stage(report, "encoded_output")); assertFalse(report.getJSONObject("classification").getBoolean("publishedOutput"))
        assertFalse(report.getJSONObject("classification").getBoolean("physicalCameraCertified"))
    }
}
