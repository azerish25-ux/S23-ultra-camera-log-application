package com.s23log.probe

import android.Manifest
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.rule.GrantPermissionRule
import com.s23log.probe.core.AudioMode
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.time.Instant

/**
 * Explicit physical-lab entry point for P016.
 *
 * It is skipped unless the runner supplies -e p016Physical true. Emulator CI can
 * compile this class, but it cannot accidentally create an S23 qualification result.
 * The device side only preserves the exact capture and observations. Full decode,
 * timing-marker detection, cadence recomputation, and qualification happen later in
 * scripts/p016_physical_qualification.py.
 */
@RunWith(AndroidJUnit4::class)
class P016PhysicalQualificationTest {
    @get:Rule
    val permissions: GrantPermissionRule = GrantPermissionRule.grant(
        Manifest.permission.CAMERA,
        Manifest.permission.RECORD_AUDIO
    )

    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context: Context get() = instrumentation.targetContext
    private val arguments: Bundle get() = InstrumentationRegistry.getArguments()

    @Test
    fun captureFirstPhysicalQualificationSlice() {
        assumeTrue(
            "Physical P016 is opt-in and is never executed by emulator CI",
            arguments.getString("p016Physical") == "true"
        )
        val runId = P016PhysicalHarness.requireArgument(arguments, "p016RunId").also {
            require(it.matches(Regex("[A-Za-z0-9][A-Za-z0-9._-]{0,95}"))) { "Invalid P016 run id" }
        }
        require(P016PhysicalHarness.requireArgument(arguments, "p016MarkerProtocol") == P016PhysicalHarness.MARKER_PROTOCOL) {
            "Unexpected timing-marker protocol"
        }
        require(arguments.getString("p016MarkerReady") == "true") {
            "The operator must explicitly confirm that the marker display and speaker are ready"
        }
        require(Build.MANUFACTURER.equals("samsung", ignoreCase = true)) {
            "P016 requires a Samsung Galaxy S23 Ultra, got ${Build.MANUFACTURER} ${Build.MODEL}"
        }
        require(Build.MODEL.matches(Regex("SM-S918[A-Za-z0-9-]*", RegexOption.IGNORE_CASE))) {
            "P016 requires an SM-S918* Galaxy S23 Ultra, got ${Build.MODEL}"
        }
        require(BuildConfig.SOURCE_REVISION.matches(Regex("[0-9a-f]{40}"))) {
            "BuildConfig.SOURCE_REVISION must bind this APK to an exact commit"
        }

        val preferences = context.getSharedPreferences(P016PhysicalHarness.SETTINGS_NAME, Context.MODE_PRIVATE)
        val priorSettings = P016PhysicalHarness.snapshotPreferences(preferences)
        val selection = P016PhysicalHarness.selectConservativeRearMode(context)
        val previousReport = CaptureHistory.latest(context).report?.name
        var recordingStartUtc: String? = null
        var recordingEndUtc: String? = null
        val deviceBefore = P016PhysicalHarness.deviceSnapshot(context)

        try {
            CameraSettings.select(context, selection.target.key)
            CameraSettings.saveMode(context, selection.target.key, selection.mode.key)
            CameraSettings.saveAudio(context, AudioMode.MONO)

            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                P016PhysicalHarness.await(scenario, "live preview for the selected conservative rear mode") {
                    it.findViewById<TextView>(R.id.cameraStatus).text.toString().startsWith("Live preview") &&
                        it.findViewById<Button>(R.id.record).isEnabled
                }
                recordingStartUtc = Instant.now().toString()
                P016PhysicalHarness.click(scenario, R.id.record)
                P016PhysicalHarness.await(scenario, "physical recording session") {
                    it.findViewById<TextView>(R.id.cameraStatus).text.toString().startsWith("Recording ")
                }
                Thread.sleep(P016PhysicalHarness.RECORDING_HOLD_MS)
                P016PhysicalHarness.click(scenario, R.id.record)
                recordingEndUtc = Instant.now().toString()
                P016PhysicalHarness.await(scenario, "return to live preview after physical capture", 60) {
                    it.findViewById<TextView>(R.id.cameraStatus).text.toString().startsWith("Live preview")
                }
            }

            val completed = P016PhysicalHarness.awaitCompletedCapture(context, previousReport)
            val deviceAfter = P016PhysicalHarness.deviceSnapshot(context)
            val directory = P016PhysicalHarness.createBundleDirectory(context, runId)
            val mediaFile = File(directory, P016PhysicalHarness.MEDIA_NAME)
            val validationFile = File(directory, P016PhysicalHarness.VALIDATION_NAME)
            val attemptFile = File(directory, P016PhysicalHarness.ATTEMPT_NAME)
            val mediaIdentity = P016PhysicalHarness.copyMedia(context, completed.entry, mediaFile)
            completed.validationFile.copyTo(validationFile, overwrite = false)
            completed.attemptFile.copyTo(attemptFile, overwrite = false)
            val validationIdentity = P016PhysicalHarness.identity(validationFile)
            val attemptIdentity = P016PhysicalHarness.identity(attemptFile)

            val expectedMedia = completed.validation
                .getJSONObject("verification")
                .getJSONObject("mediaIdentity")
            require(expectedMedia.getString("algorithm") == "SHA-256")
            require(expectedMedia.getString("sha256") == mediaIdentity.sha256 &&
                expectedMedia.getLong("byteCount") == mediaIdentity.byteCount) {
                "Copied P016 media differs from the app's checked output"
            }

            val selectedMode = JSONObject(selection.mode.describe())
                .put("processing", selection.mode.processing.name)
            val manifest = JSONObject()
                .put("schemaVersion", 1)
                .put("kind", P016PhysicalHarness.BUNDLE_KIND)
                .put("phase", "P016")
                .put("caseIds", JSONArray((1..8).map { "TC-P016-%02d".format(it) }))
                .put("runId", runId)
                .put("sourceRevision", BuildConfig.SOURCE_REVISION)
                .put("recordingStartUtc", requireNotNull(recordingStartUtc))
                .put("recordingEndUtc", requireNotNull(recordingEndUtc))
                .put("deviceBefore", deviceBefore)
                .put("deviceAfter", deviceAfter)
                .put("route", JSONObject()
                    .put("key", selection.target.key)
                    .put("logicalId", selection.target.logicalId)
                    .put("physicalId", selection.target.physicalId ?: JSONObject.NULL)
                    .put("front", selection.target.front))
                .put("selectedMode", selectedMode)
                .put("catalogErrors", JSONArray(selection.catalogErrors))
                .put("markerProtocol", JSONObject()
                    .put("id", P016PhysicalHarness.MARKER_PROTOCOL)
                    .put("operatorConfirmedReady", true)
                    .put("expectedEventsSeconds", JSONArray(P016PhysicalHarness.MARKER_EVENTS_SECONDS))
                    .put("deviceStatus", "awaiting_host_detection"))
                .put("captureValidation", completed.validation)
                .put("recordingAttempt", completed.attempt)
                .put("files", JSONObject()
                    .put("media", P016PhysicalHarness.fileRecord(P016PhysicalHarness.MEDIA_NAME, mediaIdentity))
                    .put("recordingValidation", P016PhysicalHarness.fileRecord(P016PhysicalHarness.VALIDATION_NAME, validationIdentity))
                    .put("recordingAttempt", P016PhysicalHarness.fileRecord(P016PhysicalHarness.ATTEMPT_NAME, attemptIdentity)))
                .put("onDeviceAssessment", JSONObject()
                    .put("durationAtLeast60Seconds",
                        completed.validation.getJSONObject("verification").getLong("sampleSpanUs") >= 60_000_000L)
                    .put("oneAudioTrackRequestedAndObserved",
                        completed.validation.getJSONObject("verification").getBoolean("audioRequested") &&
                            completed.validation.getJSONObject("verification").getInt("audioTrackCount") == 1)
                    .put("firstVideoFrameDecoded",
                        completed.validation.getJSONObject("verification").getBoolean("firstSyncFrameDecoded"))
                    .put("firstAudioPcmDecoded",
                        completed.validation.getJSONObject("verification").getBoolean("firstAudioPcmDecoded"))
                    .put("fullDecodeVerified", false)
                    .put("markerEventsVerified", false)
                    .put("physicalConfigurationQualified", false)
                    .put("enduranceCertified", false)
                    .put("higherResolutionQualified", false)
                    .put("status", "pending_off_device_full_decode_and_marker_analysis"))
                .put("nonClaims", JSONArray(listOf(
                    "This single run is not endurance or unlimited recording certification.",
                    "It does not qualify higher-resolution modes.",
                    "It does not qualify sensor-derived Log.",
                    "It does not establish cinema-camera equivalence."
                )))
            P016PhysicalHarness.atomicWrite(
                File(directory, P016PhysicalHarness.MANIFEST_NAME),
                manifest.toString(2) + "\n"
            )

            instrumentation.sendStatus(0, Bundle().apply {
                putString("p016RunId", runId)
                putString("p016Bundle", directory.absolutePath)
                putString("p016Status", "pending_host_validation")
            })
            assertTrue(File(directory, P016PhysicalHarness.MANIFEST_NAME).isFile)
        } finally {
            P016PhysicalHarness.restorePreferences(preferences, priorSettings)
        }
    }
}
