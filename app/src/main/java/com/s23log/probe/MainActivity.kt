package com.s23log.probe

import android.Manifest
import android.app.Activity
import android.content.ClipData
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Matrix
import android.graphics.SurfaceTexture
import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.CaptureRequest
import android.net.Uri
import android.os.Build
import android.os.Bundle
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
import com.s23log.probe.core.CapturePolicy
import com.s23log.probe.core.EngineState
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.diagnostics.ProbeStore
import com.s23log.probe.storage.CaptureHistory
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
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContentView(R.layout.activity_main)
        val root = findViewById<View>(R.id.root)
        val padding = (12 * resources.displayMetrics.density).toInt()
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
        button(R.id.record).setOnClickListener {
            if (engineState == EngineState.RECORDING || engineState == EngineState.STARTING) controller.stopRecording()
            else modes.getOrNull(spinner(R.id.modeSelector).selectedItemPosition)?.let(controller::startRecording)
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
    override fun onSaveInstanceState(outState: Bundle) { outState.putInt("page", pages.displayedChild); super.onSaveInstanceState(outState) }
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
        controller.open(target, surface, displayDegrees())
    }
    @Suppress("DEPRECATION") private fun displayDegrees(): Int {
        val rotation = if (Build.VERSION.SDK_INT >= 30) display?.rotation ?: Surface.ROTATION_0 else windowManager.defaultDisplay.rotation
        return when (rotation) { Surface.ROTATION_90 -> 90; Surface.ROTATION_180 -> 180; Surface.ROTATION_270 -> 270; else -> 0 }
    }
    private fun setItems(spinner: Spinner, labels: List<String>) {
        spinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, labels).apply { setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item) }
    }
    override fun onCatalog(result: CatalogResult) {
        if (destroyed) return
        val previous = selected?.key
        targets = result.targets
        selected = targets.firstOrNull { it.key == previous } ?: targets.firstOrNull()
        setItems(spinner(R.id.cameraSelector), targets.map { it.label })
        if (selected != null) spinner(R.id.cameraSelector).setSelection(targets.indexOf(selected))
        if (targets.isEmpty()) onState(EngineState.ERROR, "No accessible camera. ${result.errors.joinToString()}")
        else maybeOpen()
    }
    override fun onReady(target: CameraTarget, previewSize: Size, plan: ModePlan) {
        if (target.key != selected?.key || destroyed) return
        this.previewSize = previewSize
        modes = plan.modes
        setItems(spinner(R.id.modeSelector), modes.map { it.label })
        text(R.id.planNotes).text = plan.notes.joinToString("\n")
        toggle(R.id.manualExposure).isChecked = false
        toggle(R.id.manualFocus).isChecked = false
        toggle(R.id.wbLock).isChecked = false
        val c = target.characteristics
        wbModes = c[C.CONTROL_AWB_AVAILABLE_MODES].orEmpty().filter { it != CaptureRequest.CONTROL_AWB_MODE_OFF }
        setItems(spinner(R.id.wbSelector), wbModes.map(::wbName))
        val isoRange = c[C.SENSOR_INFO_SENSITIVITY_RANGE]
        text(R.id.isoInput).text = (isoRange?.lower?.coerceAtLeast(100) ?: 100).toString()
        text(R.id.limits).text = "ISO ${isoRange ?: "unreported"}; shutter ns ${c[C.SENSOR_INFO_EXPOSURE_TIME_RANGE] ?: "unreported"}; focus 0…${target.minFocus} diopters. Video shutter is bounded by its frame interval."
        transformPreview()
        updateEnabled()
    }
    override fun onState(state: EngineState, message: String) {
        if (destroyed) return
        engineState = state
        text(R.id.cameraStatus).text = message
        val mode = modes.getOrNull(spinner(R.id.modeSelector).selectedItemPosition)
        val showOverlay = state !in setOf(EngineState.PREVIEW, EngineState.RECORDING) ||
            (state == EngineState.RECORDING && mode?.previewDuringRecording == false)
        text(R.id.previewOverlay).visibility = if (showOverlay) View.VISIBLE else View.GONE
        text(R.id.previewOverlay).text = message
        if (state == EngineState.RECORDING) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        updateEnabled()
    }
    override fun onApplied(values: Map<String, Any?>) {
        if (destroyed || !visible) return
        val ms = (values["exposureNs"] as? Long)?.let { String.format(Locale.US, "%.3f", it / 1_000_000.0) } ?: "?"
        text(R.id.applied).text = "APPLIED · ISO ${values["iso"] ?: "?"} · ${ms} ms · focus ${values["focusDiopters"] ?: "?"} dpt · WB ${values["awbMode"] ?: "?"}"
    }
    override fun onVideo(outcome: SurfaceRecorder.Outcome) { restoreCapture() }
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
        button(R.id.record).isEnabled = (preview && modes.isNotEmpty()) || recording || engineState == EngineState.STARTING
        button(R.id.record).setText(if (recording || engineState == EngineState.STARTING) R.string.stop_recording else R.string.start_recording)
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
        toggle(R.id.manualFocus).isEnabled = controls && (selected?.minFocus ?: 0f) > 0f &&
            selected?.characteristics?.get(C.CONTROL_AF_AVAILABLE_MODES)?.contains(CaptureRequest.CONTROL_AF_MODE_OFF) == true
        text(R.id.focusInput).isEnabled = controls && toggle(R.id.manualFocus).isChecked
        spinner(R.id.wbSelector).isEnabled = controls && wbModes.isNotEmpty()
        toggle(R.id.wbLock).isEnabled = controls && selected?.characteristics?.get(C.CONTROL_AWB_LOCK_AVAILABLE) == true
        button(R.id.applyControls).isEnabled = controls
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
