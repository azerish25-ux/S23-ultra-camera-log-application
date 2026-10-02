package com.s23log.probe.live

import android.Manifest
import android.annotation.SuppressLint
import android.annotation.TargetApi
import android.app.ActivityManager
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.hardware.camera2.*
import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.params.OutputConfiguration
import android.hardware.camera2.params.SessionConfiguration
import android.media.ImageReader
import android.os.*
import android.util.Size
import android.view.Surface
import androidx.core.content.FileProvider
import com.s23log.probe.BuildConfig
import com.s23log.probe.camera.CameraCatalog
import com.s23log.probe.camera.CameraTarget
import com.s23log.probe.core.*
import com.s23log.probe.develop.LogP010Codec
import com.s23log.probe.diagnostics.ModeEvidence
import com.s23log.probe.diagnostics.atomicWrite
import com.s23log.probe.diagnostics.jsonValue
import com.s23log.probe.gpu.GlEnvironment
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.CancellationException
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/** Foreground camera session. A single worker owns GL/encoder input; camera and display have independent owners. */
@TargetApi(33)
class LiveLogSession(context:Context,
    private val gpuProbe: ((() -> Unit) -> JSONObject) = { RawLogGpuProbe.run(it) },
    private val backendProbe: (File,Int,Int,Int,()->Unit,(String)->Unit)->LiveBackendProbe.Result =
        { cache,w,h,fps,check,progress -> LiveBackendProbe.run(cache,w,h,fps,check,progress) },
    private val evidenceWrite: (File,String)->Unit = ::atomicWrite
) {
    data class State(val busy:Boolean=false,val preview:Boolean=false,val recording:Boolean=false,
        val message:String="Experimental live RAW-derived LogC3. Qualify the backend before camera testing.",
        val report:File?=null,val media:File?=null,val error:String?=null,val outputWidth:Int=1920,val outputHeight:Int=1080,
        val attemptReport:File?=null,val evidenceError:String?=null)
    private val app=context.applicationContext
    private val main=Handler(Looper.getMainLooper())
    private val worker=Executors.newSingleThreadExecutor()
    private val observers=linkedSetOf<(State)->Unit>()
    @Volatile var state=State();private set
    private var serial=0L
    private val stop=AtomicBoolean()
    private val startRecord=AtomicBoolean()
    private val recording=AtomicBoolean()
    private val reason=AtomicReference<String?>()
    @Volatile private var monitor:LiveLogMonitor?=null
    @Volatile private var desiredLogView=false
    @Volatile private var stopCamera:(()->Unit)?=null
    val directory=File(app.filesDir,"exports/live-log")
    val evidenceDirectory=File(app.filesDir,"exports/live-evidence")
    @Volatile private var activeAttempt:LiveAttempt?=null
    private fun attempt(kind:LiveAttemptKind,requested:JSONObject,profile:JSONObject?=null):LiveAttempt {
        val payload=profile?.toString()
        val context=JSONObject().put("device",jsonValue(ModeEvidence.device())).put("requested",requested)
            .put("profilePayload",payload ?: JSONObject.NULL)
            .put("profileSha256",payload?.let(com.s23log.probe.develop.DevelopmentAttempt::hash) ?: JSONObject.NULL)
        val attemptSerial=serial
        return LiveAttempt(evidenceDirectory,BuildConfig.SOURCE_REVISION,kind,context,evidenceWrite,ModeEvidence::queueEvidence,
            onPersistenceFailure={message -> main.post { if(attemptSerial==serial)publish(state.copy(evidenceError=message)) }})
            .also { activeAttempt=it;it.start() }
    }
    private fun observeBackend(attempt:LiveAttempt,result:LiveBackendProbe.Result) {
        val outcome=when(result.report.optString("status")) {
            "qualified" -> DevelopmentOutcome.PASSED
            "unavailable" -> DevelopmentOutcome.UNAVAILABLE
            "query_failed" -> DevelopmentOutcome.INCONCLUSIVE
            else -> DevelopmentOutcome.FAILED
        }
        attempt.safe {
            result.selected?.let { attempt.bind("selectedBackend",JSONObject().put("codec",it.codec).put("input",it.input.name)) }
            attempt.observe(LiveStage.BACKEND,outcome,"Actual encoder/decoder route-probe result",JSONObject().put("report",result.report))
        }
    }
    private fun checkRunning() {
        if(stop.get()) {
            val failure=reason.get()
            if(failure==null)throw CancellationException("Live work cancelled before completion")
            else throw IllegalStateException(failure)
        }
        safety()
    }
    fun observe(observer:(State)->Unit){check(Looper.myLooper()==Looper.getMainLooper());observers+=observer;observer(state)}
    fun remove(observer:(State)->Unit){observers-=observer}
    private fun publish(value:State){state=value;observers.toList().forEach{it(value)}}
    private fun update(id:Long,value:State){
        val evidence=activeAttempt
        main.post{if(id==serial)publish(value.copy(attemptReport=evidence?.file,evidenceError=evidence?.persistenceError))}
    }
    fun stop(){if(state.busy){stop.set(true);stopCamera?.invoke()}}
    fun record(){if(state.preview && !recording.get()){
        activeAttempt?.safe { activeAttempt?.requestRecording() };startRecord.set(true)
    }}
    fun viewing(log:Boolean){desiredLogView=log;monitor?.logView=log}
    private fun fail(message:String){reason.compareAndSet(null,message);stop.set(true);stopCamera?.invoke()}
    private fun safety(){
        require(app.filesDir.usableSpace>=128L*1024*1024){"Storage reserve reached"}
        require(app.getSystemService(PowerManager::class.java).currentThermalStatus<PowerManager.THERMAL_STATUS_SEVERE){"Severe thermal pressure; live work stopped"}
    }
    private fun begin(label:String):Long {
        check(Looper.myLooper()==Looper.getMainLooper());check(!state.busy)
        val id=++serial;activeAttempt=null;stop.set(false);recording.set(false);startRecord.set(false);reason.set(null)
        publish(State(busy=true,message=label));return id
    }
    fun testBackend(fps:Int) {
        if(state.busy)return
        val id=begin("Testing GPU arithmetic and independent ten-bit encoder/decoder routes…")
        val evidence=attempt(LiveAttemptKind.BACKEND,JSONObject().put("width",1920).put("height",1080).put("fps",fps))
        worker.execute {
            var file:File?=null
            var error:String?=null
            var message="Backend test did not complete"
            try {
                val check={checkRunning()}
                val gpu=evidence.step(LiveStage.GPU) { f -> gpuProbe(check).also { f.put("report",it) } }
                evidence.safe { evidence.begin(LiveStage.BACKEND) }
                val result=backendProbe(app.cacheDir,1920,1080,fps,check){update(id,State(busy=true,message=it))}
                observeBackend(evidence,result)
                val report=result.report.put("gpuReference",gpu).put("device",jsonValue(ModeEvidence.device()))
                    .put("attemptId",evidence.id).put("attemptReport",evidence.file.name)
                runCatching { directory.mkdirs();file=File(directory,"backend-${evidence.id}.json");atomicWrite(requireNotNull(file),report.toString(2)) }
                    .onFailure { evidence.noteReportError("Backend sidecar: ${it.message}") }
                message=if(result.selected!=null)"Qualified ${result.selected.label} for synthetic 1920×1080/$fps. Physical RAW throughput is unverified."
                    else "No route qualified. The report distinguishes encoder, decoder and precision failures; no SDR fallback was used."
            } catch(e:Exception){
                evidence.safe { evidence.failedActive(e) };error=e.message ?: e.javaClass.simpleName;message=requireNotNull(error)
                runCatching {
                    directory.mkdirs();file=File(directory,"backend-${evidence.id}.json")
                    atomicWrite(requireNotNull(file),JSONObject().put("schemaVersion",1).put("kind","live-log-backend-test")
                        .put("appCommit",BuildConfig.SOURCE_REVISION).put("device",jsonValue(ModeEvidence.device()))
                        .put("attemptId",evidence.id).put("attemptReport",evidence.file.name)
                        .put("status",if(e is CancellationException)"blocked" else "failed").put("reason",error)
                        .put("sensorPrecisionMeasured",false).put("physicalCameraCertified",false).toString(2))
                }.onFailure { evidence.noteReportError("Backend sidecar: ${it.message}") }
            } finally {
                evidence.safe { evidence.close(listOfNotNull(error)) }
                update(id,State(message=message,report=file,error=error))
            }
        }
    }
    private data class Configuration(val target:CameraTarget,val index:RawSourceIndex,val profile:RawColourProfile,
        val output:LiveLogOutput,val fps:Int,val focus:Float,val profileHash:String)
    private fun configure(json:JSONObject,output:LiveLogOutput,fps:Int,focus:Float,allowProvisional:Boolean):Configuration {
        require(app.checkSelfPermission(Manifest.permission.CAMERA)==PackageManager.PERMISSION_GRANTED){"Grant Camera permission before preparing live capture"}
        require(json.getJSONObject("calibration").getString("status")!="synthetic"){"Synthetic profiles cannot be used for a physical camera"}
        val binding=json.getJSONObject("source");require(binding.getString("fingerprint")==Build.FINGERPRINT){"Profile firmware does not match this phone"}
        val manager=app.getSystemService(CameraManager::class.java)
        val physical=if(binding.isNull("physicalCamera"))null else binding.getString("physicalCamera")
        val target=CameraCatalog.discover(manager).targets.firstOrNull {it.logicalId==binding.getString("logicalCamera") && it.physicalId==physical}
            ?: error("The profile's public camera route is not available")
        require(!target.front && target.manualSensor){"First live mode requires a rear camera with explicit manual sensor control"}
        val c=target.characteristics;val w=binding.getInt("width");val h=binding.getInt("height")
        val cfa=requireNotNull(c[C.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT]);require(cfa in 0..3)
        val map=requireNotNull(c[C.SCALER_STREAM_CONFIGURATION_MAP]);val size=Size(w,h)
        require(size in map.getOutputSizes(ImageFormat.RAW_SENSOR).orEmpty()){"RAW source dimensions are not advertised"}
        val frame=map.getOutputMinFrameDuration(ImageFormat.RAW_SENSOR,size)
        require(frame==0L || frame<=1_000_000_000L/fps+1){"Source RAW timing excludes the requested rate"}
        val black=black(c);val white=requireNotNull(c[C.SENSOR_INFO_WHITE_LEVEL])
        val meta=JSONObject().put("iso",json.getLong("iso")).put("exposureNs",json.getLong("exposureNs"))
            .put("blackLevels",JSONArray(black.toList())).put("whiteLevel",white)
        val header=JSONObject().put("width",w).put("height",h).put("cfa",cfa).put("fpsRequested",fps)
            .put("logicalCamera",target.logicalId).put("physicalCamera",physical ?: JSONObject.NULL).put("device",jsonValue(ModeEvidence.device()))
        val index=RawSourceIndex(File(directory,"live-source-not-stored"),header,listOf(RawFrameRef(meta,0,w*h*2)),0,0)
        val profile=RawColourProfile.parse(json,index,allowProvisional)
        require(output in LiveLogOutput.choices(profile.crop) && output.width>=600){"Select an explicitly supported crop/output"}
        val bytes=LiveLogOutput.memoryBytes(w,h,output)
        val memory=ActivityManager.MemoryInfo();app.getSystemService(ActivityManager::class.java).getMemoryInfo(memory)
        require(bytes<=256L*1024*1024 && !memory.lowMemory && memory.availMem>bytes+128L*1024*1024){"Live buffer budget exceeds available memory"}
        val isoRange=requireNotNull(c[C.SENSOR_INFO_SENSITIVITY_RANGE]);val exposureRange=requireNotNull(c[C.SENSOR_INFO_EXPOSURE_TIME_RANGE])
        require(profile.iso in isoRange.lower.toLong()..isoRange.upper.toLong() && profile.exposure in exposureRange.lower..minOf(exposureRange.upper,1_000_000_000L/fps)){
            "Profile ISO/shutter cannot be applied unchanged at the selected rate"
        }
        if(target.minFocus>0)require(target.manualFocus && focus.isFinite() && focus in 0f..target.minFocus){"Set a supported manual focus distance in diopters"}
        val hash=java.security.MessageDigest.getInstance("SHA-256").digest(json.toString().toByteArray()).joinToString(""){"%02x".format(it)}
        return Configuration(target,index,profile,output,fps,focus,hash)
    }
    private fun black(c:C):DoubleArray {
        val p=requireNotNull(c[C.SENSOR_BLACK_LEVEL_PATTERN]){"Black level metadata unavailable"}
        return doubleArrayOf(p.getOffsetForIndex(0,0).toDouble(),p.getOffsetForIndex(1,0).toDouble(),p.getOffsetForIndex(0,1).toDouble(),p.getOffsetForIndex(1,1).toDouble())
    }
    fun prepare(profileJson:JSONObject,output:LiveLogOutput,fps:Int,focus:Float,allowProvisional:Boolean,allowClipping:Boolean,view:Surface,orientation:Int) {
        if(state.busy)return
        val id=begin("Checking source profile, GPU arithmetic and recording route…")
        val immutableProfile=JSONObject(profileJson.toString())
        val request=JSONObject().put("width",output.width).put("height",output.height).put("fps",fps)
            .put("sourceCrop",JSONArray(output.crop().toList())).put("divisor",output.divisor).put("focusDiopters",focus)
            .put("allowProvisional",allowProvisional).put("allowClipping",allowClipping).put("displayRotationDegrees",orientation)
        val evidence=attempt(LiveAttemptKind.CAMERA,request,immutableProfile)
        worker.execute {runSession(id,immutableProfile,output,fps,focus,allowProvisional,allowClipping,view,orientation,evidence)}
    }
    private data class Packet(val pixels:ByteBuffer?,val timestamp:Long)
    @SuppressLint("MissingPermission")
    private fun runSession(id:Long,json:JSONObject,output:LiveLogOutput,fps:Int,focus:Float,allowProvisional:Boolean,allowClipping:Boolean,view:Surface,orientation:Int,evidence:LiveAttempt) {
        val cameraThread=HandlerThread("S23Log-live-camera").apply{start()};val camera=Handler(cameraThread.looper)
        val cameraClosed=CountDownLatch(1)
        val frames=ArrayBlockingQueue<Pair<Packet,JSONObject>>(3);val free=ArrayBlockingQueue<ByteBuffer>(3)
        var device:CameraDevice?=null;var session:CameraCaptureSession?=null;var reader:ImageReader?=null
        var cameraClosing=false;val opened=AtomicBoolean()
        var images=0L;var pairs=0L;var previewDropped=0L;var unmatched=0L;var rawCopyMax=0L
        val lastImage=java.util.concurrent.atomic.AtomicLong(SystemClock.elapsedRealtime())
        var matcher:RawFrameMatcher<Packet,JSONObject>?=null
        var env:GlEnvironment?=null;var gpu:RawLogGpu?=null;var display:LiveLogMonitor?=null;var encoder:LiveLogEncoder?=null
        var partial:File?=null;var media:File?=null;var reportFile:File?=null
        var config:Configuration?=null;var qualification:JSONObject?=null;var gpuProof:JSONObject?=null
        var auxiliaryError:String?=null
        val clock=LiveLogClock(fps);var submitMax=0L;var previewFrames=0L;var droppedAtStop=0L
        val take=evidence.id;var proof:JSONObject?=null;var encoding:JSONObject?=null
        var processedFrames=0L;var decodedIdentity:JSONObject?=null
        var encoderCloseReturned=true;var cameraRequested=false
        fun recycle(p:Packet){p.pixels?.let{check(free.offer(it)){"RAW buffer recycled twice"}}}
        fun closeCamera() {
            if(cameraClosing)return
            cameraClosing=true
            runCatching{session?.stopRepeating()};runCatching{session?.close()};session=null
            runCatching{device?.close()};device=null
            runCatching{reader?.setOnImageAvailableListener(null,null)};runCatching{reader?.close()};reader=null
            runCatching{matcher?.clear()};cameraClosed.countDown()
        }
        stopCamera={camera.post{closeCamera()};Unit}
        try {
            val cfg=evidence.step(LiveStage.PROFILE) { f ->
                checkRunning()
                configure(json,output,fps,focus,allowProvisional).also { c ->
                    evidence.safe { evidence.bind("sourceBinding",c.index.binding()) }
                    f.put("sourceBinding",c.index.binding()).put("routeAndLayoutMatched",true)
                        .put("requestedControlsApplicable",true).put("calibrationIndependentlyVerified",false)
                }
            };config=cfg
            val check={checkRunning()}
            gpuProof=evidence.step(LiveStage.GPU) { f -> gpuProbe(check).also { f.put("report",it) } }
            evidence.safe { evidence.begin(LiveStage.BACKEND) }
            val chosen=backendProbe(app.cacheDir,output.width,output.height,fps,check){update(id,State(busy=true,message=it))}
            observeBackend(evidence,chosen)
            qualification=chosen.report;val route=requireNotNull(chosen.selected){"No ten-bit route qualified. Use Test Log recording backend and share its report."}
            env=GlEnvironment.create(rgb10=route.input==LiveLogEncoder.Input.RGB10_SURFACE)
            gpu=RawLogGpu(env,cfg.index.width,cfg.index.height,output.width,output.height)
            display=LiveLogMonitor(env,view,640,(640L*output.height/output.width).toInt());display.logView=desiredLogView;monitor=display
            repeat(3){free.add(ByteBuffer.allocateDirect(cfg.index.width*cfg.index.height*2).order(ByteOrder.LITTLE_ENDIAN))}
            matcher=RawFrameMatcher(5,{p,_ ->unmatched++;recycle(p);if(!cameraClosing && recording.get())fail("RAW metadata pairing lost a frame")},
                {_ ->unmatched++;if(!cameraClosing && recording.get())fail("RAW image pairing lost metadata")}) {_,p,m ->
                pairs++
                if(stop.get()){recycle(p)}
                else if(p.pixels==null){previewDropped++;if(recording.get())fail("Live RAW copy pool exhausted")}
                else if(!frames.offer(p to m)){recycle(p);previewDropped++;if(recording.get())fail("Live processing cannot sustain acquisition; frame queue full")}
            }
            cameraRequested=true;evidence.safe { evidence.begin(LiveStage.CONFIGURED) }
            camera.post {
                try {
                    if(stop.get()){closeCamera();return@post}
                    val r=ImageReader.newInstance(cfg.index.width,cfg.index.height,ImageFormat.RAW_SENSOR,3);reader=r
                    r.setOnImageAvailableListener({source ->
                        if(cameraClosing || stop.get())return@setOnImageAvailableListener
                        try {
                            while(!stop.get()) {
                                val image=source.acquireNextImage() ?: break
                                val time=image.timestamp;val destination=free.poll()
                                try {
                                    image.use {
                                        images++;lastImage.set(SystemClock.elapsedRealtime())
                                        require(it.format==ImageFormat.RAW_SENSOR && it.width==cfg.index.width && it.height==cfg.index.height)
                                        if(destination!=null){
                                            val start=System.nanoTime();val plane=it.planes.single()
                                            require(plane.pixelStride==2 && plane.rowStride>=cfg.index.width*2)
                                            val bytes=plane.buffer.duplicate();val base=bytes.position()
                                            require(base.toLong()+(cfg.index.height-1L)*plane.rowStride+cfg.index.width*2<=bytes.limit())
                                            destination.clear()
                                            for(y in 0 until cfg.index.height){bytes.limit(base+y*plane.rowStride+cfg.index.width*2);bytes.position(base+y*plane.rowStride);destination.put(bytes)}
                                            destination.flip();rawCopyMax=maxOf(rawCopyMax,System.nanoTime()-start)
                                        }
                                    }
                                } catch(e:Exception){destination?.let{free.offer(it)};throw e}
                                matcher!!.image(time,Packet(destination,time))
                            }
                        } catch(e:Exception){fail("RAW acquisition failed: ${e.message}")}
                    },camera)
                    app.getSystemService(CameraManager::class.java).openCamera(cfg.target.logicalId,object:CameraDevice.StateCallback(){
                        override fun onOpened(d:CameraDevice){
                            if(stop.get() || cameraClosing){d.close();return}
                            device=d
                            try {
                                val out=OutputConfiguration(r.surface);cfg.target.physicalId?.let{out.setPhysicalCameraId(it)}
                                d.createCaptureSession(SessionConfiguration(SessionConfiguration.SESSION_REGULAR,listOf(out),{task->camera.post(task)},object:CameraCaptureSession.StateCallback(){
                                    override fun onConfigured(s:CameraCaptureSession){
                                        if(stop.get() || cameraClosing){s.close();return};session=s
                                        try {
                                            val request=cfg.target.request(d,CameraDevice.TEMPLATE_RECORD).apply {
                                                addTarget(r.surface)
                                                cfg.target.set(this,CaptureRequest.CONTROL_MODE,CaptureRequest.CONTROL_MODE_AUTO)
                                                cfg.target.set(this,CaptureRequest.CONTROL_AE_MODE,CaptureRequest.CONTROL_AE_MODE_OFF)
                                                cfg.target.set(this,CaptureRequest.SENSOR_SENSITIVITY,cfg.profile.iso.toInt())
                                                cfg.target.set(this,CaptureRequest.SENSOR_EXPOSURE_TIME,cfg.profile.exposure)
                                                cfg.target.set(this,CaptureRequest.SENSOR_FRAME_DURATION,1_000_000_000L/fps)
                                                if(cfg.target.minFocus>0){cfg.target.set(this,CaptureRequest.CONTROL_AF_MODE,CaptureRequest.CONTROL_AF_MODE_OFF);cfg.target.set(this,CaptureRequest.LENS_FOCUS_DISTANCE,focus)}
                                            }.build()
                                            s.setRepeatingRequest(request,object:CameraCaptureSession.CaptureCallback(){
                                                override fun onCaptureCompleted(s:CameraCaptureSession,q:CaptureRequest,result:TotalCaptureResult){
                                                    if(cameraClosing || stop.get())return
                                                    try {
                                                        val m=if(cfg.target.physicalId!=null)requireNotNull(result.physicalCameraResults[cfg.target.physicalId])else result
                                                        val iso=requireNotNull(m[CaptureResult.SENSOR_SENSITIVITY]);val exposure=requireNotNull(m[CaptureResult.SENSOR_EXPOSURE_TIME])
                                                        require(m[CaptureResult.CONTROL_AE_MODE]==CaptureRequest.CONTROL_AE_MODE_OFF && kotlin.math.abs(iso.toDouble()/cfg.profile.iso-1)<=.05 && kotlin.math.abs(exposure.toDouble()/cfg.profile.exposure-1)<=.05){"Live exposure differs from the fixed profile"}
                                                        val timestamp=requireNotNull(m[CaptureResult.SENSOR_TIMESTAMP])
                                                        val black=m[CaptureResult.SENSOR_DYNAMIC_BLACK_LEVEL]?.map{it.toDouble()}?.toDoubleArray() ?: black(cfg.target.characteristics)
                                                        val white=m[CaptureResult.SENSOR_DYNAMIC_WHITE_LEVEL] ?: requireNotNull(cfg.target.characteristics[C.SENSOR_INFO_WHITE_LEVEL])
                                                        val metadata=JSONObject().put("sensorTimestampNs",timestamp).put("frameNumber",result.frameNumber)
                                                            .put("iso",iso).put("exposureNs",exposure).put("blackLevels",JSONArray(black.toList())).put("whiteLevel",white)
                                                            .put("focusDiopters",m[CaptureResult.LENS_FOCUS_DISTANCE] ?: JSONObject.NULL)
                                                            .put("focusConfirmed",cfg.target.minFocus<=0 || m[CaptureResult.LENS_FOCUS_DISTANCE]?.let {it.isFinite() && kotlin.math.abs(it-focus)<=maxOf(.05f,focus*.05f)}==true)
                                                        matcher!!.result(timestamp,metadata)
                                                    } catch(e:Exception){fail("Live capture result rejected: ${e.message}")}
                                                }
                                                override fun onCaptureFailed(s:CameraCaptureSession,q:CaptureRequest,f:CaptureFailure){fail("Live RAW request failed: ${f.reason}")}
                                            },camera);opened.set(true);lastImage.set(SystemClock.elapsedRealtime())
                                            evidence.safe { evidence.observe(LiveStage.CONFIGURED,DevelopmentOutcome.PASSED,
                                                "Camera onConfigured callback and repeating request returned",
                                                JSONObject().put("cameraSessionCallback",true).put("repeatingRequestSubmitted",true)
                                                    .put("sourceBinding",cfg.index.binding())) }
                                        } catch(e:Exception){fail("Live request failed: ${e.message}")}
                                    }
                                    override fun onConfigureFailed(s:CameraCaptureSession){s.close();fail("Live RAW session configuration rejected")}
                                }))
                            }catch(e:Exception){fail("Live camera configuration failed: ${e.message}")}
                        }
                        override fun onDisconnected(d:CameraDevice){d.close();fail("Live camera disconnected")}
                        override fun onError(d:CameraDevice,error:Int){d.close();fail("Live camera error $error")}
                    },camera)
                }catch(e:Exception){fail("Live camera open failed: ${e.message}")}
            }
            val began=SystemClock.elapsedRealtime();var lastUi=0L;var isReady=false
            while(!stop.get()) {
                safety()
                if(SystemClock.elapsedRealtime()-began>10_000 && !opened.get())error("Camera did not configure within ten seconds")
                if(opened.get() && SystemClock.elapsedRealtime()-lastImage.get()>5_000)error("Live RAW stream stalled for five seconds")
                if(startRecord.getAndSet(false) && isReady && !recording.get()) {
                    while(true){val old=frames.poll() ?: break;recycle(old.first)}
                    evidence.safe { evidence.begin(LiveStage.ENCODED) }
                    directory.mkdirs();partial=File(directory,"live-$take.partial.mp4")
                    encoder=LiveLogEncoder(partial,route,output.width,output.height,fps);recording.set(true)
                    update(id,State(busy=true,preview=true,recording=true,message="Starting RAW-derived LogC3; waiting for encoded frames…",outputWidth=output.width,outputHeight=output.height))
                }
                val packet=frames.poll(50,TimeUnit.MILLISECONDS) ?: continue
                try {
                    if(!packet.second.getBoolean("focusConfirmed")){
                        require(!recording.get() && SystemClock.elapsedRealtime()-began<15_000){"Manual focus was not confirmed by sensor results"}
                        continue
                    }
                    val p=cfg.profile.parameters(cfg.index,RawFrameRef(packet.second,0,cfg.index.width*cfg.index.height*2),1).copy(crop=output.crop(),divisor=output.divisor)
                    gpu.render(requireNotNull(packet.first.pixels).duplicate().order(ByteOrder.LITTLE_ENDIAN),p,allowClipping)
                    processedFrames++
                    if(recording.get()) {
                        val pts=clock.submit(packet.first.timestamp);val started=System.nanoTime()
                        requireNotNull(encoder).submit(gpu,pts,{safety()});submitMax=maxOf(submitMax,System.nanoTime()-started)
                    } else previewFrames++
                    display.offer(gpu)
                    if(!isReady){isReady=true;update(id,State(busy=true,preview=true,message="Live RAW preview ready. ${output.label}. Profile ${cfg.profile.status}; no audio. Press Record.",outputWidth=output.width,outputHeight=output.height))}
                    val now=SystemClock.elapsedRealtime()
                    if(recording.get() && now-lastUi>=1000){lastUi=now;update(id,State(busy=true,preview=true,recording=true,
                        message="LogC3: ${encoder?.encodedFrames ?: 0} encoded / ${clock.count} submitted; ${clock.largeGaps} sensor gaps. ${display.error?.let{"Preview unavailable: $it"} ?: "Independent preview"}",outputWidth=output.width,outputHeight=output.height))}
                } finally{recycle(packet.first)}
            }
        } catch(e:Exception){evidence.safe { evidence.failedActive(e) };reason.compareAndSet(null,e.message ?: e.javaClass.simpleName);stop.set(true)}
        finally {
            stop.set(true);camera.post{closeCamera()}
            val cameraCloseAcknowledged=runCatching { cameraClosed.await(3,TimeUnit.SECONDS) }.getOrDefault(false)
            if(!cameraCloseAcknowledged)reason.compareAndSet(null,"Camera close acknowledgment timed out")
            evidence.safe {
                if(cameraRequested && !evidence.has(LiveStage.CONFIGURED)) evidence.observe(LiveStage.CONFIGURED,
                    if(reason.get()==null)DevelopmentOutcome.BLOCKED else DevelopmentOutcome.FAILED,
                    reason.get() ?: "Stopped before camera configured")
                if(opened.get()) evidence.observe(LiveStage.RAW,
                    if(!cameraCloseAcknowledged)DevelopmentOutcome.INCONCLUSIVE else if(processedFrames>0)DevelopmentOutcome.PASSED
                    else if(reason.get()==null)DevelopmentOutcome.BLOCKED else DevelopmentOutcome.FAILED,
                    if(processedFrames>0)"Matched RAW frames processed; not sustained-rate qualification" else "No valid RAW frames processed",
                    JSONObject().put("processedFrames",processedFrames).put("matchedFrames",pairs).put("imagesReceived",images)
                        .put("exactSensorTimestampPairing",true).put("profileExposureAndFocusChecked",true).put("sourcePixelsStored",false))
            }
            while(true){val p=frames.poll() ?: break;recycle(p.first);droppedAtStop++}
            recording.set(false);monitor=null
            update(id,State(busy=true,message="Finalizing retained video and verifying its actual timestamps…"))
            if(encoder!=null) {
                try {
                    encoding=evidence.step(LiveStage.ENCODED) { f -> requireNotNull(encoder).finish().also {
                        f.put("encoding",it).put("framesSubmitted",clock.count)
                    } }
                    requireNotNull(encoder).close();encoder=null
                    val times=clock.presentationTimes()
                    proof=evidence.step(LiveStage.DECODED) { f ->
                        val source=requireNotNull(partial)
                        LogP010Codec.verify(source,output.width,output.height,fps,times.size,{safety()},times){_,_->Unit}.also { verified ->
                            verified.put("pixelSourceComparison",false).put("physicalCameraCertified",false)
                            decodedIdentity=JSONObject().put("algorithm","SHA-256").put("sha256",RawJson.hash(source)).put("byteCount",source.length())
                            f.put("verification",verified).put("sensorPresentationTimesUs",JSONArray(times))
                                .put("timestampSpanUs",times.last()).put("durationUnit","us").put("durationDomain","relative_sensor_presentation_timestamps")
                                .put("partialName",source.name).put("mediaIdentity",decodedIdentity)
                        }
                    }
                    val publication=LivePublication.publish(requireNotNull(partial),File(directory,"live-$take.mp4"))
                    media=publication.published // Never bind the destination before the move actually succeeds.
                    evidence.safe { evidence.observe(LiveStage.PUBLICATION,
                        if(media!=null)DevelopmentOutcome.PASSED else DevelopmentOutcome.FAILED,
                        publication.error ?: "Checked movie published to its final filename",
                        JSONObject().put("renameSucceeded",media!=null).put("publishedName",media?.name ?: JSONObject.NULL)
                            .put("retainedName",publication.retained?.name ?: JSONObject.NULL).put("mediaIdentity",decodedIdentity)) }
                    publication.error?.let { reason.set(listOfNotNull(reason.get(),it).joinToString("; ")) }
                } catch(e:Exception){reason.set(listOfNotNull(reason.get(),"Finalization: ${e.message}").joinToString("; "))}
            }
            runCatching{encoder?.close()}.onFailure{encoderCloseReturned=false;reason.compareAndSet(null,"Encoder cleanup: ${it.message}")}
            val displayClosed=runCatching{display?.close()}.isSuccess && (display?.cleanupConfirmed ?: true)
            val gpuClosed=runCatching{gpu?.close()}.isSuccess
            val eglClosed=if(displayClosed)runCatching{env?.close()}.isSuccess else false
            if(!displayClosed || !gpuClosed || !eglClosed)reason.compareAndSet(null,"Live resource cleanup unconfirmed; shared display may remain retained")
            evidence.safe { evidence.observe(LiveStage.CLEANUP,
                if(cameraCloseAcknowledged && displayClosed && gpuClosed && eglClosed && encoderCloseReturned)DevelopmentOutcome.PASSED else DevelopmentOutcome.INCONCLUSIVE,
                "Application owner close acknowledgments; not a universal driver or power-loss guarantee",
                JSONObject().put("scope","application_owner_close_acknowledgments").put("cameraCloseAcknowledged",cameraCloseAcknowledged)
                    .put("previewCleanupConfirmed",displayClosed).put("gpuCloseReturned",gpuClosed).put("eglCloseReturned",eglClosed)
                    .put("encoderCloseReturned",encoderCloseReturned)) }
            cameraThread.quitSafely();stopCamera=null;free.clear()
            try {
                directory.mkdirs();val cfg=config
                val report=JSONObject().put("schemaVersion",1).put("kind","live-raw-logc3").put("device",jsonValue(ModeEvidence.device()))
                    .put("status",if(media!=null)"container_checked" else "not_completed").put("reason",reason.get() ?: JSONObject.NULL)
                    .put("attemptId",evidence.id).put("attemptReport",evidence.file.name)
                    .put("profile",json).put("profileHashOfCanonicalJson",cfg?.profileHash ?: JSONObject.NULL)
                    .put("source",cfg?.index?.header ?: JSONObject.NULL).put("sourcePixelsStored",false)
                    .put("calibrationStatus",cfg?.profile?.status ?: "unknown").put("developmentAppCommit",BuildConfig.SOURCE_REVISION)
                    .put("selectedMode",JSONObject().put("fps",fps).put("width",output.width).put("height",output.height))
                    .put("outputWidth",output.width).put("outputHeight",output.height).put("sourceCrop",JSONArray(output.crop().toList())).put("linearReductionDivisor",output.divisor)
                    .put("transfer","ARRI_LogC3_EI800_exposure").put("primaries","ARRI_Wide_Gamut_3").put("dataLevels","video").put("audio","none")
                    .put("provisionalExplicitlyAllowed",allowProvisional).put("outputClippingExplicitlyAllowed",allowClipping)
                    .put("clippedFramesIncludingPreview",gpu?.clippedFrames ?: 0).put("clippedPixelCount",JSONObject.NULL)
                    .put("displayRotationDegrees",orientation)
                    .put("orientationDegrees",cfg?.target?.characteristics?.get(C.SENSOR_ORIENTATION)?.let{(it-orientation+360)%360} ?: JSONObject.NULL)
                    .put("orientationAppliedToPixels",false)
                    .put("gpuReference",gpuProof ?: JSONObject.NULL).put("backendQualification",qualification ?: JSONObject.NULL)
                    .put("encoder",encoding ?: JSONObject.NULL).put("verification",proof ?: JSONObject.NULL)
                    .put("imagesReceivedIncludingPreview",images).put("matchedIncludingPreview",pairs).put("previewFrames",previewFrames)
                    .put("previewOrOverloadDrops",previewDropped).put("unmatchedAtStopOrOverflow",unmatched).put("queuedFramesDiscardedAtStop",droppedAtStop)
                    .put("framesSubmitted",clock.count).put("sensorPresentationTimesUs",JSONArray(clock.presentationTimes()))
                    .put("sensorDeltaNanosecondsTruncatedToMicroseconds",true).put("framesDuplicatedOrInterpolated",0)
                    .put("measuredFps",clock.measuredFps ?: JSONObject.NULL).put("largeGaps",clock.largeGaps).put("cadenceWithinTolerance",clock.withinTolerance)
                    .put("maximumRawCopyNs",rawCopyMax).put("maximumGpuRenderNs",gpu?.maximumRenderNs ?: 0)
                    .put("maximumGpuReadbackNs",gpu?.maximumReadbackNs ?: 0).put("gpuPackedReadbackType",gpu?.packedReadbackType ?: 0).put("maximumEncoderSubmissionNs",submitMax)
                    .put("previewShown",display?.shown ?: 0).put("previewSkipped",display?.skipped ?: 0).put("previewCleanupConfirmed",display?.cleanupConfirmed ?: true)
                    .put("physicalCameraCertified",false).put("allResolutionSupportClaimed",false).put("arriSensorDynamicRangeClaimed",false)
                media?.let{
                    val identity=JSONObject().put("algorithm","SHA-256").put("sha256",RawJson.hash(it)).put("byteCount",it.length())
                    report.put("mediaIdentity",identity);proof?.put("mediaIdentity",identity)
                }
                reportFile=File(directory,"live-$take.logc3.json");atomicWrite(reportFile,report.toString(2))
                media?.let {
                    val validation=File(app.filesDir,"exports/validation/recording-$take.json");validation.parentFile!!.mkdirs();atomicWrite(validation,report.toString(2))
                    CaptureHistory.save(app,listOf(FileProvider.getUriForFile(app,"${app.packageName}.files",it)),validation,"Live RAW-derived LogC3/AWG3 · ${cfg?.profile?.status} profile · video only · experimental")
                }
            }catch(e:Exception){auxiliaryError="Video retained; report/library failed: ${e.message}";evidence.noteReportError(requireNotNull(auxiliaryError))}
            evidence.safe { evidence.close(listOfNotNull(reason.get())) }
            val messageError=listOfNotNull(reason.get(),auxiliaryError).takeIf{it.isNotEmpty()}?.joinToString("; ")
            update(id,State(message=if(media!=null)"Saved live LogC3/AWG3: ${clock.count} frames; cadence ${if(clock.withinTolerance)"within tolerance" else "unqualified"}. ${messageError.orEmpty()}"
                else messageError ?: "Live preview stopped; no video recorded.",media=media,report=reportFile,error=messageError))
        }
    }
}
