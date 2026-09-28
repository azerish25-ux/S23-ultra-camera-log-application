package com.s23log.probe.camera

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
        fun onReady(target: CameraTarget, previewSize: Size, plan: ModePlan)
        fun onState(state: EngineState, message: String)
        fun onApplied(values: Map<String, Any?>)
        fun onVideo(outcome: SurfaceRecorder.Outcome)
        fun onRaw(outcome: RawCapture.Outcome)
    }
    private data class PreviewRequest(val target: CameraTarget, val texture: SurfaceTexture, val displayDegrees: Int)
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
    private var recorder: SurfaceRecorder? = null
    private var raw: RawCapture? = null
    private var modes: List<RecordingMode> = emptyList()
    private var lastAppliedAt = 0L
    private var previewHasFrames = false

    private fun emit(block: (Listener) -> Unit) { main.post { listener?.let(block) } }
    private fun state(next: EngineState, message: String) { state = next; emit { it.onState(next, message) } }
    fun discover() { handler.post { if (!releasing) { val result = CameraCatalog.discover(manager); emit { it.onCatalog(result) } } } }
    fun open(target: CameraTarget, texture: SurfaceTexture, displayDegrees: Int) {
        handler.post {
            if (releasing) return@post
            wanted = null
            teardown()
            controls = CameraControls()
            wanted = PreviewRequest(target, texture, displayDegrees)
            reconcile()
        }
    }
    fun applyControls(value: CameraControls) {
        handler.post {
            if (state != EngineState.PREVIEW && state != EngineState.RECORDING) return@post
            try { repeat(value); controls = value }
            catch (e: Exception) { emit { it.onState(state, "Controls rejected: ${e.message}") } }
        }
    }
    fun startRecording(mode: RecordingMode) {
        handler.post {
            if (!CapturePolicy.canStartRecording(state) || recorder != null || raw != null) return@post
            val request = wanted ?: return@post
            if (modes.none { it.key == mode.key }) { emit { it.onState(state, "Mode was not planned for this camera") }; return@post }
            try {
                state(EngineState.STARTING, "Configuring ${mode.label}. Video only; not custom Log.")
                val orientation = CapturePolicy.orientation(request.target.characteristics[C.SENSOR_ORIENTATION] ?: 0, request.displayDegrees, request.target.front)
                var current: SurfaceRecorder? = null
                current = SurfaceRecorder.prepare(app, mode, orientation, mapOf(
                    "logicalCamera" to request.target.logicalId, "physicalCamera" to request.target.physicalId,
                    "controls" to controls.describe(), "nominalFps" to mode.fps, "bitrate" to mode.bitRate,
                    "cameraTimingAdvertised" to mode.timingAdvertised, "previewDuringRecording" to mode.previewDuringRecording
                )) { outcome -> handler.post completion@{
                    if (recorder !== current) return@completion
                    recorder = null
                    closeSession()
                    emit { it.onVideo(outcome) }
                    resumeOrClose()
                } }
                val prepared = requireNotNull(current)
                recorder = prepared
                val outputs = mutableListOf(output(prepared.surface, mode.range))
                if (mode.previewDuringRecording) outputs += output(requireNotNull(previewSurface), DynamicRange.SDR)
                configure(outputs, {
                    repeat(controls)
                    prepared.sessionStarted()
                    state(EngineState.RECORDING, "Recording ${mode.label} · video only" + if (!mode.previewDuringRecording) "; SDR preview suspended for HDR compatibility" else "")
                }, { message -> prepared.cancel(message) })
            } catch (e: Exception) {
                val active = recorder
                if (active != null) active.cancel("Recording configuration failed: ${e.message}")
                else { emit { it.onState(EngineState.PREVIEW, "Recording unavailable: ${e.message}") }; configurePreview() }
            }
        }
    }
    fun stopRecording() {
        handler.post {
            val active = recorder ?: return@post
            closeSession()
            state(EngineState.STOPPING, "Finalizing video and checking output…")
            active.finish()
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
            runCatching { texture.release() }
            maybeQuit()
        }) runCatching { texture.release() }
    }
    fun release() {
        listener = null
        handler.post { releasing = true; wanted = null; teardown(); maybeQuit() }
    }
    private fun closeSession() {
        sessionEpoch.next()
        val old = session
        session = null
        if (old != null) { runCatching { old.stopRepeating() }; runCatching { old.abortCaptures() }; old.close() }
    }
    private fun closeDevice(camera: CameraDevice) {
        if (closing.add(camera)) camera.close()
    }
    private fun teardown() {
        deviceEpoch.next()
        closeSession()
        device?.let(::closeDevice)
        device = null
        previewSurface?.release()
        previewSurface = null
        modes = emptyList()
        raw?.cancel("Camera closed; unfinished RAW capture cancelled")
        if (recorder != null) {
            state(EngineState.STOPPING, "Camera closed; finalizing any recorded frames…")
            recorder?.finish()
        } else if (raw == null) state(EngineState.CLOSED, "Camera closed")
    }
    private fun resumeOrClose() {
        if (wanted != null && !releasing && device != null) configurePreview()
        else if (wanted != null && !releasing) reconcile()
        else { state(EngineState.CLOSED, "Camera closed"); maybeQuit() }
    }
    private fun maybeQuit() {
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
            val size = CameraCatalog.previewSize(request.target)
            request.texture.setDefaultBufferSize(size.width, size.height)
            previewSurface = Surface(request.texture)
            val plan = runCatching { CameraCatalog.plan(request.target) }.getOrElse { ModePlan(emptyList(), listOf("Recording-mode query failed: ${it.message}")) }
            modes = plan.modes
            emit { it.onReady(request.target, size, plan) }
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
            repeat(controls)
            state(EngineState.PREVIEW, "Preview configured; waiting for sensor frames")
            val token = sessionEpoch.current()
            handler.postDelayed({ if (sessionEpoch.isCurrent(token) && !previewHasFrames && state == EngineState.PREVIEW) fail("Preview session produced no frames") }, 10_000)
        }, ::fail)
    }
    private fun repeat(value: CameraControls) {
        val camera = requireNotNull(device)
        val target = requireNotNull(wanted).target
        val activeRecorder = recorder
        val request = camera.createCaptureRequest(if (activeRecorder == null) CameraDevice.TEMPLATE_PREVIEW else CameraDevice.TEMPLATE_RECORD).apply {
            if (activeRecorder == null || activeRecorder.mode.previewDuringRecording) addTarget(requireNotNull(previewSurface))
            activeRecorder?.let { addTarget(it.surface) }
            value.apply(this, target, activeRecorder?.mode?.fps ?: 30)
        }.build()
        val token = sessionEpoch.current()
        requireNotNull(session).setRepeatingRequest(request, object : CameraCaptureSession.CaptureCallback() {
            override fun onCaptureCompleted(s: CameraCaptureSession, request: CaptureRequest, result: TotalCaptureResult) {
                if (!sessionEpoch.isCurrent(token) || session !== s) return
                if (!previewHasFrames && activeRecorder == null) { previewHasFrames = true; state(EngineState.PREVIEW, "Live preview · SDR · no Log transform") }
                val actual = if (target.physicalId != null && Build.VERSION.SDK_INT >= 28) result.physicalCameraResults[target.physicalId] else result
                val values = mapOf<String, Any?>(
                    "metadataCamera" to (if (actual == null) "physical metadata unavailable" else target.key),
                    "iso" to actual?.get(CaptureResult.SENSOR_SENSITIVITY),
                    "exposureNs" to actual?.get(CaptureResult.SENSOR_EXPOSURE_TIME),
                    "focusDiopters" to actual?.get(CaptureResult.LENS_FOCUS_DISTANCE),
                    "awbMode" to actual?.get(CaptureResult.CONTROL_AWB_MODE),
                    "awbState" to actual?.get(CaptureResult.CONTROL_AWB_STATE),
                    "frameDurationNs" to actual?.get(CaptureResult.SENSOR_FRAME_DURATION),
                    "sensorTimestampNs" to actual?.get(CaptureResult.SENSOR_TIMESTAMP)
                )
                activeRecorder?.noteApplied(values)
                val now = SystemClock.elapsedRealtime()
                if (now - lastAppliedAt > 250) { lastAppliedAt = now; emit { it.onApplied(values) } }
            }
            override fun onCaptureFailed(s: CameraCaptureSession, request: CaptureRequest, failure: CaptureFailure) {
                if (sessionEpoch.isCurrent(token)) emit { it.onState(state, "A capture request failed (${failure.reason}); inspect output timing evidence") }
            }
        }, handler)
    }
}
