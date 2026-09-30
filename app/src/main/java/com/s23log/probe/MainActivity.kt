package com.s23log.probe

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.ClipData
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ActivityInfo
import android.graphics.Matrix
import android.graphics.SurfaceTexture
import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.CaptureRequest
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.provider.Settings
import android.util.Size
import android.view.Surface
import android.view.TextureView
import android.view.View
import android.view.WindowManager
import android.widget.*
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.s23log.probe.camera.*
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.CapturePolicy
import com.s23log.probe.core.EngineState
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.diagnostics.ProbeStore
import com.s23log.probe.diagnostics.ModeEvidence
import com.s23log.probe.core.ModePlanning
import com.s23log.probe.core.ProcessingPath
import com.s23log.probe.core.MonitorTransform
import com.s23log.probe.storage.CaptureHistory
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.PendingMedia
import java.io.File
import java.util.Locale

class MainActivity : Activity(), CameraController.Listener, TextureView.SurfaceTextureListener {
    private lateinit var controller: CameraController
    private lateinit var texture: TextureView
    private lateinit var pages: ViewFlipper
    private val reports: ProbeStore get() = (application as S23Application).reports
    private var visible = false
    private var destroyed = false
    private var targets: List<CameraTarget> = emptyList()
    private var selected: CameraTarget? = null
    private var modes: List<RecordingMode> = emptyList()
    private var wbModes: List<Int> = emptyList()
    private var previewSize: Size? = null
    private var requestedKey: String? = null
    private var engineState = EngineState.CLOSED
    private var modeKey: String? = null
    private var bindingControls = false
    private var latestPlan: ModePlan? = null
    private var viewingTransform = MonitorTransform.SDR_TONEMAP
    private var manualApplied = false
    private var audioMode = AudioMode.MONO
    private var audioFailure: String? = null
    private var resourceProblem: String? = null
    private var preRecordingOrientation: Int? = null
    private var permissionAction: (() -> Unit)? = null
    private val observer: (ProbeStore.State) -> Unit = { state ->
        text(R.id.status).text = state.message
        if (text(R.id.report).text.toString() != state.text) text(R.id.report).text = state.text
        button(R.id.runProbe).isEnabled = !state.running
        button(R.id.shareReport).isEnabled = state.shareable && !state.running
    }
    private fun text(id: Int): TextView = findViewById(id)
    private fun button(id: Int): Button = findViewById(id)
    private fun spinner(id: Int): Spinner = findViewById(id)
    private fun toggle(id: Int): CompoundButton = findViewById(id)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (savedInstanceState?.containsKey("preRecordingOrientation") == true)
            preRecordingOrientation = savedInstanceState.getInt("preRecordingOrientation")
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContentView(R.layout.activity_main)
        val root = findViewById<View>(R.id.root)
        val padding = (8 * resources.displayMetrics.density).toInt()
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            val ime = insets.getInsets(WindowInsetsCompat.Type.ime())
            view.setPadding(padding + bars.left, padding + bars.top, padding + bars.right, padding + maxOf(bars.bottom, ime.bottom))
            insets
        }
        pages = findViewById(R.id.pages)
        pages.displayedChild = savedInstanceState?.getInt("page", 0) ?: 0
        texture = findViewById(R.id.preview)
        texture.surfaceTextureListener = this
        controller = CameraController(this, this)
        audioMode = CameraSettings.audio(this)
        button(R.id.audioMode).setOnClickListener { chooseAudioMode() }
        button(R.id.cameraTab).setOnClickListener { pages.displayedChild = 0; maybeOpen() }
        button(R.id.diagnosticsTab).setOnClickListener { pages.displayedChild = 1; requestedKey = null; controller.close() }
        button(R.id.enableCamera).setOnClickListener { withCameraPermission { requestedKey = null; controller.discover() } }
        button(R.id.runProbe).setOnClickListener { withCameraPermission { reports.start() } }
        button(R.id.shareReport).setOnClickListener {
            reports.export { result ->
                if (!destroyed && visible) result.onSuccess { files -> shareFiles(files, "application/octet-stream") }
                    .onFailure { text(R.id.status).text = "Report export failed: ${it.message}. The scan is retained." }
            }
        }
        spinner(R.id.cameraSelector).onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val target = targets.getOrNull(position) ?: return
                if (target.key != selected?.key) { selected = target; requestedKey = null; maybeOpen() }
            }
        }
        spinner(R.id.modeSelector).onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                // Adapter/layout callbacks may arrive after a newer selection was bound.
                if (parent?.selectedItemPosition != position) return
                val mode = modes.getOrNull(position) ?: return
                if (!bindingControls && mode.key != modeKey && engineState == EngineState.PREVIEW) {
                    // Close the UI's ready window immediately, before the camera-thread hop.
                    onState(EngineState.OPENING, "Matching preview to ${mode.label}…")
                    controller.selectMode(mode)
                }
            }
        }
        button(R.id.recoverCaptures).setOnClickListener { showRecovery() }
        button(R.id.captureLibrary).setOnClickListener { startActivity(Intent(this, CaptureLibraryActivity::class.java)) }
        button(R.id.openControls).setOnClickListener {
            val panel = findViewById<View>(R.id.controlsPanel)
            panel.visibility = if (panel.visibility == View.VISIBLE) View.GONE else View.VISIBLE
        }
        button(R.id.closeControls).setOnClickListener { findViewById<View>(R.id.controlsPanel).visibility = View.GONE }
        button(R.id.modeDetails).setOnClickListener { showModeEvidence() }
        button(R.id.monitorTransform).setOnClickListener {
            viewingTransform = if (viewingTransform == MonitorTransform.SDR_TONEMAP) MonitorTransform.HLG_SIGNAL else MonitorTransform.SDR_TONEMAP
            controller.setMonitor(viewingTransform); updateEnabled()
        }
        button(R.id.testMode).setOnClickListener {
            val mode = modes.firstOrNull { it.key == modeKey } ?: return@setOnClickListener
            AlertDialog.Builder(this).setTitle(R.string.test_title).setMessage(getString(R.string.test_explanation, mode.label, audioLabel(audioMode)))
                .setNegativeButton(R.string.cancel, null).setPositiveButton(R.string.test_start) { _, _ ->
                    if (modeKey == mode.key && ModePlanning.recordingAllowed(engineState, mode, manualApplied)) {
                        findViewById<View>(R.id.controlsPanel).visibility = View.GONE
                        requestRecording(mode, 5)
                    }
                }.show()
        }
        button(R.id.record).setOnClickListener {
            if (engineState == EngineState.RECORDING || engineState == EngineState.STARTING) controller.stopRecording()
            else modes.firstOrNull { it.key == modeKey }?.let { mode ->
                if (ModePlanning.recordingAllowed(engineState, mode, manualApplied)) {
                    requestRecording(mode, null)
                }
            }
        }
        button(R.id.rawOne).setOnClickListener { controller.captureRaw(1) }
        button(R.id.rawFive).setOnClickListener { controller.captureRaw(5) }
        button(R.id.applyControls).setOnClickListener { applyControls() }
        toggle(R.id.manualExposure).setOnCheckedChangeListener { _, _ -> updateEnabled() }
        toggle(R.id.manualFocus).setOnCheckedChangeListener { _, _ -> updateEnabled() }
        button(R.id.shareCapture).setOnClickListener {
            val entry = CaptureHistory.latest(this)
            if (entry.uris.isNotEmpty()) shareUris(entry.uris, if (entry.uris.first().toString().contains("video")) "video/mp4" else "application/octet-stream")
        }
        button(R.id.shareValidation).setOnClickListener { CaptureHistory.latest(this).report?.let { shareFiles(listOf(it), "application/json") } }
        onState(EngineState.CLOSED, "Enable camera to begin. Recording modes are verified only after capture.")
    }
    override fun onStart() { super.onStart(); reports.observe(observer) }
    override fun onResume() {
        super.onResume()
        visible = true
        restoreCapture()
        renderAudioIdle()
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            if (targets.isEmpty()) controller.discover() else maybeOpen()
        }
    }
    override fun onStop() {
        visible = false
        requestedKey = null
        controller.close()
        reports.remove(observer)
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        super.onStop()
    }
    override fun onDestroy() { destroyed = true; controller.release(); super.onDestroy() }
    override fun onSaveInstanceState(outState: Bundle) {
        outState.putInt("page", pages.displayedChild)
        preRecordingOrientation?.let { outState.putInt("preRecordingOrientation", it) }
        super.onSaveInstanceState(outState)
    }
    private fun withCameraPermission(action: () -> Unit) {
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) { action(); return }
        val prefs = getPreferences(MODE_PRIVATE)
        if (prefs.getBoolean("permissionAsked", false) && !shouldShowRequestPermissionRationale(Manifest.permission.CAMERA)) {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
            return
        }
        permissionAction = action
        prefs.edit().putBoolean("permissionAsked", true).apply()
        requestPermissions(arrayOf(Manifest.permission.CAMERA), 1001)
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1002) {
            audioFailure = if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) null else getString(R.string.audio_denied)
            renderAudioIdle()
            text(R.id.cameraStatus).setText(if (audioFailure == null) R.string.audio_granted else R.string.audio_denied)
            return // Permission grants never resurrect stale recording requests.
        }
        if (requestCode != 1001) return
        val action = permissionAction
        permissionAction = null
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) { action?.invoke(); controller.discover() }
        else { text(R.id.status).text = "Camera permission denied. Enable it to run the complete probe."; onState(EngineState.CLOSED, "Camera permission denied. Enable camera to retry or open Settings.") }
    }
    private fun maybeOpen() {
        val target = selected ?: return
        val surface = texture.surfaceTexture ?: return
        if (!visible || pages.displayedChild != 0 || !texture.isAvailable || checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) return
        if (requestedKey == target.key) return
        requestedKey = target.key
        controller.open(target, surface, displayDegrees(), CameraSettings.mode(this, target.key), CameraSettings.controls(this, target.key))
    }
    @Suppress("DEPRECATION") private fun displayDegrees(): Int {
        val rotation = if (Build.VERSION.SDK_INT >= 30) display?.rotation ?: Surface.ROTATION_0 else windowManager.defaultDisplay.rotation
        return when (rotation) { Surface.ROTATION_90 -> 90; Surface.ROTATION_180 -> 180; Surface.ROTATION_270 -> 270; else -> 0 }
    }
    private fun setItems(spinner: Spinner, labels: List<String>) {
        spinner.adapter = ArrayAdapter(this, R.layout.selector_item, labels).apply { setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
    }
    override fun onCatalog(result: CatalogResult) {
        if (destroyed) return
        val previous = selected?.key ?: CameraSettings.camera(this)
        targets = result.targets
        selected = targets.firstOrNull { it.key == previous } ?: targets.firstOrNull()
        setItems(spinner(R.id.cameraSelector), targets.map { it.label })
        if (selected != null) spinner(R.id.cameraSelector).setSelection(targets.indexOf(selected))
        if (targets.isEmpty()) onState(EngineState.ERROR, "No accessible camera. ${result.errors.joinToString()}")
        else maybeOpen()
    }
    override fun onReady(target: CameraTarget, previewSize: Size, plan: ModePlan, mode: RecordingMode?) {
        if (target.key != selected?.key || destroyed) return
        this.previewSize = previewSize
        modes = plan.modes
        latestPlan = plan
        manualApplied = false
        bindingControls = true
        modeKey = mode?.key
        setItems(spinner(R.id.modeSelector), modes.map { it.label })
        if (mode != null) spinner(R.id.modeSelector).setSelection(modes.indexOf(mode))
        CameraSettings.select(this, target.key)
        CameraSettings.saveMode(this, target.key, modeKey)
        text(R.id.planNotes).text = plan.notes.joinToString("\n")
        val c = target.characteristics
        wbModes = target.wbModes
        setItems(spinner(R.id.wbSelector), wbModes.map(::wbName))
        renderControls(CameraSettings.controls(this, target.key))
        bindingControls = false
        val isoRange = c[C.SENSOR_INFO_SENSITIVITY_RANGE]
        text(R.id.limits).text = "ISO ${isoRange ?: "unreported"}; shutter ns ${c[C.SENSOR_INFO_EXPOSURE_TIME_RANGE] ?: "unreported"}; focus 0…${target.minFocus} diopters. Video shutter is bounded by its frame interval."
        transformPreview()
        updateEnabled()
    }
    override fun onModeChanged(cameraKey: String, mode: RecordingMode, previewSize: Size) {
        if (destroyed || cameraKey != selected?.key || modes.none { it.key == mode.key }) return
        modeKey = mode.key
        this.previewSize = previewSize
        selected?.let { CameraSettings.saveMode(this, it.key, mode.key) }
        spinner(R.id.modeSelector).setSelection(modes.indexOfFirst { it.key == mode.key })
        transformPreview()
    }
    override fun onControlsChanged(cameraKey: String, controls: CameraControls) {
        if (destroyed || cameraKey != selected?.key) return
        manualApplied = controls.manualExposure
        renderControls(controls)
        selected?.let { CameraSettings.saveControls(this, it.key, controls) }
        updateEnabled()
    }
    private fun renderControls(controls: CameraControls) {
        toggle(R.id.manualExposure).isChecked = controls.manualExposure
        toggle(R.id.manualFocus).isChecked = controls.focusDiopters != null
        toggle(R.id.wbLock).isChecked = controls.wbLock
        text(R.id.isoInput).text = controls.iso.toString()
        text(R.id.shutterInput).text = String.format(Locale.US, "%.6f", controls.exposureNs / 1_000_000.0)
        text(R.id.focusInput).text = (controls.focusDiopters ?: 0f).toString()
        wbModes.indexOf(controls.wbMode).takeIf { it >= 0 }?.let { spinner(R.id.wbSelector).setSelection(it) }
    }
    private fun showModeEvidence() {
        val target = selected ?: return
        val plan = latestPlan ?: return
        val text = TextView(this).apply {
            setPadding(24, 16, 24, 16)
            textSize = 12f
            setTextIsSelectable(true)
            text = ModeEvidence.report(target, plan).toString(2)
        }
        val scroll = ScrollView(this).apply { addView(text) }
        AlertDialog.Builder(this).setTitle(R.string.mode_evidence_title).setView(scroll)
            .setNegativeButton(R.string.close, null).setPositiveButton(R.string.mode_export) { _, _ ->
                ModeEvidence.export(this, target, plan) { result ->
                    if (!destroyed && visible) result.onSuccess { shareFiles(listOf(it), "application/json") }
                        .onFailure { Toast.makeText(this, "Mode export failed: ${it.message}", Toast.LENGTH_LONG).show() }
                }
            }.show()
    }
    private fun showRecovery() {
        val entries = PendingMedia.recoverable(this)
        if (entries.isEmpty()) {
            AlertDialog.Builder(this).setTitle("Recover captures").setMessage("No retained video files. Recovery clips are private and may be incomplete or unverified.").setPositiveButton("Close", null).show()
            return
        }
        AlertDialog.Builder(this).setTitle("Retained footage — not verified")
            .setItems(entries.map { "${it.file.name} (${it.file.length() / 1024} KiB)" }.toTypedArray()) { _, index ->
                val entry = entries[index]
                AlertDialog.Builder(this).setTitle("Unverified recovery clip").setMessage(entry.reason + "\nExport this file for inspection or recovery. It has not been published as a verified recording.")
                    .setPositiveButton("Export") { _, _ -> shareUris(listOf(entry.uri), "video/mp4") }
                    .setNeutralButton("Keep", null)
                    .setNegativeButton("Delete…") { _, _ ->
                        AlertDialog.Builder(this).setTitle("Permanently delete recovery clip?").setMessage(entry.file.name)
                            .setNegativeButton("Keep", null).setPositiveButton("Delete") { _, _ ->
                                runCatching { PendingMedia.discardRecovery(this, entry) }
                                    .onFailure { Toast.makeText(this, it.message, Toast.LENGTH_LONG).show() }
                            }.show()
                    }.show()
            }.setNegativeButton("Close", null).show()
    }
    override fun onState(state: EngineState, message: String) {
        if (destroyed) return
        val previous = engineState
        engineState = state
        if (state in setOf(EngineState.STARTING, EngineState.RECORDING, EngineState.STOPPING)) {
            if (preRecordingOrientation == null) {
                preRecordingOrientation = requestedOrientation
                requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LOCKED
            }
        } else preRecordingOrientation?.let {
            preRecordingOrientation = null
            requestedOrientation = it
        }
        if (state in setOf(EngineState.PREVIEW, EngineState.CLOSED, EngineState.ERROR))
            text(R.id.resourceStatus).text = resourceProblem ?: getString(R.string.resource_idle)
        if (state == EngineState.OPENING || state == EngineState.CLOSED || state == EngineState.ERROR) manualApplied = false
        val clock = findViewById<Chronometer>(R.id.recordingClock)
        if (state == EngineState.RECORDING && previous != state) { clock.base = SystemClock.elapsedRealtime(); clock.start() }
        else if (state != EngineState.RECORDING) { clock.stop(); if (state == EngineState.PREVIEW || state == EngineState.CLOSED) clock.base = SystemClock.elapsedRealtime() }
        text(R.id.cameraStatus).text = message
        val mode = modes.getOrNull(spinner(R.id.modeSelector).selectedItemPosition)
        val showOverlay = state !in setOf(EngineState.PREVIEW, EngineState.RECORDING) ||
            (state == EngineState.RECORDING && mode?.previewDuringRecording == false)
        text(R.id.previewOverlay).visibility = if (showOverlay) View.VISIBLE else View.GONE
        text(R.id.previewOverlay).text = message
        if (state == EngineState.STARTING || state == EngineState.RECORDING) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        if (state != EngineState.RECORDING) renderAudioIdle()
        updateEnabled()
    }
    override fun onApplied(values: Map<String, Any?>) {
        if (destroyed || !visible) return
        val wasManual = manualApplied
        manualApplied = values["aeMode"] == CaptureRequest.CONTROL_AE_MODE_OFF
        if (wasManual != manualApplied) updateEnabled()
        val ms = (values["exposureNs"] as? Long)?.let { String.format(Locale.US, "%.3f", it / 1_000_000.0) } ?: "?"
        text(R.id.applied).text = "APPLIED · ${values["nominalFps"] ?: "auto"} fps target · ISO ${values["iso"] ?: "?"} · ${ms} ms · focus ${values["focusDiopters"] ?: "?"} dpt · WB ${values["awbMode"] ?: "?"}"
    }
    override fun onVideo(outcome: SurfaceRecorder.Outcome) {
        if (outcome.audioError != null) audioFailure = "Microphone error: ${outcome.audioError}"
        restoreCapture(); renderAudioIdle()
    }
    override fun onRaw(outcome: RawCapture.Outcome) { restoreCapture() }
    private fun restoreCapture() {
        if (destroyed) return
        val entry = CaptureHistory.latest(this)
        text(R.id.captureResult).text = entry.message
        button(R.id.shareCapture).isEnabled = entry.uris.isNotEmpty()
        button(R.id.shareValidation).isEnabled = entry.report != null
    }
    private fun updateEnabled() {
        val preview = engineState == EngineState.PREVIEW
        val recording = engineState == EngineState.RECORDING
        val idle = CapturePolicy.canChangeCamera(engineState)
        spinner(R.id.cameraSelector).isEnabled = idle
        spinner(R.id.modeSelector).isEnabled = preview && modes.isNotEmpty()
        val mode = modes.firstOrNull { it.key == modeKey }
        val processed = mode?.processing == ProcessingPath.GPU_HLG10
        button(R.id.monitorTransform).isEnabled = processed && (preview || recording)
        button(R.id.monitorTransform).setText(if (viewingTransform == MonitorTransform.SDR_TONEMAP) R.string.monitor_sdr else R.string.monitor_signal)
        text(R.id.colourStatus).setText(if (processed) R.string.colour_gpu else R.string.colour_direct)
        val canRecord = ModePlanning.recordingAllowed(engineState, mode, manualApplied)
        button(R.id.record).isEnabled = canRecord || recording || engineState == EngineState.STARTING
        button(R.id.testMode).isEnabled = canRecord
        button(R.id.audioMode).isEnabled = idle
        button(R.id.modeDetails).isEnabled = idle && latestPlan != null
        text(R.id.modeEvidence).setText(if (mode?.ratePlan?.requiresManual == true && !manualApplied) R.string.manual_timing_required else R.string.advertised_only)
        button(R.id.record).setText(if (recording || engineState == EngineState.STARTING) R.string.stop_recording else R.string.start_recording)
        button(R.id.recoverCaptures).isEnabled = idle
        button(R.id.captureLibrary).isEnabled = idle
        button(R.id.diagnosticsTab).isEnabled = idle
        button(R.id.cameraTab).isEnabled = idle
        button(R.id.enableCamera).isEnabled = idle
        button(R.id.enableCamera).visibility = if (engineState == EngineState.CLOSED || engineState == EngineState.ERROR) View.VISIBLE else View.GONE
        val rawAvailable = runCatching { selected?.rawSize != null }.getOrDefault(false)
        button(R.id.rawOne).isEnabled = preview && rawAvailable
        button(R.id.rawFive).isEnabled = preview && rawAvailable
        val controls = preview || recording
        toggle(R.id.manualExposure).isEnabled = controls && selected?.manualSensor == true
        text(R.id.isoInput).isEnabled = controls && toggle(R.id.manualExposure).isChecked
        text(R.id.shutterInput).isEnabled = controls && toggle(R.id.manualExposure).isChecked
        toggle(R.id.manualFocus).isEnabled = controls && selected?.manualFocus == true
        text(R.id.focusInput).isEnabled = controls && toggle(R.id.manualFocus).isChecked
        spinner(R.id.wbSelector).isEnabled = controls && wbModes.isNotEmpty()
        toggle(R.id.wbLock).isEnabled = controls && selected?.wbLockAvailable == true
        button(R.id.applyControls).isEnabled = controls
    }
    private fun audioLabel(mode: AudioMode): String = getString(when (mode) {
        AudioMode.OFF -> R.string.audio_video_only
        AudioMode.MONO -> R.string.audio_mono
        AudioMode.STEREO -> R.string.audio_stereo
    })
    private fun chooseAudioMode() {
        if (!CapturePolicy.canChangeCamera(engineState)) return
        val choices = listOf(AudioMode.MONO, AudioMode.STEREO, AudioMode.OFF)
        AlertDialog.Builder(this).setTitle(R.string.audio_choose)
            .setSingleChoiceItems(choices.map(::audioLabel).toTypedArray(), choices.indexOf(audioMode)) { dialog, index ->
                if (CapturePolicy.canChangeCamera(engineState)) {
                    audioMode = choices[index]; CameraSettings.saveAudio(this, audioMode)
                    audioFailure = null; renderAudioIdle()
                }
                dialog.dismiss()
            }.setNegativeButton(R.string.cancel, null).show()
    }
    private fun requestRecording(mode: RecordingMode, testSeconds: Int?) {
        if (!visible || pages.displayedChild != 0 || mode.key != modeKey || !ModePlanning.recordingAllowed(engineState, mode, manualApplied)) return
        if (audioMode.enabled && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            val previouslyAsked = getPreferences(MODE_PRIVATE).getBoolean("audioPermissionAsked", false)
            val openSettings = previouslyAsked && !shouldShowRequestPermissionRationale(Manifest.permission.RECORD_AUDIO)
            AlertDialog.Builder(this).setTitle(R.string.audio_permission_title).setMessage(R.string.audio_permission_body)
                .setPositiveButton(if (openSettings) R.string.audio_settings else R.string.audio_allow) { _, _ ->
                    if (openSettings) startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
                    else {
                        getPreferences(MODE_PRIVATE).edit().putBoolean("audioPermissionAsked", true).apply()
                        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 1002)
                    }
                }.setNeutralButton(R.string.audio_video_only_action) { _, _ ->
                    if (CapturePolicy.canChangeCamera(engineState)) {
                        audioMode = AudioMode.OFF; CameraSettings.saveAudio(this, audioMode); audioFailure = null; renderAudioIdle()
                    }
                }.setNegativeButton(R.string.cancel, null).show()
            return
        }
        audioFailure = null
        onState(EngineState.STARTING, "Starting camera${if (audioMode.enabled) " and microphone" else ""}…")
        controller.startRecording(mode, testSeconds, audioMode)
    }
    private fun renderAudioIdle() {
        if (destroyed) return
        button(R.id.audioMode).setText(if (audioMode.enabled) R.string.audio_mic else R.string.audio_off)
        button(R.id.audioMode).contentDescription = audioLabel(audioMode)
        text(R.id.audioStatus).text = audioFailure ?: when {
            !audioMode.enabled -> getString(R.string.audio_video_only)
            engineState == EngineState.STARTING -> "Waiting for microphone samples"
            engineState == EngineState.STOPPING -> "Finalizing audio + video"
            checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED -> "${audioMode.name.lowercase()} · microphone permission needed"
            else -> "${audioMode.name.lowercase()} · 48 kHz · idle"
        }
        findViewById<ProgressBar>(R.id.audioLeft).progress = 0
        findViewById<ProgressBar>(R.id.audioRight).apply { progress = 0; visibility = if (audioMode == AudioMode.STEREO) View.VISIBLE else View.GONE }
    }
    override fun onAudioMeter(meter: AudioCapture.Meter) {
        if (destroyed || !visible || engineState !in setOf(EngineState.STARTING, EngineState.RECORDING)) return
        val clipped = meter.levels.any { it.clipped }
        val peak = meter.levels.maxOfOrNull { it.peakDb } ?: -96.0
        val uncertainty = when {
            meter.timingStatus != "no_discontinuity_observed" -> " · ${meter.timingStatus.replace('_', ' ')}"
            Build.VERSION.SDK_INT < 33 -> " · legacy clock unverified"
            else -> "" // Never label packet timing as physical lip-sync certification.
        }
        text(R.id.audioStatus).text = "${if (clipped) "CLIPPING · " else ""}${audioMode.name.lowercase()} · 48 kHz · ${String.format(Locale.US, "%.0f", peak)} dBFS$uncertainty"
        text(R.id.audioStatus).contentDescription = "${meter.route}. ${text(R.id.audioStatus).text}"
        findViewById<ProgressBar>(R.id.audioLeft).progress = meter.levels.getOrNull(0)?.meter ?: 0
        findViewById<ProgressBar>(R.id.audioRight).progress = meter.levels.getOrNull(1)?.meter ?: 0
    }
    override fun onAudioError(message: String) { audioFailure = message; renderAudioIdle() }
    override fun onResources(snapshot: RecordingResources.Snapshot) {
        if (destroyed || !visible) return
        resourceProblem = snapshot.decision.stopReason?.let { RecordingResources.stopMessage(this, it) }
        if (resourceProblem != null) { text(R.id.resourceStatus).text = resourceProblem; return }
        val remaining = snapshot.decision.remainingSecondsEstimate?.let { getString(R.string.resource_seconds, it) }
            ?: getString(R.string.resource_unknown)
        val thermal = snapshot.thermalStatus?.let { resources.getStringArray(R.array.resource_thermal_levels).getOrNull(it) }
            ?.let { getString(R.string.resource_thermal_level, it) }
            ?: getString(R.string.resource_thermal_unknown)
        text(R.id.resourceStatus).text = "$remaining · $thermal"
    }
    private fun applyControls() {
        try {
            val iso = text(R.id.isoInput).text.toString().toInt()
            val ms = text(R.id.shutterInput).text.toString().toDouble()
            require(iso > 0 && ms.isFinite() && ms > 0 && ms <= 60_000) { "Enter a positive ISO and shutter of at most 60,000 ms" }
            val focus = if (toggle(R.id.manualFocus).isChecked) text(R.id.focusInput).text.toString().toFloat().also { require(it.isFinite() && it >= 0) } else null
            controller.applyControls(CameraControls(toggle(R.id.manualExposure).isChecked, iso, (ms * 1_000_000).toLong(), focus,
                wbModes.getOrNull(spinner(R.id.wbSelector).selectedItemPosition) ?: CaptureRequest.CONTROL_AWB_MODE_AUTO,
                toggle(R.id.wbLock).isChecked))
        } catch (e: Exception) { text(R.id.cameraStatus).text = "Invalid controls: ${e.message}" }
    }
    private fun wbName(mode: Int): String = when (mode) {
        1 -> "Auto"; 2 -> "Incandescent"; 3 -> "Fluorescent"; 4 -> "Warm fluorescent"; 5 -> "Daylight"; 6 -> "Cloudy daylight"; 7 -> "Twilight"; 8 -> "Shade"; else -> "Preset $mode"
    }
    private fun shareFiles(files: List<File>, mime: String) {
        try { shareUris(files.map { FileProvider.getUriForFile(this, "$packageName.files", it) }, mime) }
        catch (e: Exception) { Toast.makeText(this, "Could not export files: ${e.message}", Toast.LENGTH_LONG).show() }
    }
    private fun shareUris(uris: List<Uri>, mime: String) {
        if (uris.isEmpty()) return
        try {
            val intent = Intent(if (uris.size == 1) Intent.ACTION_SEND else Intent.ACTION_SEND_MULTIPLE).apply {
                type = mime
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                if (uris.size == 1) putExtra(Intent.EXTRA_STREAM, uris.first()) else putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(uris))
                clipData = ClipData.newUri(contentResolver, "S23Log", uris.first()).also { clip -> uris.drop(1).forEach { clip.addItem(ClipData.Item(it)) } }
            }
            startActivity(Intent.createChooser(intent, "Share S23Log files"))
        } catch (e: Exception) { Toast.makeText(this, "Could not share: ${e.message}", Toast.LENGTH_LONG).show() }
    }
    private fun transformPreview() {
        val size = previewSize ?: return
        val target = selected ?: return
        val w = texture.width.toFloat()
        val h = texture.height.toFloat()
        if (w <= 0 || h <= 0) return
        val angle = CapturePolicy.orientation(target.characteristics[C.SENSOR_ORIENTATION] ?: 0, displayDegrees(), target.front)
        val rotated = angle % 180 != 0
        val scale = minOf(w / (if (rotated) size.height else size.width), h / (if (rotated) size.width else size.height))
        texture.setTransform(Matrix().apply {
            setScale(size.width / w, size.height / h)
            postTranslate(-size.width / 2f, -size.height / 2f)
            postRotate(angle.toFloat())
            postScale(scale, scale)
            postTranslate(w / 2f, h / 2f)
            if (target.front) postScale(-1f, 1f, w / 2f, h / 2f)
        })
    }
    override fun onSurfaceTextureAvailable(surface: SurfaceTexture, width: Int, height: Int) { requestedKey = null; maybeOpen(); transformPreview() }
    override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, width: Int, height: Int) { transformPreview() }
    override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean { requestedKey = null; controller.detachTexture(surface); return false }
    override fun onSurfaceTextureUpdated(surface: SurfaceTexture) = Unit
}
