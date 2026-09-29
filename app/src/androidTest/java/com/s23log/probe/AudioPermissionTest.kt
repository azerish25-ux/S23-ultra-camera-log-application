package com.s23log.probe

import android.Manifest
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Context
import android.content.pm.PackageManager
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.s23log.probe.core.AudioMode
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Run separately after pm revoke, outside the microphone-granted instrumentation process. */
@RunWith(AndroidJUnit4::class)
class AudioPermissionTest {
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context: Context get() = instrumentation.targetContext
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, predicate: (MainActivity) -> Boolean) {
        val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(40)
        val ready = AtomicBoolean()
        while (System.nanoTime() < end) {
            scenario.onActivity { ready.set(predicate(it)) }
            if (ready.get()) return
            Thread.sleep(100)
        }
        fail(label)
    }
    private fun click(scenario: ActivityScenario<MainActivity>, id: Int) = scenario.onActivity {
        assertTrue(it.findViewById<Button>(id).isEnabled)
        assertTrue(it.findViewById<Button>(id).performClick())
    }
    private fun clickDialog(text: String) {
        val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(10)
        while (System.nanoTime() < end) {
            val nodes = instrumentation.uiAutomation.rootInActiveWindow?.findAccessibilityNodeInfosByText(text).orEmpty()
            val button = nodes.firstOrNull { it.text?.toString() == text && it.isClickable }
            if (button != null) { assertTrue(button.performAction(AccessibilityNodeInfo.ACTION_CLICK)); return }
            Thread.sleep(100)
        }
        fail("No clickable dialog action: $text")
    }
    private fun denySystemPermission() {
        val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(15)
        while (System.nanoTime() < end) {
            val root = instrumentation.uiAutomation.rootInActiveWindow
            val button = listOf("com.android.permissioncontroller", "com.google.android.permissioncontroller")
                .flatMap { root?.findAccessibilityNodeInfosByViewId("$it:id/permission_deny_button").orEmpty() }
                .firstOrNull { it.isClickable && it.isVisibleToUser }
            if (button != null) { assertTrue(button.performAction(AccessibilityNodeInfo.ACTION_CLICK)); return }
            Thread.sleep(100)
        }
        fail("The actual Android microphone permission dialog did not appear")
    }
    @Test fun realDenialCancelAndExplicitVideoOnlyPreserveUserIntent() {
        assertEquals("CI must revoke microphone permission before starting this process", PackageManager.PERMISSION_DENIED,
            context.checkSelfPermission(Manifest.permission.RECORD_AUDIO))
        assertEquals(PackageManager.PERMISSION_GRANTED, context.checkSelfPermission(Manifest.permission.CAMERA))
        CameraSettings.saveAudio(context, AudioMode.MONO)
        val automation = instrumentation.uiAutomation
        val service = automation.serviceInfo
        service.flags = service.flags or AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
        automation.serviceInfo = service
        val previous = CaptureHistory.latest(context).report?.name
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            scenario.onActivity { it.getPreferences(Context.MODE_PRIVATE).edit().remove("audioPermissionAsked").commit() }
            fun live() = await(scenario, "Preview should remain usable without microphone permission") {
                it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") && it.findViewById<Button>(R.id.record).isEnabled
            }
            live()
            click(scenario, R.id.record)
            clickDialog(context.getString(R.string.cancel))
            assertEquals(AudioMode.MONO, CameraSettings.audio(context))
            assertEquals(previous, CaptureHistory.latest(context).report?.name)
            live()
            click(scenario, R.id.record)
            clickDialog(context.getString(R.string.audio_allow))
            denySystemPermission()
            await(scenario, "Denied audio is shown, not silently disabled") {
                it.findViewById<TextView>(R.id.audioStatus).text.contains("denied", true) && it.findViewById<Button>(R.id.record).isEnabled
            }
            assertEquals(PackageManager.PERMISSION_DENIED, context.checkSelfPermission(Manifest.permission.RECORD_AUDIO))
            assertEquals(AudioMode.MONO, CameraSettings.audio(context))
            assertEquals(previous, CaptureHistory.latest(context).report?.name)
            click(scenario, R.id.record)
            clickDialog(context.getString(R.string.audio_video_only_action))
            assertEquals(AudioMode.OFF, CameraSettings.audio(context))
            assertEquals("Choosing muted does not start a stale take", previous, CaptureHistory.latest(context).report?.name)
            click(scenario, R.id.record)
            await(scenario, "An explicit Record action starts video only") {
                it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Recording ") &&
                    it.findViewById<TextView>(R.id.cameraStatus).text.contains("video only")
            }
            Thread.sleep(3500)
            click(scenario, R.id.record)
            await(scenario, "Muted file finalized") { CaptureHistory.latest(context).report?.name != previous }
            val report = JSONObject(requireNotNull(CaptureHistory.latest(context).report).readText())
            assertEquals("checked", report.getString("status"))
            assertTrue(report.getBoolean("videoOnly"))
            assertEquals(0, report.getJSONObject("verification").getInt("audioTrackCount"))
            val evidence = JSONObject().put("kind", "microphone-permission-test").put("appCommit", BuildConfig.SOURCE_REVISION)
                .put("initialMicrophonePermissionDenied", true).put("systemDenialClicked", true)
                .put("cancelPreservedIntent", true).put("denialPreservedIntent", true)
                .put("videoOnlyExplicit", true).put("mutedRecordingChecked", true)
                .put("microphoneStillDenied", context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_DENIED)
            File(context.filesDir, "exports/microphone-permission-test.json").writeText(evidence.toString(2))
        }
    }
}
