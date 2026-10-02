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
import com.s23log.probe.core.PreviewAid
import com.s23log.probe.core.BitratePreset
import com.s23log.probe.core.BitratePolicy
import com.s23log.probe.storage.CaptureHistory
import com.s23log.probe.storage.CameraSettings
import com.s23log.probe.storage.PendingMedia
import com.s23log.probe.storage.ColourReferenceStore
import java.io.File
import java.util.Locale

class MainActivity : Activity(), CameraController.Listener, TextureView.SurfaceTextureListener {
    private lateinit var controller: CameraController
    private lateinit var texture: TextureView
    private lateinit var quickControls: QuickControls
    private lateinit var previewAids: PreviewAidsView
    private lateinit var pages: ViewFlipper
    private val reports: ProbeStore get() = (application as S23Application).reports
    private val colourReferences: ColourReferenceStore get() = (application as S23Application).colourReferences
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
    private var manualRequested = false
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
    private val colourObserver: (ColourReferenceStore.State) -> Unit = { state ->
        text(R.id.colourReferenceStatus).text = when {
            state.running -> getString(R.string.colour_reference_preparing)
            state.error != null -> getString(R.string.colour_reference_failed, state.error)
            state.files.isNotEmpty() -> getString(R.string.colour_reference_ready)
            else -> getString(R.string.colour_reference_scope)
        }
        button(R.id.colourReference).setText(if (state.files.isNotEmpty()) R.string.colour_reference_share else R.string.colour_reference_prepare)
        updateEnabled()
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
        texture.isOpaque = false // Aspect-fit padding must stay transparent for display analysis.
        previewAids = findViewById(R.id.previewAidsOverlay)
        texture.surfaceTextureListener = this
        controller = CameraController(this, this)
        quickControls = QuickControls(this)
        texture.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ ->
            val panel = findViewById<View>(R.id.controlsPanel)
            val desired = (texture.height * 0.65f).toInt().coerceAtLeast(1)
            if (panel.layoutParams.height != desired) panel.layoutParams = panel.layoutParams.apply { height = desired }
        }
        audioMode = CameraSettings.audio(this)
        button(R.id.audioMode).setOnClickListener { chooseAudioMode() }
        button(R.id.cameraTab).setOnClickListener { pages.displayedChild = 0; maybeOpen() }
        button(R.id.clipsTab).setOnClickListener { openClips() }
        button(R.id.diagnosticsTab).setOnClickListener { pages.displayedChild = 1; requestedKey = null; controller.close() }
        button(R.id.enableCamera).setOnClickListener { withCameraPermission { requestedKey = null; controller.discover() } }
        button(R.id.recordingAttempts).setOnClickListener { showRecordingAttempts() }
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
                selectCamera(target)
            }
        }
        spinner(R.id.modeSelector).onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                // Adapter/layout callbacks may arrive after a newer selection was bound.
                if (parent?.selectedItemPosition != position) return
                if (position == 0) {
                    modes.indexOfFirst { it.key == modeKey }.takeIf { it >= 0 }?.let { parent.setSelection(it + 1) }
                    return
                }
                val mode = modes.getOrNull(position - 1) ?: return
                if (!bindingControls && mode.key != modeKey && engineState == EngineState.PREVIEW) {
                    // Close the UI's ready window immediately, before the camera-thread hop.
                    onState(EngineState.OPENING, "Matching preview to ${mode.label}…")
                    controller.selectMode(mode)
                }
            }
        }
        button(R.id.recoverCaptures).setOnClickListener { showRecovery() }
        button(R.id.captureLibrary).setOnClickListener { openClips() }
        button(R.id.openControls).setOnClickListener {
            val panel = findViewById<View>(R.id.controlsPanel)
            if (panel.visibility != View.VISIBLE) showSettings(false)
            panel.visibility = if (panel.visibility == View.VISIBLE) View.GONE else View.VISIBLE
        }
        button(R.id.openSettings).setOnClickListener { showSettings(true) }
        button(R.id.backToManual).setOnClickListener { showSettings(false) }
        button(R.id.closeControls).setOnClickListener { findViewById<View>(R.id.controlsPanel).visibility = View.GONE }
        button(R.id.modeDetails).setOnClickListener { showModeEvidence() }
        button(R.id.previewAids).setOnClickListener { choosePreviewAids() }
        button(R.id.bitratePreset).setOnClickListener { chooseBitratePreset() }
        button(R.id.colourReference).setOnClickListener {
            val state = colourReferences.state
            if (state.files.isNotEmpty() && state.files.all { it.isFile }) shareFiles(state.files, "application/octet-stream")
            else colourReferences.prepare()
        }
        button(R.id.monitorTransform).setOnClickListener {
            viewingTransform = if (viewingTransform == MonitorTransform.SDR_TONEMAP) MonitorTransform.HLG_SIGNAL else MonitorTransform.SDR_TONEMAP
            controller.setMonitor(viewingTransform); updateEnabled()
        }
        button(R.id.testMode).setOnClickListener {
            val mode = modes.firstOrNull { it.key == modeKey } ?: return@setOnClickListener
            AlertDialog.Builder(this).setTitle(R.string.test_title).setMessage(getString(R.string.test_explanation, mode.label, audioLabel(audioMode)))
                .setNegativeButton(R.string.cancel, null).setPositiveButton(R.string.test_start) { _, _ ->
                    if (modeKey == mode.key && ModePlanning.recordingAllowed(engineState, mode, manualApplied, manualRequested)) {
                        findViewById<View>(R.id.controlsPanel).visibility = View.GONE
                        requestRecording(mode, 5)
                    }
                }.show()
        }
        button(R.id.record).setOnClickListener {
            if (engineState == EngineState.RAW) controller.stopRaw()
            else if (engineState == EngineState.RECORDING || engineState == EngineState.STARTING) controller.stopRecording()
            else modes.firstOrNull { it.key == modeKey }?.let { mode ->
                if (ModePlanning.recordingAllowed(engineState, mode, manualApplied, manualRequested)) {
                    requestRecording(mode, null)
                }
            }
        }
        button(R.id.liveLog).setOnClickListener {
            if (Build.VERSION.SDK_INT >= 33) startActivity(Intent(this, LiveLogActivity::class.java))
            else onState(engineState, "Live Log requires Android 13 or newer")
        }
        button(R.id.rawSequence).setOnClickListener { chooseRawSequence() }
        button(R.id.rawSequences).setOnClickListener { showRawSequences() }
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
    override fun onStart() { super.onStart(); reports.observe(observer); colourReferences.observe(colourObserver) }
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
        previewAids.setActive(false)
        requestedKey = null
        controller.close()
        reports.remove(observer)
        colourReferences.remove(colourObserver)
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        super.onStop()
    }
    override fun onDestroy() { destroyed = true; previewAids.close(); controller.release(); super.onDestroy() }
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
    private fun openClips() {
        if (CapturePolicy.canChangeCamera(engineState)) startActivity(Intent(this, CaptureLibraryActivity::class.java))
    }
    private fun showSettings(settings: Boolean) {
        findViewById<View>(R.id.manualControlFields).visibility = if (settings) View.GONE else View.VISIBLE
        findViewById<View>(R.id.settingsFields).visibility = if (settings) View.VISIBLE else View.GONE
        findViewById<ScrollView>(R.id.controlsPanel).scrollTo(0, 0)
    }
    @Suppress("DEPRECATION") private fun displayDegrees(): Int {
        val rotation = if (Build.VERSION.SDK_INT >= 30) display?.rotation ?: Surface.ROTATION_0 else windowManager.defaultDisplay.rotation
        return when (rotation) { Surface.ROTATION_90 -> 90; Surface.ROTATION_180 -> 180; Surface.ROTATION_270 -> 270; else -> 0 }
    }
    private fun setItems(spinner: Spinner, labels: List<String>) {
        spinner.adapter = object : ArrayAdapter<String>(this, R.layout.selector_item, labels) {
            override fun areAllItemsEnabled(): Boolean = spinner.id != R.id.modeSelector
            override fun isEnabled(position: Int): Boolean = spinner.id != R.id.modeSelector || position != 0
            override fun getView(position: Int, convertView: View?, parent: android.view.ViewGroup): View {
                return super.getView(position, convertView, parent).also { view ->
                    if (spinner.id == R.id.cameraSelector && view is TextView) {
                        view.text = "⋯"
                        view.contentDescription = getString(R.string.all_camera_routes, labels.getOrNull(position) ?: "")
                    }
                }
            }
        }.apply { setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
    }
    private fun selectCamera(target: CameraTarget) {
        if (target.key == selected?.key) return
        if (!CapturePolicy.canChangeCamera(engineState)) {
            selected?.let { spinner(R.id.cameraSelector).setSelection(targets.indexOf(it)) }
            return
        }
        selected = target; requestedKey = null
        spinner(R.id.cameraSelector).setSelection(targets.indexOf(target))
        // Disable recording before the asynchronous camera switch is admitted.
        onState(EngineState.OPENING, getString(R.string.switching_camera, target.label))
        renderLensRail(); maybeOpen()
    }
    private fun renderLensRail() {
        val rail = findViewById<LinearLayout>(R.id.lensRail)
        rail.removeAllViews()
        targets.forEach { target ->
            val facing = when (target.characteristics[C.LENS_FACING]) {
                C.LENS_FACING_BACK -> getString(R.string.lens_rear)
                C.LENS_FACING_FRONT -> getString(R.string.lens_front)
                C.LENS_FACING_EXTERNAL -> getString(R.string.lens_external)
                else -> getString(R.string.lens_unknown)
            }
            val focal = target.characteristics[C.LENS_INFO_AVAILABLE_FOCAL_LENGTHS]?.joinToString("/") { String.format(Locale.US, "%.1f", it) } ?: "?"
            rail.addView(Button(this).apply {
                text = "$facing $focal mm · ${target.physicalId ?: target.logicalId}"
                contentDescription = getString(R.string.advertised_camera_route, target.label)
                tag = target.key; isAllCaps = false
                isSelected = target.key == selected?.key
                alpha = if (isSelected) 1f else 0.65f
                setTextColor(if (isSelected) 0xFF72E5D1.toInt() else 0xFFE4EAF1.toInt())
                isEnabled = CapturePolicy.canChangeCamera(engineState)
                setOnClickListener { selectCamera(target) }
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.MATCH_PARENT)
            })
        }
    }
    override fun onCatalog(result: CatalogResult) {
        if (destroyed) return
        val previous = selected?.key ?: CameraSettings.camera(this)
        targets = result.targets
        selected = targets.firstOrNull { it.key == previous } ?: targets.firstOrNull()
        setItems(spinner(R.id.cameraSelector), targets.map { it.label })
        if (selected != null) spinner(R.id.cameraSelector).setSelection(targets.indexOf(selected))
        renderLensRail()
        if (targets.isEmpty()) onState(EngineState.ERROR, "No accessible camera. ${result.errors.joinToString()}")
        else maybeOpen()
    }
    override fun onReady(target: CameraTarget, previewSize: Size, plan: ModePlan, mode: RecordingMode?) {
        if (target.key != selected?.key || destroyed) return
        this.previewSize = previewSize
        modes = plan.modes
        latestPlan = plan
        renderBitrate(mode)
        manualApplied = false
        bindingControls = true
        modeKey = mode?.key
        setItems(spinner(R.id.modeSelector), listOf(getString(R.string.choose_format)) + modes.map { it.label })
        spinner(R.id.modeSelector).setSelection(if (mode != null) modes.indexOf(mode) + 1 else 0)
        CameraSettings.select(this, target.key)
        if (modeKey != null) CameraSettings.saveMode(this, target.key, modeKey)
        text(R.id.planNotes).text = plan.notes.joinToString("\n")
        val c = target.characteristics
        wbModes = target.wbModes
        setItems(spinner(R.id.wbSelector), wbModes.map(::wbName))
        quickControls.configure(target, mode)
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
        renderBitrate(mode)
        this.previewSize = previewSize
        selected?.let { quickControls.configure(it, mode) }
        selected?.let { CameraSettings.saveMode(this, it.key, mode.key) }
        spinner(R.id.modeSelector).setSelection(modes.indexOfFirst { it.key == mode.key } + 1)
        transformPreview()
    }
    override fun onControlsChanged(cameraKey: String, controls: CameraControls) {
        if (destroyed || cameraKey != selected?.key) return
        manualRequested = controls.manualExposure
        manualApplied = false // Accepted intent is not current sensor-result confirmation.
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
        quickControls.setCompensation(controls.exposureCompensationSteps)
        wbModes.indexOf(controls.wbMode).takeIf { it >= 0 }?.let { spinner(R.id.wbSelector).setSelection(it) }
        quickControls.sync()
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
    private fun chooseRawSequence() {
        val target = selected ?: return
        if (!manualApplied || !manualRequested) {
            AlertDialog.Builder(this).setTitle(R.string.raw_sequence)
                .setMessage("Apply manual exposure and wait for sensor-result confirmation first. RAW recording uses that ISO, shutter and focus; the existing audio choice is not changed.")
                .setPositiveButton(R.string.close, null).show()
            return
        }
        AlertDialog.Builder(this).setTitle(R.string.raw_sequence)
            .setItems(arrayOf("Acquire only — 5 seconds, no pixels saved", "Save RAW source — 5 seconds, video only")) { _, choice ->
                val map = target.characteristics[C.SCALER_STREAM_CONFIGURATION_MAP]
                val sizes = runCatching { map?.getOutputSizes(android.graphics.ImageFormat.RAW_SENSOR).orEmpty().toList() }.getOrDefault(emptyList())
                val candidates = sizes.sortedBy { it.width.toLong() * it.height }.flatMap { size ->
                    listOf(24, 30).mapNotNull { fps -> runCatching {
                        val plan = com.s23log.probe.core.RawSequencePlan(size.width, size.height, fps, 5, choice == 1)
                        val interval = requireNotNull(map).getOutputMinFrameDuration(android.graphics.ImageFormat.RAW_SENSOR, size)
                        val reason = if (interval > 1_000_000_000L / fps + 1) "Advertised RAW interval too long"
                            else plan.rejection(Runtime.getRuntime().maxMemory(), filesDir.usableSpace)
                        plan to reason
                    }.getOrNull() }
                }
                if (candidates.isEmpty()) {
                    AlertDialog.Builder(this).setTitle(R.string.raw_sequence).setMessage("No ordinary Bayer RAW_SENSOR candidates are exposed by this route.")
                        .setPositiveButton(R.string.close, null).show()
                } else AlertDialog.Builder(this).setTitle("Advertised RAW candidates — not certified")
                    .setItems(candidates.map { (p, why) -> "${p.width}×${p.height} / ${p.fps}" + (why?.let { " — $it" } ?: "") }.toTypedArray()) { _, index ->
                        val (plan, why) = candidates[index]
                        if (why != null) {
                            AlertDialog.Builder(this).setMessage(why).setPositiveButton(R.string.close, null).show()
                        } else AlertDialog.Builder(this).setTitle("Start continuous RAW?")
                            .setMessage("${plan.width}×${plan.height} at requested ${plan.fps} fps, five seconds.\n" +
                                "${plan.expectedPayloadBytes / 1_000_000} MB expected source payload. Preview pauses; no audio. " +
                                "Stop RAW remains available. Overflow stops acquisition and retains written frames. " +
                                "This does not certify sustained RAW video. Develop the saved source on this phone from Retained RAW sequences, or use the desktop developer.")
                            .setNegativeButton(R.string.cancel, null).setPositiveButton("Start RAW") { _, _ ->
                                if (selected?.key == target.key && engineState == EngineState.PREVIEW && manualApplied) {
                                    findViewById<View>(R.id.controlsPanel).visibility = View.GONE
                                    controller.captureRawSequence(plan)
                                }
                            }.show()
                    }.setNegativeButton(R.string.close, null).show()
            }.setNegativeButton(R.string.cancel, null).show()
    }
    private fun showRawSequences() {
        val folder = File(filesDir, "exports/raw-sequences")
        val files = folder.listFiles().orEmpty().filter { it.isFile && it.name.matches(Regex("raw-[0-9a-f-]+\\.s23raw")) }
            .sortedByDescending { it.lastModified() }
        if (files.isEmpty()) {
            AlertDialog.Builder(this).setTitle(R.string.raw_sequences).setMessage("No retained RAW sequences. RAW source is private; export before uninstalling. Interrupted sequences are retained here too.")
                .setPositiveButton(R.string.close, null).show()
        } else AlertDialog.Builder(this).setTitle("RAW source — may be incomplete")
            .setItems(files.map { "${it.name} (${it.length() / 1_000_000} MB)" }.toTypedArray()) { _, index ->
                val file = files[index]
                val report = File(filesDir, "exports/validation/${file.nameWithoutExtension}.json")
                AlertDialog.Builder(this).setTitle("Retained RAW source")
                    .setMessage("Develop this source as LogC3 on this phone, or export it for desktop development. Checksums, timing and a bound colour profile are required. Incomplete sources are never silently repaired.")
                    .setPositiveButton("Export") { _, _ -> shareFiles(listOf(file) + listOfNotNull(report.takeIf { it.isFile }), "application/octet-stream") }
                    .setNeutralButton("Develop as LogC3") { _, _ ->
                        startActivity(Intent(this, RawDevelopActivity::class.java).putExtra("sourceName", file.name))
                    }.setNegativeButton("Delete…") { _, _ ->
                        AlertDialog.Builder(this).setTitle("Permanently delete this RAW source?").setMessage(file.name)
                            .setNegativeButton("Keep", null).setPositiveButton("Delete") { _, _ ->
                                if (!file.delete()) Toast.makeText(this, "RAW source could not be deleted", Toast.LENGTH_LONG).show()
                            }.show()
                    }.show()
            }.setNegativeButton(R.string.close, null).show()
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
        val monitorAvailable = state in setOf(EngineState.PREVIEW, EngineState.ADJUSTING) ||
            (state == EngineState.RECORDING && modes.firstOrNull { it.key == modeKey }?.previewDuringRecording == true)
        previewAids.setActive(visible && pages.displayedChild == 0 && monitorAvailable)
        if (state in setOf(EngineState.STARTING, EngineState.RECORDING, EngineState.STOPPING, EngineState.RAW)) {
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
        if (state == EngineState.OPENING || state == EngineState.CLOSED || state == EngineState.ERROR) {
            manualApplied = false; manualRequested = false
        }
        val clock = findViewById<Chronometer>(R.id.recordingClock)
        if (state == EngineState.RECORDING && previous != state) { clock.base = SystemClock.elapsedRealtime(); clock.start() }
        else if (state != EngineState.RECORDING) { clock.stop(); if (state == EngineState.PREVIEW || state == EngineState.CLOSED) clock.base = SystemClock.elapsedRealtime() }
        text(R.id.cameraStatus).text = message
        val mode = modes.firstOrNull { it.key == modeKey }
        val showOverlay = state !in setOf(EngineState.PREVIEW, EngineState.ADJUSTING, EngineState.RECORDING) ||
            (state == EngineState.RECORDING && mode?.previewDuringRecording == false)
        text(R.id.previewOverlay).visibility = if (showOverlay) View.VISIBLE else View.GONE
        text(R.id.previewOverlay).text = message
        if (state == EngineState.STARTING || state == EngineState.RECORDING || state == EngineState.RAW) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        if (state != EngineState.RECORDING) renderAudioIdle()
        updateEnabled()
    }
    override fun onApplied(values: Map<String, Any?>) {
        if (destroyed || !visible) return
        val wasManual = manualApplied
        val wasRequested = manualRequested
        manualRequested = values["manualRequested"] == true
        manualApplied = values["manualExposureConfirmed"] == true
        if (wasManual != manualApplied || wasRequested != manualRequested) updateEnabled()
        val ms = (values["exposureNs"] as? Long)?.let { String.format(Locale.US, "%.3f", it / 1_000_000.0) } ?: "?"
        text(R.id.applied).text = "APPLIED · ${values["nominalFps"] ?: "auto"} fps target · ISO ${values["iso"] ?: "?"} · ${ms} ms · focus ${values["focusDiopters"] ?: "?"} dpt · WB ${values["awbMode"] ?: "?"}"
        text(R.id.applied).append("\nReported lens · ${values["focalLengthMm"] ?: "?"} mm" +
            (values["activePhysicalCameraId"]?.let { " · active physical $it" } ?: ""))
        if (values["exposureCompensationActive"] == true) {
            val steps = values["exposureCompensationSteps"] as? Int
            val ev = steps?.let { selected?.exposureCompensation?.ev(it) }?.let { String.format(Locale.US, "%+.2f", it) } ?: "?"
            val state = when (values["aeState"]) {
                CaptureRequest.CONTROL_AE_STATE_INACTIVE -> "inactive"
                CaptureRequest.CONTROL_AE_STATE_SEARCHING -> "searching"
                CaptureRequest.CONTROL_AE_STATE_CONVERGED -> "converged"
                CaptureRequest.CONTROL_AE_STATE_LOCKED -> "locked"
                CaptureRequest.CONTROL_AE_STATE_FLASH_REQUIRED -> "flash required"
                CaptureRequest.CONTROL_AE_STATE_PRECAPTURE -> "precapture"
                else -> "unreported"
            }
            text(R.id.applied).append("\nAE compensation · $ev EV reported · $state")
        }
        if (manualRequested) {
            val check = values["manualControlMatch"] as? Map<*, *>
            val targetMs = (check?.get("targetExposureNs") as? Long)?.let { String.format(Locale.US, "%.3f", it / 1_000_000.0) } ?: "?"
            val clamped = values["requestedIso"] != check?.get("targetIso") || values["requestedExposureNs"] != check?.get("targetExposureNs")
            text(R.id.applied).append("\nMANUAL TARGET · ISO ${check?.get("targetIso") ?: "?"} · $targetMs ms · ${check?.get("status") ?: "unknown"}" + if (clamped) " · clamped to supported limits" else "")
        }
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
        findViewById<LinearLayout>(R.id.lensRail).let { rail -> for (i in 0 until rail.childCount) rail.getChildAt(i).isEnabled = idle }
        spinner(R.id.modeSelector).isEnabled = preview && modes.isNotEmpty()
        val mode = modes.firstOrNull { it.key == modeKey }
        val processed = mode?.processing == ProcessingPath.GPU_HLG10
        button(R.id.monitorTransform).isEnabled = processed && (preview || recording)
        button(R.id.monitorTransform).setText(if (viewingTransform == MonitorTransform.SDR_TONEMAP) R.string.monitor_sdr else R.string.monitor_signal)
        text(R.id.colourStatus).setText(if (processed) R.string.colour_gpu else R.string.colour_direct)
        val canRecord = ModePlanning.recordingAllowed(engineState, mode, manualApplied, manualRequested)
        button(R.id.record).isEnabled = canRecord || recording || engineState == EngineState.STARTING || engineState == EngineState.RAW
        button(R.id.testMode).isEnabled = canRecord
        button(R.id.audioMode).isEnabled = idle
        button(R.id.modeDetails).isEnabled = idle && latestPlan != null
        button(R.id.previewAids).isEnabled = preview || (recording && mode?.previewDuringRecording == true)
        text(R.id.modeEvidence).setText(if (mode == null) R.string.choose_format else if (mode.ratePlan.requiresManual && !manualApplied) R.string.manual_timing_required else R.string.advertised_only)
        button(R.id.record).setText(if (engineState == EngineState.RAW) R.string.stop_raw else if (recording || engineState == EngineState.STARTING) R.string.stop_recording else R.string.start_recording)
        button(R.id.recoverCaptures).isEnabled = idle
        button(R.id.captureLibrary).isEnabled = idle
        button(R.id.clipsTab).isEnabled = idle
        button(R.id.diagnosticsTab).isEnabled = idle
        button(R.id.cameraTab).isEnabled = idle
        button(R.id.enableCamera).isEnabled = idle
        button(R.id.enableCamera).visibility = if (engineState == EngineState.CLOSED || engineState == EngineState.ERROR) View.VISIBLE else View.GONE
        val rawAvailable = runCatching { selected?.rawSize != null }.getOrDefault(false)
        button(R.id.rawOne).isEnabled = preview && rawAvailable
        button(R.id.rawFive).isEnabled = preview && rawAvailable
        button(R.id.rawSequence).isEnabled = preview && selected?.manualSensor == true
        button(R.id.rawSequences).isEnabled = idle
        button(R.id.liveLog).isEnabled = idle && Build.VERSION.SDK_INT >= 33
        val controls = preview || recording
        toggle(R.id.manualExposure).isEnabled = controls && selected?.manualSensor == true
        text(R.id.isoInput).isEnabled = controls && toggle(R.id.manualExposure).isChecked
        text(R.id.shutterInput).isEnabled = controls && toggle(R.id.manualExposure).isChecked
        toggle(R.id.manualFocus).isEnabled = controls && selected?.manualFocus == true
        text(R.id.focusInput).isEnabled = controls && toggle(R.id.manualFocus).isChecked
        spinner(R.id.wbSelector).isEnabled = controls && wbModes.isNotEmpty()
        toggle(R.id.wbLock).isEnabled = controls && selected?.wbLockAvailable == true
        button(R.id.applyControls).isEnabled = controls
        button(R.id.bitratePreset).isEnabled = preview
        button(R.id.colourReference).isEnabled = idle && !colourReferences.state.running
        quickControls.enabled(controls && toggle(R.id.manualExposure).isChecked && selected?.manualSensor == true,
            controls && toggle(R.id.manualFocus).isChecked && selected?.manualFocus == true,
            controls && !toggle(R.id.manualExposure).isChecked)
    }
    private fun bitrateLabel(preset: BitratePreset) = getString(when (preset) {
        BitratePreset.LOW -> R.string.bitrate_low
        BitratePreset.STANDARD -> R.string.bitrate_standard
        BitratePreset.HIGH -> R.string.bitrate_high
    })
    private fun bitrateChoice(preset: BitratePreset, mode: RecordingMode?): String {
        if (mode == null) return bitrateLabel(preset)
        val target = BitratePolicy.select(mode.baseBitRate, mode.minimumBitRate, mode.maximumBitRate, preset)
        return "${bitrateLabel(preset)} · ${String.format(Locale.US, "%.1f", target.effective / 1_000_000.0)} Mb/s" +
            if (target.limited) getString(R.string.bitrate_limited) else ""
    }
    private fun renderBitrate(mode: RecordingMode?) {
        val preset = mode?.bitratePreset ?: CameraSettings.bitratePreset(this)
        button(R.id.bitratePreset).text = getString(R.string.bitrate_current, bitrateChoice(preset, mode))
    }
    private fun chooseBitratePreset() {
        if (engineState != EngineState.PREVIEW) return
        val mode = modes.firstOrNull { it.key == modeKey }
        val choices = BitratePreset.entries
        AlertDialog.Builder(this).setTitle(R.string.bitrate_title)
            .setSingleChoiceItems(choices.map { bitrateChoice(it, mode) }.toTypedArray(), choices.indexOf(mode?.bitratePreset ?: CameraSettings.bitratePreset(this))) { dialog, index ->
                applyBitratePreset(choices[index]); dialog.dismiss()
            }.setNegativeButton(R.string.cancel, null).show()
    }
    internal fun applyBitratePreset(preset: BitratePreset) { if (engineState == EngineState.PREVIEW) controller.setBitratePreset(preset) }
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
        if (!visible || pages.displayedChild != 0 || mode.key != modeKey || !ModePlanning.recordingAllowed(engineState, mode, manualApplied, manualRequested)) return
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
        controller.startRecording(mode, testSeconds, audioMode, previewAids.features())
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
                toggle(R.id.wbLock).isChecked, exposureCompensationSteps = quickControls.compensationSteps))
        } catch (e: Exception) { text(R.id.cameraStatus).text = "Invalid controls: ${e.message}" }
    }
    private fun wbName(mode: Int): String = when (mode) {
        1 -> "Auto"; 2 -> "Incandescent"; 3 -> "Fluorescent"; 4 -> "Warm fluorescent"; 5 -> "Daylight"; 6 -> "Cloudy daylight"; 7 -> "Twilight"; 8 -> "Shade"; else -> "Preset $mode"
    }
    private fun showRecordingAttempts() {
        val directory = File(filesDir, "exports/recording-evidence")
        val files = directory.listFiles().orEmpty().filter { it.isFile && it.name.matches(Regex("recording-attempt-[0-9a-f-]{36}\\.json")) }
            .sortedByDescending { it.lastModified() }.take(64)
        if (files.isEmpty()) {
            AlertDialog.Builder(this).setTitle(R.string.recording_attempts)
                .setMessage("No retained attempts yet. Failed and interrupted recording attempts appear here too.")
                .setPositiveButton(R.string.close, null).show()
            return
        }
        val labels = files.map { java.text.DateFormat.getDateTimeInstance().format(java.util.Date(it.lastModified())) + " · " + it.name.removePrefix("recording-attempt-").take(8) }
        AlertDialog.Builder(this).setTitle("Recording attempts · latest ${files.size}")
            .setItems(labels.toTypedArray()) { _, index ->
                val file = files[index]
                val summary = runCatching {
                    require(file.length() in 1..2_000_000)
                    val report = org.json.JSONObject(file.readText())
                    val stages = report.getJSONArray("stages")
                    (if (report.getBoolean("closed")) "Completed attempt" else "Incomplete checkpoint — not a completed recording") + "\n\n" +
                        (0 until stages.length()).joinToString("\n") { i -> val row = stages.getJSONObject(i); "${row.getString("stage")}: ${row.getString("outcome")}" } +
                        "\n\nFull-file decoding and physical S23 qualification are separate checks."
                }.getOrElse { "Report could not be read: ${it.message}" }
                AlertDialog.Builder(this).setTitle(R.string.recording_attempts).setMessage(summary)
                    .setPositiveButton("Share report") { _, _ -> shareFiles(listOf(file), "application/json") }
                    .setNegativeButton(R.string.close, null).show()
            }.setNegativeButton(R.string.close, null).show()
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
        val contentWidth = (if (rotated) size.height else size.width) * scale
        val contentHeight = (if (rotated) size.width else size.height) * scale
        previewAids.setContentBounds((w - contentWidth) / 2, (h - contentHeight) / 2,
            (w + contentWidth) / 2, (h + contentHeight) / 2)
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
    override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean { requestedKey = null; previewAids.clearFrame(); controller.detachTexture(surface); return false }
    override fun onSurfaceTextureUpdated(surface: SurfaceTexture) { if (visible && pages.displayedChild == 0) previewAids.sample(texture) }

    private fun choosePreviewAids() {
        val choices = PreviewAid.entries
        val enabled = choices.map { it in previewAids.features() }.toBooleanArray()
        fun apply() {
            val selected = choices.filterIndexed { i, _ -> enabled[i] }.toSet()
            applyPreviewAids(selected)
        }
        AlertDialog.Builder(this).setTitle(R.string.preview_aids_title)
            .setMultiChoiceItems(R.array.preview_aid_options, enabled) { _, index, checked -> enabled[index] = checked; apply() }
            .setPositiveButton(R.string.close, null)
            .setNegativeButton(R.string.preview_aids_off) { _, _ -> enabled.fill(false); apply() }.show()
    }
    internal fun applyPreviewAids(features: Set<PreviewAid>) {
        previewAids.setFeatures(features); controller.notePreviewAids(features)
    }
}
