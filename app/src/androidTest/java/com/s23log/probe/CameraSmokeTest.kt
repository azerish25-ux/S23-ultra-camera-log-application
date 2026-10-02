package com.s23log.probe

import android.Manifest
import android.content.Context
import android.widget.Button
import android.widget.TextView
import androidx.core.content.FileProvider
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.storage.CaptureHistory
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.core.DynamicRange
import com.s23log.probe.core.RecordingMode
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/** Exercises real framework, camera, encoder and files. Emulator results are not S23 Ultra certification. */
@RunWith(AndroidJUnit4::class)
class CameraSmokeTest {
    @get:Rule val permission: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA)
    private val context: Context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Before fun selectExplicitVideoOnly() { CameraSettings.saveAudio(context, com.s23log.probe.core.AudioMode.OFF) }

    private fun await(scenario: ActivityScenario<MainActivity>, label: String, seconds: Long = 45, predicate: (MainActivity) -> Boolean) {
        val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(seconds)
        val success = AtomicBoolean()
        while (System.nanoTime() < end) {
            scenario.onActivity { success.set(predicate(it)) }
            if (success.get()) return
            Thread.sleep(150)
        }
        val status = AtomicReference("")
        scenario.onActivity { status.set(it.findViewById<TextView>(R.id.cameraStatus).text.toString()) }
        fail("Timed out: $label. Last camera state: ${status.get()}")
    }
    private fun live(scenario: ActivityScenario<MainActivity>) = await(scenario, "live sensor preview") {
        it.findViewById<TextView>(R.id.cameraStatus).text.toString().startsWith("Live preview")
    }
    private fun click(scenario: ActivityScenario<MainActivity>, id: Int) {
        scenario.onActivity { activity ->
            val button = activity.findViewById<Button>(id)
            assertTrue("${activity.resources.getResourceEntryName(id)} must be enabled; state: " +
                activity.findViewById<TextView>(R.id.cameraStatus).text, button.isEnabled)
            assertTrue(button.performClick())
        }
    }
    private fun waitForNewOutput(previous: String?, minimumSpanUs: Long = 0) {
        val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(30)
        while (System.nanoTime() < end) {
            val entry = CaptureHistory.latest(context)
            if (entry.report?.name != previous && entry.uris.isNotEmpty() && entry.report != null) {
                val json = JSONObject(entry.report.readText())
                assertEquals(json.toString(), "checked", json.getString("status"))
                assertTrue(json.getJSONObject("verification").getBoolean("firstSyncFrameDecoded"))
                assertTrue(json.getJSONObject("verification").getInt("samples") >= 2)
                assertTrue("Recorded sample span must meet the duration requirement", json.getJSONObject("verification").getLong("sampleSpanUs") >= minimumSpanUs)
                context.contentResolver.openInputStream(entry.uris.first()).use { input ->
                    assertNotNull(input)
                    assertTrue(input!!.read(ByteArray(16)) > 0)
                }
                val attempt = File(context.filesDir, "exports/recording-evidence/${json.getString("attemptReport")}")
                val report = runCatching { JSONObject(attempt.readText()) }.getOrNull()
                if (report?.optBoolean("closed") != true) { Thread.sleep(50); continue }
                assertEquals(json.getString("attemptId"), report.getString("attemptId"))
                assertEquals(BuildConfig.SOURCE_REVISION, report.getString("sourceRevision"))
                assertTrue(report.toString(), report.getJSONObject("classification").getBoolean("recordingSucceeded"))
                assertFalse(report.getJSONObject("classification").getBoolean("fullDecodeVerified"))
                assertFalse(report.getJSONObject("classification").getBoolean("physicalCameraCertified"))
                return
            }
            if (entry.report?.name != previous && entry.message.contains("rejected")) fail(entry.message)
            Thread.sleep(150)
        }
        fail("No new verified video: ${CaptureHistory.latest(context).message}")
    }
    private fun begin(scenario: ActivityScenario<MainActivity>) {
        live(scenario)
        await(scenario, "negotiated SDR recording candidate") { it.findViewById<Button>(R.id.record).isEnabled }
        click(scenario, R.id.record)
        await(scenario, "recording capture session") { it.findViewById<TextView>(R.id.cameraStatus).text.toString().startsWith("Recording ") }
    }

    @Test fun diagnosticsSurviveRecreationAndShareAsFiles() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            live(scenario)
            click(scenario, R.id.diagnosticsTab)
            click(scenario, R.id.runProbe)
            scenario.recreate()
            await(scenario, "completed report") { it.findViewById<Button>(R.id.shareReport).isEnabled }
            scenario.onActivity { assertTrue(it.findViewById<TextView>(R.id.report).text.contains("S23LOG")) }
            val latch = CountDownLatch(1)
            val result = AtomicReference<Result<List<File>>>()
            scenario.onActivity { (it.application as S23Application).reports.export { files -> result.set(files); latch.countDown() } }
            assertTrue(latch.await(10, TimeUnit.SECONDS))
            val files = result.get().getOrThrow()
            assertEquals(2, files.size)
            val exported = JSONObject(files.first { it.extension == "json" }.readText())
            assertEquals(2, exported.getInt("schemaVersion"))
            assertEquals(BuildConfig.SOURCE_REVISION, exported.getString("sourceRevision"))
            assertFalse(exported.getJSONObject("stageEvidence").getBoolean("recordingVerified"))
            assertFalse(exported.getJSONObject("stageEvidence").getBoolean("physicalCameraCertified"))
            scenario.onActivity { assertNotNull(it.findViewById<Button>(R.id.recordingAttempts)) }
            files.forEach { file ->
                val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
                context.contentResolver.openInputStream(uri).use { assertTrue(it!!.read() >= 0) }
            }
        }
    }
    @Test fun previewSurvivesStopAndRecreation() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            live(scenario)
            scenario.moveToState(Lifecycle.State.CREATED)
            Thread.sleep(500)
            scenario.moveToState(Lifecycle.State.RESUMED)
            live(scenario)
            scenario.recreate()
            live(scenario)
        }
    }
    @Test fun recordsTenIndependentDecodableVideos() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            repeat(10) {
                val previous = CaptureHistory.latest(context).report?.name
                begin(scenario)
                Thread.sleep(4000)
                click(scenario, R.id.record)
                waitForNewOutput(previous)
                live(scenario)
            }
        }
    }
    @Test fun recordsAtLeastSixtySeconds() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            val previous = CaptureHistory.latest(context).report?.name
            begin(scenario)
            Thread.sleep(65_000)
            click(scenario, R.id.record)
            waitForNewOutput(previous, minimumSpanUs = 60_000_000)
            live(scenario)
        }
    }
    @Test fun recordingLocksOrientationAndReportsResourceBudget() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            val original = java.util.concurrent.atomic.AtomicInteger()
            scenario.onActivity { original.set(it.requestedOrientation) }
            val previous = CaptureHistory.latest(context).report?.name
            begin(scenario)
            scenario.onActivity { assertEquals(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LOCKED, it.requestedOrientation) }
            Thread.sleep(2500)
            click(scenario, R.id.record)
            waitForNewOutput(previous)
            live(scenario)
            scenario.onActivity { assertEquals(original.get(), it.requestedOrientation) }
            val report = JSONObject(requireNotNull(CaptureHistory.latest(context).report).readText())
            val resources = report.getJSONObject("resourceSafety")
            assertTrue(resources.getLong("availableBytes") >= resources.getLong("requiredFreeBytes"))
            assertEquals(android.os.Build.VERSION.SDK_INT >= 29, resources.getBoolean("publicationCopyBudgeted"))
            assertFalse(resources.getBoolean("estimateIsGuarantee"))
            assertFalse(resources.getBoolean("physicalThermalCertification"))
            assertTrue(report.getLong("minimumObservedFreeBytes") > 0)
            assertTrue(report.isNull("resourceStopReason"))
        }
    }
    @Test fun leavingActivityFinalizesRecording() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            val previous = CaptureHistory.latest(context).report?.name
            begin(scenario)
            Thread.sleep(4000)
            scenario.moveToState(Lifecycle.State.CREATED)
            waitForNewOutput(previous)
            scenario.moveToState(Lifecycle.State.RESUMED)
            live(scenario)
        }
    }
    @Test fun providerRejectsPathsOutsideExportDirectory() {
        val private = File(context.filesDir, "not-an-export.txt").apply { writeText("private") }
        try {
            try {
                FileProvider.getUriForFile(context, "${context.packageName}.files", private)
                fail("Provider must not expose all app-private files")
            } catch (_: IllegalArgumentException) { /* required */ }
        } finally { private.delete() }
    }
    @Test fun sidecarWriteFailureKeepsActualDecodableRecording() {
        val previous = CaptureHistory.latest(context)
        val directory = File(context.filesDir, "exports/validation")
        val backup = File(context.filesDir, "validation-backup-${java.util.UUID.randomUUID()}")
        var captured: android.net.Uri? = null
        val existed = directory.exists()
        if (existed) assertTrue(directory.renameTo(backup))
        assertTrue(directory.createNewFile()) // forces the real report write to fail
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                begin(scenario)
                Thread.sleep(4000)
                click(scenario, R.id.record)
                await(scenario, "video retained despite report write failure") {
                    val entry = CaptureHistory.latest(context)
                    if (entry.uris.isNotEmpty() && entry.uris != previous.uris) captured = entry.uris.first()
                    captured != null && entry.message.contains("Validation report unavailable")
                }
                val entry = CaptureHistory.latest(context)
                assertNull(entry.report)
                assertTrue(entry.message.startsWith("Saved "))
                val retriever = android.media.MediaMetadataRetriever()
                try {
                    retriever.setDataSource(context, captured!!)
                    val frame = retriever.getFrameAtTime(0)
                    assertNotNull("Real footage must remain decodable", frame)
                    frame?.recycle()
                } finally { retriever.release() }
            }
        } finally {
            captured?.let { context.contentResolver.delete(it, null, null) }
            assertTrue(directory.delete())
            if (existed) assertTrue(backup.renameTo(directory))
            CaptureHistory.save(context, previous.uris, previous.report, previous.message)
        }
    }

    private fun advertisedSdrModes(): List<RecordingMode> {
        val selected = requireNotNull(CameraSettings.camera(context))
        val manager = context.getSystemService(android.hardware.camera2.CameraManager::class.java)
        val target = CameraCatalog.discover(manager).targets.first { it.key == selected }
        return CameraCatalog.plan(target).modes.filter { it.range == DynamicRange.SDR && !it.ratePlan.requiresManual && it.fps <= 30 }
    }

    private fun selectReadyMode(scenario: ActivityScenario<MainActivity>, mode: RecordingMode) {
        await(scenario, "mode selector ready") {
            it.findViewById<android.widget.Spinner>(R.id.modeSelector).isEnabled
        }
        scenario.onActivity { activity ->
            val selector = activity.findViewById<android.widget.Spinner>(R.id.modeSelector)
            val choice = (0 until selector.count).first { selector.getItemAtPosition(it).toString() == mode.label }
            selector.setSelection(choice)
        }
        // A stale Live-preview label (or a fixed sleep) is not acknowledgement of
        // this selection. Require the engine's accepted key AND its new live session.
        await(scenario, "fresh live preview for ${mode.label}") { activity ->
            val key = CameraSettings.camera(context)
            key != null && CameraSettings.mode(context, key) == mode.key &&
                activity.findViewById<android.widget.Spinner>(R.id.modeSelector).selectedItem.toString() == mode.label &&
                activity.findViewById<TextView>(R.id.cameraStatus).text.toString().startsWith("Live preview") &&
                activity.findViewById<Button>(R.id.applyControls).isEnabled &&
                activity.findViewById<Button>(R.id.record).isEnabled
        }
    }

    @Test fun repeatedModeChangesRestoreLivePreviewAndActionReadiness() {
        val settings = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val before = settings.all.filterValues { it is String }
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                live(scenario)
                val choices = advertisedSdrModes()
                assertTrue("At least one SDR candidate is required", choices.isNotEmpty())
                for (mode in listOf(choices.last(), choices.first(), choices.last())) {
                    selectReadyMode(scenario, mode)
                    scenario.recreate()
                    live(scenario)
                    scenario.onActivity { activity ->
                        val key = requireNotNull(CameraSettings.camera(context))
                        assertEquals(mode.key, CameraSettings.mode(context, key))
                        assertEquals(mode.label, activity.findViewById<android.widget.Spinner>(R.id.modeSelector).selectedItem.toString())
                        assertTrue(activity.findViewById<Button>(R.id.applyControls).isEnabled)
                        assertTrue(activity.findViewById<Button>(R.id.record).isEnabled)
                    }
                }
            }
        } finally {
            val editor = settings.edit().clear()
            before.forEach { (key, value) -> editor.putString(key, value as String) }
            assertTrue(editor.commit())
        }
    }

    @Test fun selectedModeAndControlIntentSurviveRecreation() {
        val settings = context.getSharedPreferences("camera_settings_v1", Context.MODE_PRIVATE)
        val before = settings.all.filterValues { it is String }
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                live(scenario)
                val mode = advertisedSdrModes().last()
                selectReadyMode(scenario, mode)
                scenario.onActivity { activity ->
                    activity.findViewById<android.widget.CompoundButton>(R.id.manualExposure).isChecked = false
                    activity.findViewById<android.widget.EditText>(R.id.isoInput).setText("125")
                    activity.findViewById<android.widget.EditText>(R.id.shutterInput).setText("20")
                }
                click(scenario, R.id.applyControls)
                await(scenario, "accepted control intent saved") {
                    val key = requireNotNull(CameraSettings.camera(context))
                    val saved = CameraSettings.controls(context, key)
                    saved.iso == 125 && saved.exposureNs == 20_000_000L && !saved.manualExposure
                }
                scenario.recreate()
                live(scenario)
                scenario.onActivity { activity ->
                    assertEquals("125", activity.findViewById<android.widget.EditText>(R.id.isoInput).text.toString())
                    assertEquals("20.000000", activity.findViewById<android.widget.EditText>(R.id.shutterInput).text.toString())
                    assertEquals(mode.label, activity.findViewById<android.widget.Spinner>(R.id.modeSelector).selectedItem.toString())
                }
            }
        } finally {
            val editor = settings.edit().clear()
            before.forEach { (key, value) -> editor.putString(key, value as String) }
            editor.commit()
        }
    }

    @Test fun recordControlStaysVisibleWhenManualPanelScrollsAndInLandscape() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            live(scenario)
            fun assertDock(activity: MainActivity) {
                val record = activity.findViewById<Button>(R.id.record)
                val rect = android.graphics.Rect()
                assertTrue(record.getGlobalVisibleRect(rect))
                assertEquals(record.height, rect.height())
                var parent = record.parent
                while (parent is android.view.View) {
                    assertFalse("Record must not scroll away", parent is android.widget.ScrollView)
                    parent = parent.parent
                }
            }
            click(scenario, R.id.openControls)
            scenario.onActivity { activity ->
                val panel = activity.findViewById<android.widget.ScrollView>(R.id.controlsPanel)
                assertEquals(android.view.View.VISIBLE, panel.visibility)
                panel.scrollTo(0, 10000)
                assertDock(activity)
                activity.requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
            }
            await(scenario, "landscape layout") {
                it.resources.configuration.orientation == android.content.res.Configuration.ORIENTATION_LANDSCAPE &&
                    it.findViewById<Button>(R.id.record).width > 0
            }
            live(scenario)
            scenario.onActivity { assertDock(it); it.requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED }
        }
    }

    @Test fun userConfirmedModeTestStopsAndExportsFirstSampleEvidence() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            live(scenario)
            val previous = CaptureHistory.latest(context).report?.name
            click(scenario, R.id.testMode)
            val instrumentation = InstrumentationRegistry.getInstrumentation()
            instrumentation.waitForIdleSync()
            val buttons = instrumentation.uiAutomation.rootInActiveWindow.findAccessibilityNodeInfosByText("Record test")
            assertTrue("An explicit confirmation is required", buttons.isNotEmpty())
            assertTrue(buttons.first().performAction(android.view.accessibility.AccessibilityNodeInfo.ACTION_CLICK))
            waitForNewOutput(previous, minimumSpanUs = 3_000_000)
            live(scenario)
            val json = JSONObject(requireNotNull(CaptureHistory.latest(context).report).readText())
            assertEquals("user_initiated_short_recording", json.getJSONObject("requested").getString("testKind"))
            assertTrue(json.getJSONArray("stages").toString().contains("first_sample_written"))
            assertTrue(json.getJSONObject("device").getString("appCommit").isNotBlank())
            assertTrue(json.getJSONObject("verification").has("cadenceStatus"))
        }
    }

}
