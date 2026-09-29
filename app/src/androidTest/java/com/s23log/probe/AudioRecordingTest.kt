package com.s23log.probe

import android.Manifest
import android.content.Context
import android.widget.Button
import android.widget.TextView
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.core.AudioMode
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Uses real AudioRecord/AAC/Camera2. A silent emulator is not a physical lip-sync measurement. */
@RunWith(AndroidJUnit4::class)
class AudioRecordingTest {
    @get:Rule val permissions: GrantPermissionRule = GrantPermissionRule.grant(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
    private val context: Context get() = InstrumentationRegistry.getInstrumentation().targetContext
    @Before fun microphoneMode() { CameraSettings.saveAudio(context, AudioMode.MONO) }
    private fun await(scenario: ActivityScenario<MainActivity>, label: String, predicate: (MainActivity) -> Boolean) {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(45)
        val accepted = AtomicBoolean()
        while (System.nanoTime() < deadline) {
            scenario.onActivity { accepted.set(predicate(it)) }
            if (accepted.get()) return
            Thread.sleep(150)
        }
        var status = ""
        scenario.onActivity { status = "${it.findViewById<TextView>(R.id.cameraStatus).text} / ${it.findViewById<TextView>(R.id.audioStatus).text}" }
        fail("$label: $status")
    }
    private fun ready(scenario: ActivityScenario<MainActivity>) = await(scenario, "Live preview") {
        it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Live preview") && it.findViewById<Button>(R.id.record).isEnabled
    }
    private fun click(scenario: ActivityScenario<MainActivity>, id: Int) {
        scenario.onActivity { assertTrue(it.findViewById<Button>(id).isEnabled); it.findViewById<Button>(id).performClick() }
    }
    private fun begin(scenario: ActivityScenario<MainActivity>) {
        ready(scenario); click(scenario, R.id.record)
        await(scenario, "Audio/video first samples acknowledged") {
            it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Recording ") && it.findViewById<TextView>(R.id.cameraStatus).text.contains("AAC")
        }
        scenario.onActivity { assertFalse("Audio settings cannot change mid-take", it.findViewById<Button>(R.id.audioMode).isEnabled) }
    }
    private fun output(previous: String?, channels: Int = 1, minSpanUs: Long = 2_000_000): JSONObject {
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(40)
        while (System.nanoTime() < deadline) {
            val entry = CaptureHistory.latest(context)
            if (entry.report != null && entry.report.name != previous) {
                val json = JSONObject(entry.report.readText())
                assertEquals(json.toString(), "checked", json.getString("status"))
                assertFalse(json.getBoolean("videoOnly")); assertFalse(json.getBoolean("physicalLipSyncVerified"))
                assertTrue(json.getJSONArray("stages").toString().contains("av_samples_written"))
                val verification = json.getJSONObject("verification")
                assertTrue(verification.getBoolean("firstAudioPcmDecoded"))
                assertTrue(verification.getLong("sampleSpanUs") >= minSpanUs)
                assertEquals(1, verification.getInt("audioTrackCount"))
                val audio = verification.getJSONObject("audio")
                assertEquals("AAC-LC", audio.getString("profile")); assertEquals(48000, audio.getInt("sampleRate")); assertEquals(channels, audio.getInt("channels"))
                assertTrue(audio.getLong("samples") >= 2)
                assertTrue(json.getJSONObject("audio").getBoolean("builtInRouteConfirmed"))
                assertTrue(json.getJSONObject("audio").getJSONObject("clock").getString("source") != "unavailable")
                assertFalse(verification.getBoolean("physicalLipSyncVerified"))
                return json
            }
            Thread.sleep(150)
        }
        error("No completed audio recording: ${CaptureHistory.latest(context).message}")
    }
    @Test fun threeAudioTakesReleaseTheMicrophoneBetweenRecordings() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            repeat(3) {
                val previous = CaptureHistory.latest(context).report?.name
                begin(scenario); Thread.sleep(4000); click(scenario, R.id.record); output(previous); ready(scenario)
            }
        }
    }
    @Test fun audioVideoTrackTimingSurvivesSixtySeconds() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            val previous = CaptureHistory.latest(context).report?.name
            begin(scenario); Thread.sleep(65_000); click(scenario, R.id.record)
            val json = output(previous, minSpanUs = 60_000_000)
            assertTrue(json.getJSONObject("verification").getJSONObject("audio").getLong("packetSpanUs") >= 60_000_000)
            ready(scenario)
        }
    }
    @Test fun leavingActivityDrainsBothTracks() {
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            val previous = CaptureHistory.latest(context).report?.name
            begin(scenario); Thread.sleep(4000); scenario.moveToState(Lifecycle.State.CREATED)
            output(previous); scenario.moveToState(Lifecycle.State.RESUMED); ready(scenario)
        }
    }
    @Test fun stereoSelectionProducesTwoChannelsRatherThanSilentlyDownmixing() {
        CameraSettings.saveAudio(context, AudioMode.STEREO)
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            val previous = CaptureHistory.latest(context).report?.name
            begin(scenario); Thread.sleep(4000); click(scenario, R.id.record); output(previous, channels = 2)
        }
    }
    @Test fun deniedMicrophoneDoesNotSilentlyRecordVideoOnly() {
        val automation = InstrumentationRegistry.getInstrumentation().uiAutomation
        fun appop(mode: String) { automation.executeShellCommand("appops set ${context.packageName} RECORD_AUDIO $mode").use { descriptor ->
            android.os.ParcelFileDescriptor.AutoCloseInputStream(descriptor).use { it.readBytes() }
        } }
        try {
            appop("deny")
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                ready(scenario)
                val previous = CaptureHistory.latest(context).report?.name
                click(scenario, R.id.record)
                await(scenario, "Microphone denial reported without a silent take") {
                    it.findViewById<TextView>(R.id.audioStatus).text.contains("failed", ignoreCase = true) ||
                        automation.rootInActiveWindow?.findAccessibilityNodeInfosByText("Record with microphone audio?")?.isNotEmpty() == true
                }
                scenario.onActivity { assertFalse(it.findViewById<TextView>(R.id.cameraStatus).text.startsWith("Recording ")) }
                assertEquals(previous, CaptureHistory.latest(context).report?.name)
            }
        } finally { appop("allow") }
    }
}
