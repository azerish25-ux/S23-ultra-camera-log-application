package com.s23log.probe.gpu

import android.annotation.TargetApi
import android.graphics.SurfaceTexture
import android.hardware.DataSpace
import android.opengl.EGL14
import android.opengl.EGLSurface
import android.opengl.EGLExt
import android.opengl.GLES11Ext
import android.opengl.GLES30 as GL
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.util.Size
import android.view.Surface
import com.s23log.probe.core.MonitorTransform
import com.s23log.probe.core.ProcessingFrameClock
import com.s23log.probe.core.RecordingMode
import java.util.concurrent.atomic.AtomicBoolean

/** Dedicated GPU owner. The display has its own context/worker and cannot backlog recording buffers. */
@TargetApi(33)
class GpuVideoProcessor private constructor(private val mode: RecordingMode, private val encoderSurface: Surface,
    private val displaySurface: Surface, private val monitorSize: Size, private val callbackHandler: Handler,
    private val ready: (Surface) -> Unit, private val failed: (String) -> Unit) {
    private val thread = HandlerThread("S23Log-colour").apply { start() }
    private val handler = Handler(thread.looper)
    private var egl: GlEnvironment? = null
    private var encoderWindow: EGLSurface = EGL14.EGL_NO_SURFACE
    private var renderer: ColourRenderer? = null
    private var monitor: GpuMonitor? = null
    private var texture: SurfaceTexture? = null
    private var inputSurface: Surface? = null
    private var inputTexture = 0
    private val frameClock = ProcessingFrameClock(mode.fps)
    private val transform = FloatArray(16)
    private val renderQueued = AtomicBoolean()
    private val stopRequested = AtomicBoolean()
    private var finishing = false
    private var closed = false
    private var lastTimestamp = 0L
    private var maxProcessingNs = 0L
    private var submitted = 0L
    private var lastDataSpace: Int? = null
    private var fault: String? = null
    private var gpuEvidence: Map<String, Any> = emptyMap()
    private var precision: Map<String, Any> = emptyMap()
    @Volatile private var viewing = MonitorTransform.SDR_TONEMAP
    @Volatile private var snapshot: Map<String, Any?> = mapOf("status" to "initializing", "customLog" to false)
    private val closeCallbacks = mutableListOf<(String?) -> Unit>()

    private fun initialize() {
        if (stopRequested.get()) { dispose(); return }
        try {
            require(Build.VERSION.SDK_INT >= 33) { "GPU HLG requires API 33+" }
            val environment = GlEnvironment.create(rgb10 = true); egl = environment
            gpuEvidence = environment.describe()
            precision = ColourGpuProbe.run() // 1024-pixel setup fixture, never full-resolution live readback.
            encoderWindow = environment.window(encoderSurface, hlg = true)
            renderer = ColourRenderer(mode.width, mode.height, externalYuv = true)
            val id = IntArray(1); GL.glGenTextures(1,id,0); inputTexture=id[0]
            GL.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,inputTexture)
            GL.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,GL.GL_TEXTURE_MIN_FILTER,GL.GL_LINEAR)
            GL.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,GL.GL_TEXTURE_MAG_FILTER,GL.GL_LINEAR)
            GL.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,GL.GL_TEXTURE_WRAP_S,GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,GL.GL_TEXTURE_WRAP_T,GL.GL_CLAMP_TO_EDGE)
            GlTools.check("external camera texture")
            val cameraTexture = SurfaceTexture(inputTexture).apply { setDefaultBufferSize(mode.width,mode.height) }
            texture=cameraTexture; inputSurface=Surface(cameraTexture)
            // Native frame notifications carry no copied frames; our scheduled render is coalesced.
            cameraTexture.setOnFrameAvailableListener({
                if(!stopRequested.get() && renderQueued.compareAndSet(false,true)) handler.post {
                    renderQueued.set(false)
                    if(!stopRequested.get() && !closed) render()
                }
            }, callbackHandler)
            monitor = GpuMonitor(environment,displaySurface,monitorSize,handler,{ error ->
                if(error!=null) fault(error) else if(!stopRequested.get()) {
                    updateEvidence("ready")
                    callbackHandler.post { if(!stopRequested.get()) ready(requireNotNull(inputSurface)) }
                }
            },::fault)
        } catch(e:Exception) { fault("GPU colour setup rejected: ${e.message}") }
    }
    private fun render() {
        try {
            val environment=requireNotNull(egl); environment.current()
            val cameraTexture=requireNotNull(texture); cameraTexture.updateTexImage()
            val timestamp=cameraTexture.timestamp
            if(timestamp==lastTimestamp) return // Multiple notifications can describe the same newest buffer.
            val dataSpace=cameraTexture.dataSpace
            require(DataSpace.getStandard(dataSpace)==DataSpace.STANDARD_BT2020 &&
                DataSpace.getTransfer(dataSpace)==DataSpace.TRANSFER_HLG &&
                DataSpace.getRange(dataSpace) in setOf(DataSpace.RANGE_LIMITED,DataSpace.RANGE_FULL)) {
                "Camera supplied dataspace $dataSpace, not explicit full/limited BT.2020 HLG; no guessed conversion performed"
            }
            if(!frameClock.accept(timestamp,System.nanoTime())) return
            lastTimestamp=timestamp;lastDataSpace=dataSpace
            val began=System.nanoTime()
            cameraTexture.getTransformMatrix(transform)
            requireNotNull(renderer).import(inputTexture,transform,fullRange=DataSpace.getRange(dataSpace)==DataSpace.RANGE_FULL)
            environment.current(encoderWindow)
            requireNotNull(renderer).record()
            check(EGLExt.eglPresentationTimeANDROID(environment.display,encoderWindow,timestamp)) { "Encoder presentation timestamp rejected" }
            check(EGL14.eglSwapBuffers(environment.display,encoderWindow)) { "Encoder surface swap failed" }
            submitted++
            // Display work uses independent bounded textures. If all are busy, skip only the preview update.
            environment.current()
            monitor?.offer(requireNotNull(renderer),viewing)
            maxProcessingNs=maxOf(maxProcessingNs,System.nanoTime()-began)
            updateEvidence("running")
        } catch(e:Exception) { fault("GPU recording stopped: ${e.message}") }
    }
    fun setMonitor(transform: MonitorTransform) { viewing=transform }
    fun requestStop() { stopRequested.set(true) }
    fun describe(): Map<String, Any?> = snapshot
    fun close(callback: (String?) -> Unit) {
        stopRequested.set(true)
        if (!handler.post {
            if(closed) { callbackHandler.post { callback(fault) }; return@post }
            closeCallbacks += callback
            if(!finishing) {
                finishing=true;frameClock.stop();texture?.setOnFrameAvailableListener(null)
                val active=monitor
                if(active==null) dispose() else active.close { error ->
                    if(error!=null && fault==null) fault=error
                    dispose()
                }
            }
        }) callbackHandler.post { callback(if (closed) fault else "GPU owner is unavailable") }
    }
    private fun fault(message: String) {
        if(fault!=null || closed) return
        fault=message;stopRequested.set(true);updateEvidence("failed")
        callbackHandler.post { failed(message) }
    }
    private fun updateEvidence(status:String) {
        snapshot=mapOf("schemaVersion" to 1,"status" to status,"configuration" to mode.colour.describe(),
            "gpu" to gpuEvidence,"setupPrecisionProbe" to precision,"inputDataSpace" to lastDataSpace,
            "inputConversion" to "GL_EXT_YUV_target_explicit_BT2020_range_from_dataspace",
            "workingStorage" to "RGBA16F","encoderInputStorage" to "RGBA_1010102",
            "encoderInputColourspace" to "BT2020_HLG","recordingTransform" to "HLG_inverse_then_HLG_forward",
            "monitorTransform" to viewing.name,"monitor" to monitor?.describe(),"clock" to frameClock.describe(),
            "submittedFrames" to submitted,"maximumProcessingNs" to maxProcessingNs,"cleanupConfirmed" to closed,
            "error" to fault,"customLog" to false,"cameraInputPrecisionMeasured" to false,
            "cameraColourCertified" to false,"outputRgbRange" to "0_to_1_clamped_by_RGB10",
            "losslessIdentityClaimed" to false,"liveCpuPixelReadbacks" to 0)
    }
    private fun dispose() {
        if(closed) return
        var error=fault
        fun attempt(block:()->Unit) { try{block()}catch(e:Exception){if(error==null)error=e.message?:e.toString()} }
        attempt { egl?.current() }
        attempt { texture?.setOnFrameAvailableListener(null); inputSurface?.release(); texture?.release() }
        attempt { renderer?.close() }
        attempt { if(inputTexture!=0)GL.glDeleteTextures(1,intArrayOf(inputTexture),0) }
        attempt { egl?.destroy(encoderWindow); egl?.close() }
        closed=true;fault=error;updateEvidence(if(error==null)"closed" else "failed")
        val callbacks=closeCallbacks.toList();closeCallbacks.clear()
        callbacks.forEach { c -> callbackHandler.post { c(error) } }
        thread.quitSafely()
    }
    companion object {
        fun prepare(mode:RecordingMode,encoder:Surface,preview:Surface,previewSize:Size,callbacks:Handler,
                    monitor:MonitorTransform,ready:(Surface)->Unit,failed:(String)->Unit):GpuVideoProcessor =
            GpuVideoProcessor(mode,encoder,preview,previewSize,callbacks,ready,failed).also {
                it.viewing=monitor;it.handler.post(it::initialize)
            }
    }
}

/** Three small display buffers. Slot ownership ends only after the monitor GPU has finished sampling. */
private class GpuMonitor(private val parent:GlEnvironment,private val target:Surface,private val size:Size,
    private val producer:Handler,private val initialized:(String?)->Unit,private val failed:(String)->Unit) {
    private class Slot(val texture:Int,val fbo:Int) { val busy=AtomicBoolean() }
    private val slots=ArrayList<Slot>()
    private val thread=HandlerThread("S23Log-monitor").apply { start() }
    private val handler=Handler(thread.looper)
    private var egl:GlEnvironment?=null
    private var window=EGL14.EGL_NO_SURFACE
    private var program=0
    private val stopping=AtomicBoolean()
    @Volatile private var ready=false
    @Volatile private var displayed=0L
    private var skipped=0L
    @Volatile private var fault:String?=null
    init {
        try {
            repeat(3) {
                val texture=GlTools.texture(size.width,size.height,GL.GL_RGBA8)
                try { slots+=Slot(texture,GlTools.fbo(texture)) } catch(e:Exception) { GL.glDeleteTextures(1,intArrayOf(texture),0);throw e }
            }
            handler.post {
                try {
                    val environment=GlEnvironment.create(share=parent);egl=environment
                    window=environment.window(target,hlg=false);environment.current(window)
                    program=GlTools.program(ColourShaders.copy);ready=true
                    producer.post { initialized(null) }
                } catch(e:Exception) { fault="Independent monitor unavailable: ${e.message}";producer.post { initialized(fault) } }
            }
        } catch(e:Exception) { fault="Monitor buffers unavailable: ${e.message}";producer.post { initialized(fault) } }
    }
    fun offer(renderer:ColourRenderer,transform:MonitorTransform) {
        if(!ready || stopping.get()) { skipped++;return }
        val slot=slots.firstOrNull { it.busy.compareAndSet(false,true) } ?: run { skipped++;return }
        var fence=0L
        try {
            renderer.monitor(slot.fbo,size.width,size.height,transform)
            fence=GL.glFenceSync(GL.GL_SYNC_GPU_COMMANDS_COMPLETE,0);check(fence!=0L);GL.glFlush()
            val sync=fence
            if(!handler.post {
                try {
                    val environment=requireNotNull(egl);environment.current(window)
                    GL.glWaitSync(sync,0,GL.GL_TIMEOUT_IGNORED)
                    if(!stopping.get()) {
                        GlTools.draw(program,slot.texture,0,size.width,size.height)
                        check(EGL14.eglSwapBuffers(environment.display,window)) { "Monitor swap failed" }
                        GL.glFinish();displayed++
                    }
                } catch(e:Exception) { fault="Monitor failed: ${e.message}";producer.post { failed(requireNotNull(fault)) } }
                finally { GL.glDeleteSync(sync);slot.busy.set(false) }
            }) { GL.glDeleteSync(sync);slot.busy.set(false) }
        } catch(e:Exception) { if(fence!=0L)GL.glDeleteSync(fence);slot.busy.set(false);throw e }
    }
    fun describe():Map<String,Any?> = mapOf("independentWorker" to true,"bufferCount" to 3,
        "displayedFrames" to displayed,"skippedPreviewUpdates" to skipped,"error" to fault)
    fun close(done:(String?)->Unit) {
        stopping.set(true)
        handler.post {
            runCatching { egl?.let { it.current();if(program!=0)GL.glDeleteProgram(program);it.destroy(window);it.close() } }
                .onFailure { if(fault==null)fault=it.message }
            producer.post {
                runCatching { parent.current();slots.forEach { GL.glDeleteFramebuffers(1,intArrayOf(it.fbo),0);GL.glDeleteTextures(1,intArrayOf(it.texture),0) } }
                    .onFailure { if(fault==null)fault=it.message }
                slots.clear();done(fault)
            }
            thread.quitSafely()
        }
    }
}
