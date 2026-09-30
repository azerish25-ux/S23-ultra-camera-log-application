package com.s23log.probe.camera

import com.s23log.probe.S23Application
import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.SurfaceTexture
import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CaptureFailure
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.CaptureResult
import android.hardware.camera2.TotalCaptureResult
import android.hardware.camera2.params.DynamicRangeProfiles
import android.hardware.camera2.params.OutputConfiguration
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.Looper
import android.os.SystemClock
import android.util.Size
import android.view.Surface
import com.s23log.probe.core.AudioMode
import com.s23log.probe.core.ProcessingPath
import com.s23log.probe.core.MonitorTransform
import com.s23log.probe.core.ManualExposureGate
import com.s23log.probe.core.ManualResultPolicy
import com.s23log.probe.core.CapturePolicy
import com.s23log.probe.core.DynamicRange
import com.s23log.probe.core.EngineState
import com.s23log.probe.core.RecordingMode
import com.s23log.probe.core.SessionEpoch
import java.util.concurrent.Executors

/** Serial owner of camera resources. No blocking codec drain or file I/O on this thread. */
class CameraController(context: Context, listener: Listener) {
    interface Listener {
        fun onCatalog(result: CatalogResult)
        fun onReady(target: CameraTarget, previewSize: Size, plan: ModePlan, mode: RecordingMode?)
        fun onModeChanged(cameraKey: String, mode: RecordingMode, previewSize: Size)
        fun onControlsChanged(cameraKey: String, controls: CameraControls)
        fun onState(state: EngineState, message: String)
        fun onApplied(values: Map<String, Any?>)
        fun onAudioMeter(meter: AudioCapture.Meter) {}
        fun onAudioError(message: String) {}
        fun onResources(snapshot: RecordingResources.Snapshot) {}
        fun onVideo(outcome: SurfaceRecorder.Outcome)
        fun onRaw(outcome: RawCapture.Outcome)
    }
    private data class PreviewRequest(val target: CameraTarget, val texture: SurfaceTexture, val displayDegrees: Int, val modeKey: String?, val controls: CameraControls)
    private val app = context.applicationContext
    private val manager = app.getSystemService(CameraManager::class.java)
    private val thread = HandlerThread("S23Log-camera").apply { start() }
    private val handler = Handler(thread.looper)
    private val main = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor()
    @Volatile private var listener: Listener? = listener
    private var releasing = false
    private var wanted: PreviewRequest? = null
    private var device: CameraDevice? = null
    private var session: CameraCaptureSession? = null
    private var previewSurface: Surface? = null
    private var openingToken: Long? = null
    private val closing = mutableSetOf<CameraDevice>()
    private val deviceEpoch = SessionEpoch()
    private val sessionEpoch = SessionEpoch()
    private var state = EngineState.CLOSED
    private var controls = CameraControls()
    private var intentControls = CameraControls()
    private var selectedMode: RecordingMode? = null
    private val requestEpoch = SessionEpoch()
    private var afterFirstPreview: CameraControls? = null
    private class ManualJob(val intent: CameraControls, val previous: CameraControls, val gate: ManualExposureGate) {
        var effective = intent
        var deadline: Runnable? = null
    }
    private var manualJob: ManualJob? = null
    private var recorder: SurfaceRecorder? = null
    private var raw: RawCapture? = null
    private var modes: List<RecordingMode> = emptyList()
    private var lastAppliedAt = 0L
    private var previewHasFrames = false
    private var previewControlWarning: String? = null
    private var manualExposureConfirmed = false
    private val closeWaiters = java.util.IdentityHashMap<CameraCaptureSession, () -> Unit>()
    private val retiredTextures = mutableSetOf<SurfaceTexture>()
    private var monitorTransform = MonitorTransform.SDR_TONEMAP
    fun setMonitor(transform: MonitorTransform) { handler.post { monitorTransform = transform; recorder?.setMonitor(transform) } }
    private fun releaseRetiredTextures() {
        if (recorder == null) { retiredTextures.forEach { runCatching { it.release() } }; retiredTextures.clear() }
    }
    private fun afterPreviewClosed(active: SurfaceRecorder, ready: () -> Unit) {
        val old = session
        if (old == null) { ready(); return }
        closeWaiters[old] = { if (recorder === active && state == EngineState.STARTING && wanted != null) ready() }
        closeSession()
        handler.postDelayed({ if (closeWaiters.remove(old) != null && recorder === active) active.cancel("Camera preview did not disconnect before GPU monitor setup") }, 5000)
    }

    private fun emit(block: (Listener) -> Unit) { main.post { listener?.let(block) } }
    private fun changedControls(value: CameraControls) {
        val key = wanted?.target?.key ?: return
        emit { it.onControlsChanged(key, value) }
    }
    private fun state(next: EngineState, message: String) { state = next; emit { it.onState(next, message) } }
    fun discover() {
        io.execute {
            val recovery = runCatching { (app as S23Application).awaitMediaRecovery() }
            handler.post {
                if (!releasing) {
                    if (recovery.isFailure) { state(EngineState.ERROR, "Media recovery could not finish; capture remains disabled"); return@post }
                    val result = CameraCatalog.discover(manager)
                    emit { it.onCatalog(result) }
                }
            }
        }
    }
    fun open(target: CameraTarget, texture: SurfaceTexture, displayDegrees: Int, modeKey: String? = null, initialControls: CameraControls = CameraControls()) {
        handler.post {
            if (releasing) return@post
            wanted = null
            teardown()
            intentControls = initialControls
            controls = initialControls.copy(manualExposure = false, wbLock = false, afModeOverride = null)
            wanted = PreviewRequest(target, texture, displayDegrees, modeKey, initialControls)
            reconcile()
        }
    }
    fun selectMode(mode: RecordingMode) {
        handler.post {
            if (state != EngineState.PREVIEW || recorder != null || raw != null || modes.none { it.key == mode.key }) return@post
            if (selectedMode?.key == mode.key) return@post
            try {
                val request = requireNotNull(wanted)
                val size = CameraCatalog.previewSize(request.target, mode)
                // Closing/flushing the old session can block. Stop advertising readiness
                // before doing it, not after the replacement Surface has been created.
                state(EngineState.OPENING, "Matching preview to ${mode.label}…")
                selectedMode = mode
                closeSession()
                previewSurface?.release()
                request.texture.setDefaultBufferSize(size.width, size.height)
                previewSurface = Surface(request.texture)
                emit { it.onModeChanged(request.target.key, mode, size) }
                configurePreview()
            } catch (e: Exception) { fail("Mode preview unavailable: ${e.message}") }
        }
    }
    fun applyControls(value: CameraControls) {
        handler.post {
            if (state != EngineState.PREVIEW && state != EngineState.RECORDING) return@post
            try {
                if (value.manualExposure && !controls.manualExposure) {
                    require(state == EngineState.PREVIEW) { "Stop recording before establishing manual exposure locks" }
                    beginManual(value)
                } else if (value.manualExposure) {
                    // Never temporarily enable AE during a recording to re-meter focus or WB.
                    val safe = value.copy(focusDiopters = value.focusDiopters ?: controls.focusDiopters,
                        wbLock = value.wbMode == CaptureRequest.CONTROL_AWB_MODE_AUTO || value.wbLock)
                    require(value.wbMode == controls.wbMode && (!safe.wbLock || controls.wbLock)) {
                        "Return to auto exposure in preview before changing the white-balance strategy"
                    }
                    repeat(safe)
                    controls = safe; intentControls = safe
                    changedControls(safe)
                } else {
                    require(state != EngineState.RECORDING || !controls.manualExposure) { "Stop recording before leaving manual exposure" }
                    repeat(value)
                    controls = value; intentControls = value
                    changedControls(value)
                }
            } catch (e: Exception) { changedControls(controls); emit { it.onState(state, "Controls rejected: ${e.message}") } }
        }
    }
    private fun beginManual(value: CameraControls) {
        val target = requireNotNull(wanted).target
        require(target.manualSensor) { "Manual sensor controls unavailable on this route" }
        require(value.wbMode != CaptureRequest.CONTROL_AWB_MODE_AUTO || target.wbLockAvailable) { "Select a WB preset; this route cannot lock automatic WB" }
        require(target.minFocus == 0f || target.manualFocus) { "This route cannot freeze its focus before disabling AE" }
        val autofocus = value.focusDiopters == null && target.minFocus > 0
        if (autofocus) require(target.characteristics[C.CONTROL_AF_AVAILABLE_MODES]?.contains(CaptureRequest.CONTROL_AF_MODE_AUTO) == true) {
            "Set manual focus explicitly; a triggered focus lock is unavailable"
        }
        val job = ManualJob(value, controls, ManualExposureGate(SystemClock.elapsedRealtime()))
        manualJob = job
        state(EngineState.ADJUSTING, "Establishing focus and white balance with auto exposure; manual exposure is not active yet…")
        val preflight = value.copy(manualExposure = false, wbLock = false,
            afModeOverride = if (autofocus) CaptureRequest.CONTROL_AF_MODE_AUTO else null)
        try {
            repeat(preflight, if (autofocus) CaptureRequest.CONTROL_AF_TRIGGER_START else null)
            val deadline = object : Runnable {
                override fun run() {
                    if (manualJob !== job) return
                    if (job.gate.accept(SystemClock.elapsedRealtime(), ManualExposureGate.Evidence()) == ManualExposureGate.Action.REJECT)
                        rejectManual(job, "Timed out waiting for ${job.gate.stage}; required capture-result metadata was not confirmed")
                    else handler.postDelayed(this, 200)
                }
            }
            job.deadline = deadline
            handler.postDelayed(deadline, 200)
        } catch (e: Exception) { rejectManual(job, e.message ?: "Preflight request failed") }
    }
    private fun rejectManual(job: ManualJob, reason: String) {
        if (manualJob !== job) return
        manualJob = null
        job.deadline?.let(handler::removeCallbacks)
        val safe = job.previous.copy(manualExposure = false, wbLock = false, afModeOverride = null)
        try {
            repeat(safe); controls = safe; intentControls = safe
            changedControls(safe)
            state(EngineState.PREVIEW, "Manual transition rejected: $reason. Auto exposure restored; no recording started.")
        } catch (e: Exception) { fail("Could not restore preview controls: ${e.message}") }
    }
    private fun advanceManual(actual: CaptureResult?) {
        val job = manualJob ?: return
        if (actual == null) return // missing physical metadata must time out, never confirm a lock
        val target = requireNotNull(wanted).target
        val autofocus = job.intent.focusDiopters == null && target.minFocus > 0
        val autoWb = job.intent.wbMode == CaptureRequest.CONTROL_AWB_MODE_AUTO
        val ae = actual[CaptureResult.CONTROL_AE_STATE]
        val af = actual[CaptureResult.CONTROL_AF_STATE]
        val wb = actual[CaptureResult.CONTROL_AWB_STATE]
        val focus = actual[CaptureResult.LENS_FOCUS_DISTANCE]
        val fixedFocus = target.minFocus == 0f ||
            (actual[CaptureResult.CONTROL_AF_MODE] == CaptureRequest.CONTROL_AF_MODE_OFF && focus != null && focus.isFinite() &&
                (actual[CaptureResult.LENS_STATE] == null || actual[CaptureResult.LENS_STATE] == CaptureResult.LENS_STATE_STATIONARY))
        val locked = fixedFocus && if (autoWb)
            actual[CaptureResult.CONTROL_AWB_LOCK] == true && wb == CaptureResult.CONTROL_AWB_STATE_LOCKED
            else actual[CaptureResult.CONTROL_AWB_MODE] == job.intent.wbMode
        val expected = job.effective.effective(target, selectedMode?.fps)
        val appliedManual = ManualResultPolicy.assess(expected.iso, expected.exposureNs,
            selectedMode?.fps?.let { 1_000_000_000L / it }, actual[CaptureResult.SENSOR_SENSITIVITY],
            actual[CaptureResult.SENSOR_EXPOSURE_TIME], actual[CaptureResult.SENSOR_FRAME_DURATION],
            actual[CaptureResult.CONTROL_AE_MODE] == CaptureRequest.CONTROL_AE_MODE_OFF)
        val evidence = ManualExposureGate.Evidence(
            converged = actual[CaptureResult.CONTROL_AE_MODE] == CaptureRequest.CONTROL_AE_MODE_ON &&
                ae in listOf(CaptureResult.CONTROL_AE_STATE_CONVERGED, CaptureResult.CONTROL_AE_STATE_FLASH_REQUIRED, CaptureResult.CONTROL_AE_STATE_LOCKED) &&
                (if (autofocus) af == CaptureResult.CONTROL_AF_STATE_FOCUSED_LOCKED && focus != null else fixedFocus) &&
                (if (autoWb) wb == CaptureResult.CONTROL_AWB_STATE_CONVERGED else actual[CaptureResult.CONTROL_AWB_MODE] == job.intent.wbMode),
            locked = locked,
            applied = locked && appliedManual.matched,
            focusFailed = autofocus && job.gate.stage == ManualExposureGate.Stage.CONVERGING && af == CaptureResult.CONTROL_AF_STATE_NOT_FOCUSED_LOCKED
        )
        try {
            when (job.gate.accept(SystemClock.elapsedRealtime(), evidence)) {
                ManualExposureGate.Action.LOCK -> {
                    job.effective = job.intent.copy(wbLock = autoWb || job.intent.wbLock,
                        focusDiopters = job.intent.focusDiopters ?: if (target.minFocus > 0) requireNotNull(focus) else null)
                    repeat(job.effective.copy(manualExposure = false))
                    state(EngineState.ADJUSTING, "Confirming fixed focus and white-balance lock before disabling auto exposure…")
                }
                ManualExposureGate.Action.APPLY -> {
                    repeat(job.effective)
                    state(EngineState.ADJUSTING, "Confirming applied manual exposure in sensor results…")
                }
                ManualExposureGate.Action.COMPLETE -> {
                    controls = job.effective; intentControls = job.effective
                    manualJob = null; job.deadline?.let(handler::removeCallbacks)
                    changedControls(controls)
                    state(EngineState.PREVIEW, "Live preview · manual exposure confirmed; focus fixed and WB locked/preset · ${selectedMode?.fps ?: "auto"} fps target")
                }
                ManualExposureGate.Action.REJECT -> rejectManual(job, "Focus failed or the lock/apply deadline expired")
                ManualExposureGate.Action.WAIT -> Unit
            }
        } catch (e: Exception) { rejectManual(job, e.message ?: "Control transition failed") }
    }
    fun startRecording(mode: RecordingMode, testSeconds: Int? = null, audioMode: AudioMode = AudioMode.OFF) {
        handler.post {
            if (!CapturePolicy.canStartRecording(state) || recorder != null || raw != null) return@post
            val request = wanted ?: return@post
            if (modes.none { it.key == mode.key } || selectedMode?.key != mode.key) { emit { it.onState(state, "Mode was not planned for this camera") }; return@post }
            if (mode.ratePlan.requiresManual && !controls.manualExposure) {
                emit { it.onState(state, "This mode requires confirmed manual exposure. Open Controls and apply manual exposure first.") }; return@post
            }
            if (controls.manualExposure && !manualExposureConfirmed) {
                emit { it.onState(state, "Manual settings have not matched current sensor results. Inspect the applied values before recording.") }
                return@post
            }
            if (testSeconds != null && testSeconds != 5) return@post
            try {
                state(EngineState.STARTING, "Configuring ${mode.label} · ${if (audioMode.enabled) "microphone ${audioMode.name.lowercase()}" else "video only"} · not custom Log")
                val orientation = CapturePolicy.orientation(request.target.characteristics[C.SENSOR_ORIENTATION] ?: 0, request.displayDegrees, request.target.front)
                var current: SurfaceRecorder? = null
                current = SurfaceRecorder.prepare(app, mode, orientation, mapOf(
                    "logicalCamera" to request.target.logicalId, "physicalCamera" to request.target.physicalId,
                    "controls" to intentControls.describe(), "effectiveControls" to controls.effective(request.target, mode.fps).describe(),
                    "selectedMode" to mode.describe(), "nominalFps" to mode.fps, "bitrate" to mode.bitRate,
                    "testKind" to (if (testSeconds != null) "user_initiated_short_recording" else "normal_recording"),
                    "requestedTestSeconds" to testSeconds, "audioMode" to audioMode.name,
                    "cameraTimingAdvertised" to mode.timingAdvertised, "previewDuringRecording" to mode.previewDuringRecording
                ), audioMode = audioMode, onResources = { snapshot -> handler.post {
                    if (recorder === current && state in setOf(EngineState.STARTING, EngineState.RECORDING)) emit { it.onResources(snapshot) }
                } }, onSafetyStop = { reason -> handler.post {
                    if (recorder === current && state in setOf(EngineState.STARTING, EngineState.RECORDING)) {
                        closeSession(); state(EngineState.STOPPING, app.getString(com.s23log.probe.R.string.resource_stopping, reason))
                    }
                } }, onAudioMeter = { meter -> handler.post {
                    if (recorder === current && state in setOf(EngineState.STARTING, EngineState.RECORDING)) emit { it.onAudioMeter(meter) }
                } }, onAudioFault = { message -> handler.post {
                    if (recorder === current) {
                        closeSession()
                        state(EngineState.STOPPING, "Audio capture failed; draining retained footage")
                        emit { it.onAudioError(message) }
                    }
                } }, onFirstSample = { handler.post {
                    if (recorder === current && state == EngineState.STARTING && wanted != null) {
                        state(EngineState.RECORDING, "Recording ${mode.label} · ${if (audioMode.enabled) "AAC ${audioMode.channels}ch / 48 kHz" else "video only"}" +
                            if (!mode.previewDuringRecording) "; SDR preview suspended for HDR compatibility" else "")
                        if (testSeconds != null) handler.postDelayed({
                            if (recorder === current && state == EngineState.RECORDING) stopRecording()
                        }, testSeconds * 1000L)
                    }
                } }) { outcome -> handler.post completion@{
                    if (recorder !== current) return@completion
                    recorder = null
                    releaseRetiredTextures()
                    closeSession()
                    emit { it.onVideo(outcome) }
                    resumeOrClose()
                } }
                val prepared = requireNotNull(current)
                recorder = prepared
                fun createRecordingSession(input: Surface) {
                    if (recorder !== prepared || state != EngineState.STARTING || wanted == null) return
                    val cameraOutput = output(input, mode.colour.inputProfile).apply {
                        if (Build.VERSION.SDK_INT >= 33) timestampBase = OutputConfiguration.TIMESTAMP_BASE_MONOTONIC
                    }
                    val outputs = mutableListOf(cameraOutput)
                    if (mode.processing == ProcessingPath.DIRECT && mode.previewDuringRecording)
                        outputs += output(requireNotNull(previewSurface), DynamicRange.SDR)
                    configure(outputs, {
                        repeat(controls)
                        prepared.sessionStarted()
                        state(EngineState.STARTING, "Camera configured; waiting for ${if (audioMode.enabled) "video and audio samples" else "encoded footage"}…")
                    }, { message -> prepared.cancel(message) })
                }
                if (mode.processing == ProcessingPath.DIRECT) createRecordingSession(prepared.surface)
                else afterPreviewClosed(prepared) {
                    val preview = previewSurface
                    if (preview == null) prepared.cancel("Preview surface disappeared before GPU setup")
                    else prepared.prepareCameraInput(preview, CameraCatalog.previewSize(request.target, mode), monitorTransform,
                        ready = { input -> handler.post { createRecordingSession(input) } }, fault = { message -> handler.post {
                            if (recorder === prepared) {
                                closeSession(); state(EngineState.STOPPING, message)
                            }
                        } })
                }
            } catch (e: Exception) {
                val active = recorder
                if (active != null) active.cancel("Recording configuration failed: ${e.message}")
                else {
                    emit {
                        it.onState(EngineState.PREVIEW, "Recording unavailable: ${e.message}")
                        if (e is RecordingResources.PreflightRejected) it.onResources(e.snapshot)
                        else if (audioMode.enabled) it.onAudioError("Recording setup failed: ${e.message}. Audio was not disabled.")
                    }
                    configurePreview()
                }
            }
        }
    }
    fun stopRecording() {
        val cutoffNs = System.nanoTime()
        handler.post {
            val active = recorder ?: return@post
            active.requestStopBoundary(cutoffNs)
            closeSession()
            state(EngineState.STOPPING, "Finalizing video and checking output…")
            active.finish(cutoffNs)
        }
    }
    fun captureRaw(count: Int) {
        handler.post {
            if (state != EngineState.PREVIEW || recorder != null || raw != null) return@post
            val request = wanted ?: return@post
            try {
                val orientation = CapturePolicy.orientation(request.target.characteristics[C.SENSOR_ORIENTATION] ?: 0, request.displayDegrees, request.target.front)
                state(EngineState.RAW, "Preparing $count sequential RAW still capture(s)…")
                var job: RawCapture? = null
                job = RawCapture(app, request.target, controls, orientation, count, handler, io,
                    { message -> if (raw === job) state(EngineState.RAW, message) },
                    { result ->
                        if (raw === job) {
                            raw = null
                            closeSession()
                            emit { it.onRaw(result) }
                            resumeOrClose()
                        }
                    })
                val prepared = requireNotNull(job)
                raw = prepared
                configure(listOf(output(prepared.surface, DynamicRange.SDR)), {
                    prepared.start(requireNotNull(device), requireNotNull(session))
                }, { message -> prepared.cancel(message) })
            } catch (e: Exception) {
                raw?.cancel("RAW unavailable: ${e.message}") ?: run { emit { it.onState(state, "RAW unavailable: ${e.message}") }; configurePreview() }
            }
        }
    }
    fun close() { handler.post { wanted = null; teardown(); maybeQuit() } }
    fun detachTexture(texture: SurfaceTexture) {
        if (!handler.post {
            if (wanted?.texture === texture) { wanted = null; teardown() }
            if (recorder?.mode?.processing == ProcessingPath.GPU_HLG10) retiredTextures += texture
            else runCatching { texture.release() }
            maybeQuit()
        }) runCatching { texture.release() }
    }
    fun release() {
        listener = null
        handler.post { releasing = true; wanted = null; teardown(); maybeQuit() }
    }
    private fun closeSession() {
        manualExposureConfirmed = false
        sessionEpoch.next()
        requestEpoch.next()
        manualJob?.deadline?.let(handler::removeCallbacks)
        manualJob = null
        val old = session
        session = null
        if (old != null) { runCatching { old.stopRepeating() }; runCatching { old.abortCaptures() }; old.close() }
    }
    private fun closeDevice(camera: CameraDevice) {
        if (closing.add(camera)) camera.close()
    }
    private fun teardown() {
        val cutoffNs = System.nanoTime()
        recorder?.requestStopBoundary(cutoffNs)
        deviceEpoch.next()
        closeSession()
        device?.let(::closeDevice)
        device = null
        previewSurface?.release()
        previewSurface = null
        modes = emptyList()
        selectedMode = null
        afterFirstPreview = null
        raw?.cancel("Camera closed; unfinished RAW capture cancelled")
        if (recorder != null) {
            state(EngineState.STOPPING, "Camera closed; finalizing any recorded frames…")
            recorder?.finish(cutoffNs)
        } else if (raw == null) state(EngineState.CLOSED, "Camera closed")
    }
    private fun resumeOrClose() {
        if (wanted != null && !releasing && device != null) configurePreview()
        else if (wanted != null && !releasing) reconcile()
        else { state(EngineState.CLOSED, "Camera closed"); maybeQuit() }
    }
    private fun maybeQuit() {
        releaseRetiredTextures()
        if (releasing && device == null && openingToken == null && closing.isEmpty() && recorder == null && raw == null) {
            io.shutdown()
            thread.quitSafely()
        }
    }
    private fun reconcile() {
        if (releasing) { maybeQuit(); return }
        val request = wanted ?: return
        if (openingToken != null || closing.isNotEmpty() || recorder != null || raw != null || device != null) return
        if (app.checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            fail("Camera permission is required"); return
        }
        try {
            val plan = runCatching { CameraCatalog.plan(request.target) }.getOrElse { ModePlan(emptyList(), listOf("Recording-mode query failed: ${it.message}")) }
            modes = plan.modes
            selectedMode = modes.firstOrNull { it.key == request.modeKey || it.legacyKey == request.modeKey }
                ?: modes.firstOrNull { !it.ratePlan.requiresManual } ?: modes.firstOrNull()
            val size = CameraCatalog.previewSize(request.target, selectedMode)
            request.texture.setDefaultBufferSize(size.width, size.height)
            previewSurface = Surface(request.texture)
            val mode = selectedMode
            emit { it.onReady(request.target, size, plan, mode) }
            state(EngineState.OPENING, "Opening ${request.target.label}…")
            val token = deviceEpoch.next()
            openingToken = token
            manager.openCamera(request.target.logicalId, object : CameraDevice.StateCallback() {
                override fun onOpened(camera: CameraDevice) {
                    if (openingToken == token) openingToken = null
                    if (!deviceEpoch.isCurrent(token) || wanted == null || releasing) { closeDevice(camera); return }
                    device = camera
                    configurePreview()
                }
                override fun onDisconnected(camera: CameraDevice) {
                    if (openingToken == token) openingToken = null
                    if (deviceEpoch.isCurrent(token)) fail("Camera disconnected")
                    closeDevice(camera)
                }
                override fun onError(camera: CameraDevice, error: Int) {
                    if (openingToken == token) openingToken = null
                    if (deviceEpoch.isCurrent(token)) fail("Camera open/runtime error $error")
                    closeDevice(camera)
                }
                override fun onClosed(camera: CameraDevice) { closing.remove(camera); reconcile(); maybeQuit() }
            }, handler)
        } catch (e: Exception) { openingToken = null; fail("Camera unavailable: ${e.message}") }
    }
    private fun fail(message: String) {
        wanted = null
        teardown()
        state(EngineState.ERROR, message)
        maybeQuit()
    }
    private fun output(surface: Surface, range: DynamicRange): OutputConfiguration = OutputConfiguration(surface).apply {
        if (Build.VERSION.SDK_INT >= 28) wanted?.target?.physicalId?.let { setPhysicalCameraId(it) }
        if (Build.VERSION.SDK_INT >= 33) dynamicRangeProfile = if (range == DynamicRange.HLG10) DynamicRangeProfiles.HLG10 else DynamicRangeProfiles.STANDARD
        else require(range == DynamicRange.SDR) { "HDR camera output requires API 33+" }
    }
    @Suppress("DEPRECATION")
    private fun configure(outputs: List<OutputConfiguration>, ready: () -> Unit, failed: (String) -> Unit) {
        closeSession()
        val token = sessionEpoch.current()
        val camera = device ?: run { failed("Camera closed before session creation"); return }
        try {
            camera.createCaptureSessionByOutputConfigurations(outputs, object : CameraCaptureSession.StateCallback() {
                override fun onConfigured(created: CameraCaptureSession) {
                    if (!sessionEpoch.isCurrent(token) || device !== camera || wanted == null) { created.close(); return }
                    session = created
                    try { ready() } catch (e: Exception) { closeSession(); failed("Capture request rejected: ${e.message}") }
                }
                override fun onClosed(created: CameraCaptureSession) { closeWaiters.remove(created)?.invoke() }
                override fun onConfigureFailed(created: CameraCaptureSession) {
                    created.close()
                    if (sessionEpoch.isCurrent(token)) { closeSession(); failed("Camera rejected this output combination; no format downgrade was performed") }
                }
            }, handler)
            handler.postDelayed({
                if (sessionEpoch.isCurrent(token) && session == null) { closeSession(); failed("Capture-session configuration timed out") }
            }, 10_000)
        } catch (e: Exception) { closeSession(); failed("Session creation failed: ${e.message}") }
    }
    private fun configurePreview() {
        if (wanted == null || device == null || previewSurface == null || recorder != null || raw != null || releasing) return
        previewHasFrames = false
        configure(listOf(output(requireNotNull(previewSurface), DynamicRange.SDR)), {
            afterFirstPreview = intentControls.takeIf { it.manualExposure }
            controls = if (afterFirstPreview != null) intentControls.copy(manualExposure = false, wbLock = false) else intentControls
            previewControlWarning = null
            try { repeat(controls) } catch (e: Exception) {
                // Persisted intent is not a guarantee that a route/firmware still accepts it.
                afterFirstPreview = null
                controls = CameraControls(); intentControls = controls
                repeat(controls)
                previewControlWarning = "Saved controls unavailable: ${e.message}. Auto defaults restored."
                changedControls(controls)
            }
            // onConfigured proves configuration only. Recording and control changes
            // become available in onCaptureCompleted after this session delivers a frame.
            state(EngineState.OPENING, "Preview configured; waiting for sensor frames")
            val token = sessionEpoch.current()
            handler.postDelayed({ if (sessionEpoch.isCurrent(token) && !previewHasFrames && state == EngineState.OPENING) fail("Preview session produced no frames") }, 10_000)
        }, ::fail)
    }
    private fun repeat(value: CameraControls, afTrigger: Int? = null) {
        manualExposureConfirmed = false
        val camera = requireNotNull(device)
        val target = requireNotNull(wanted).target
        val activeRecorder = recorder
        val mode = activeRecorder?.mode ?: selectedMode
        val fps = mode?.fps?.takeUnless { mode.ratePlan.requiresManual && !value.manualExposure }
        val effective = value.effective(target, fps)
        val builder = target.request(camera, if (activeRecorder == null) CameraDevice.TEMPLATE_PREVIEW else CameraDevice.TEMPLATE_RECORD).apply {
            if (activeRecorder == null || (activeRecorder.mode.processing == ProcessingPath.DIRECT && activeRecorder.mode.previewDuringRecording)) addTarget(requireNotNull(previewSurface))
            activeRecorder?.let { addTarget(it.cameraSurface) }
            // Manual-only modes use ordinary AE preview while converging focus/WB;
            // do not send a fictitious fixed AE range before manual controls are active.
            value.apply(this, target, fps, mode?.ratePlan)
            target.set(this, CaptureRequest.CONTROL_AF_TRIGGER, CaptureRequest.CONTROL_AF_TRIGGER_IDLE)
        }
        val token = sessionEpoch.current()
        val requestToken = requestEpoch.next()
        val callback = object : CameraCaptureSession.CaptureCallback() {
            override fun onCaptureCompleted(s: CameraCaptureSession, request: CaptureRequest, result: TotalCaptureResult) {
                if (!sessionEpoch.isCurrent(token) || !requestEpoch.isCurrent(requestToken) || session !== s) return
                if (!previewHasFrames && activeRecorder == null) {
                    previewHasFrames = true
                    afterFirstPreview?.let { restore ->
                        afterFirstPreview = null
                        try { beginManual(restore) } catch (e: Exception) {
                            intentControls = controls
                            changedControls(controls)
                            state(EngineState.PREVIEW, "Restored manual controls unavailable: ${e.message}. Auto exposure remains active.")
                        }
                        return // Restored manual intent is not ready until its locks are confirmed.
                    }
                    state(EngineState.PREVIEW, "Live preview · SDR · " + (if (selectedMode?.ratePlan?.requiresManual == true && !controls.manualExposure)
                        "manual timing requires applied manual exposure" else "${selectedMode?.fps ?: "auto"} fps target") + " · no Log transform" +
                        (previewControlWarning?.let { ". $it" } ?: ""))
                }
                val actual = if (target.physicalId != null && Build.VERSION.SDK_INT >= 28) result.physicalCameraResults[target.physicalId] else result
                advanceManual(actual)
                if (!requestEpoch.isCurrent(requestToken)) return
                val manualResult = if (value.manualExposure) ManualResultPolicy.assess(effective.iso, effective.exposureNs,
                    fps?.let { 1_000_000_000L / it }, actual?.get(CaptureResult.SENSOR_SENSITIVITY),
                    actual?.get(CaptureResult.SENSOR_EXPOSURE_TIME), actual?.get(CaptureResult.SENSOR_FRAME_DURATION),
                    actual?.get(CaptureResult.CONTROL_AE_MODE) == CaptureRequest.CONTROL_AE_MODE_OFF) else null
                val previouslyConfirmed = manualExposureConfirmed
                manualExposureConfirmed = manualResult?.matched == true
                if (value.manualExposure && manualJob == null && state == EngineState.PREVIEW && previouslyConfirmed != manualExposureConfirmed) {
                    state(EngineState.PREVIEW, if (manualExposureConfirmed) "Live preview · manual sensor settings match the effective request within documented tolerances"
                        else "Manual sensor settings differ from the request; inspect the applied values")
                }
                val values = mapOf<String, Any?>(
                    "metadataCamera" to (if (actual == null) "physical metadata unavailable" else target.key),
                    "iso" to actual?.get(CaptureResult.SENSOR_SENSITIVITY),
                    "exposureNs" to actual?.get(CaptureResult.SENSOR_EXPOSURE_TIME),
                    "focusDiopters" to actual?.get(CaptureResult.LENS_FOCUS_DISTANCE),
                    "awbMode" to actual?.get(CaptureResult.CONTROL_AWB_MODE),
                    "awbState" to actual?.get(CaptureResult.CONTROL_AWB_STATE),
                    "awbLock" to actual?.get(CaptureResult.CONTROL_AWB_LOCK),
                    "aeMode" to actual?.get(CaptureResult.CONTROL_AE_MODE),
                    "afMode" to actual?.get(CaptureResult.CONTROL_AF_MODE),
                    "afState" to actual?.get(CaptureResult.CONTROL_AF_STATE),
                    "nominalFps" to (activeRecorder?.mode?.fps ?: selectedMode?.fps),
                    "rateControl" to (activeRecorder?.mode ?: selectedMode)?.ratePlan?.control?.name,
                    "manualRequested" to value.manualExposure,
                    "manualExposureConfirmed" to manualExposureConfirmed,
                    "manualControlMatch" to manualResult?.describe(),
                    "requestedIso" to value.iso, "requestedExposureNs" to value.exposureNs,
                    "manualTimingActive" to (manualExposureConfirmed && fps != null),
                    "frameDurationNs" to actual?.get(CaptureResult.SENSOR_FRAME_DURATION),
                    "sensorTimestampNs" to actual?.get(CaptureResult.SENSOR_TIMESTAMP)
                )
                activeRecorder?.noteApplied(values)
                val now = SystemClock.elapsedRealtime()
                if (now - lastAppliedAt > 250) { lastAppliedAt = now; emit { it.onApplied(values) } }
            }
            override fun onCaptureFailed(s: CameraCaptureSession, request: CaptureRequest, failure: CaptureFailure) {
                if (sessionEpoch.isCurrent(token) && requestEpoch.isCurrent(requestToken)) emit { it.onState(state, "A capture request failed (${failure.reason}); inspect output timing evidence") }
            }
        }
        val activeSession = requireNotNull(session)
        activeSession.setRepeatingRequest(builder.build(), callback, handler)
        val chosenAf = if (target.physicalId != null && CaptureRequest.CONTROL_AF_MODE in target.physicalKeys && Build.VERSION.SDK_INT >= 28)
            builder.getPhysicalCameraKey(CaptureRequest.CONTROL_AF_MODE, target.physicalId) else builder.get(CaptureRequest.CONTROL_AF_MODE)
        val trigger = afTrigger ?: if (chosenAf == CaptureRequest.CONTROL_AF_MODE_AUTO && !value.manualExposure) CaptureRequest.CONTROL_AF_TRIGGER_START else null
        if (trigger != null) {
            target.set(builder, CaptureRequest.CONTROL_AF_TRIGGER, trigger)
            activeSession.capture(builder.build(), callback, handler)
        }
    }
}
