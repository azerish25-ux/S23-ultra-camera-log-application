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
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/** Foreground camera session. A single worker owns GL/encoder input; camera and display have independent owners. */
@TargetApi(33)
class LiveLogSession(context:Context) {
    data class State(val busy:Boolean=false,val preview:Boolean=false,val recording:Boolean=false,
        val message:String="Experimental live RAW-derived LogC3. Qualify the backend before camera testing.",
        val report:File?=null,val media:File?=null,val error:String?=null,val outputWidth:Int=1920,val outputHeight:Int=1080)
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
    fun observe(observer:(State)->Unit){check(Looper.myLooper()==Looper.getMainLooper());observers+=observer;observer(state)}
    fun remove(observer:(State)->Unit){observers-=observer}
    private fun publish(value:State){state=value;observers.toList().forEach{it(value)}}
    private fun update(id:Long,value:State){main.post{if(id==serial)publish(value)}}
    fun stop(){if(state.busy){stop.set(true);stopCamera?.invoke()}}
    fun record(){if(state.preview && !recording.get())startRecord.set(true)}
    fun viewing(log:Boolean){desiredLogView=log;monitor?.logView=log}
    private fun fail(message:String){reason.compareAndSet(null,message);stop.set(true);stopCamera?.invoke()}
    private fun safety(){
        require(app.filesDir.usableSpace>=128L*1024*1024){"Storage reserve reached"}
        require(app.getSystemService(PowerManager::class.java).currentThermalStatus<PowerManager.THERMAL_STATUS_SEVERE){"Severe thermal pressure; live work stopped"}
    }
    private fun begin(label:String):Long {
        check(Looper.myLooper()==Looper.getMainLooper());check(!state.busy)
        val id=++serial;stop.set(false);recording.set(false);startRecord.set(false);reason.set(null)
        publish(State(busy=true,message=label));return id
    }
    fun testBackend(fps:Int) {
        if(state.busy)return
        val id=begin("Testing GPU arithmetic and independent ten-bit encoder/decoder routes…")
        worker.execute {
            var file:File?=null
            try {
                val check={require(!stop.get()){"Backend test cancelled"};safety()}
                val gpu=RawLogGpuProbe.run(check)
                val result=LiveBackendProbe.run(app.cacheDir,1920,1080,fps,check){update(id,State(busy=true,message=it))}
                val report=result.report.put("gpuReference",gpu).put("device",jsonValue(ModeEvidence.device()))
                directory.mkdirs();file=File(directory,"backend-${UUID.randomUUID()}.json");atomicWrite(file,report.toString(2))
                update(id,State(message=if(result.selected!=null)"Qualified ${result.selected.label} for synthetic 1920×1080/$fps. Physical RAW throughput is unverified."
                    else "No route qualified. The report distinguishes encoder, decoder and precision failures; no SDR fallback was used.",report=file))
            } catch(e:Exception){
                runCatching {
                    directory.mkdirs();file=File(directory,"backend-${UUID.randomUUID()}.json")
                    atomicWrite(requireNotNull(file),JSONObject().put("schemaVersion",1).put("kind","live-log-backend-test")
                        .put("appCommit",BuildConfig.SOURCE_REVISION).put("device",jsonValue(ModeEvidence.device()))
                        .put("status","failed").put("reason",e.message ?: e.javaClass.simpleName)
                        .put("sensorPrecisionMeasured",false).put("physicalCameraCertified",false).toString(2))
                }
                update(id,State(message=e.message ?: "Backend test failed",report=file,error=e.message))
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
        worker.execute {runSession(id,immutableProfile,output,fps,focus,allowProvisional,allowClipping,view,orientation)}
    }
    private data class Packet(val pixels:ByteBuffer?,val timestamp:Long)
    @SuppressLint("MissingPermission")
    private fun runSession(id:Long,json:JSONObject,output:LiveLogOutput,fps:Int,focus:Float,allowProvisional:Boolean,allowClipping:Boolean,view:Surface,orientation:Int) {
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
        val clock=LiveLogClock(fps);var submitMax=0L;var previewFrames=0L;var droppedAtStop=0L
        val take=UUID.randomUUID().toString();var proof:JSONObject?=null;var encoding:JSONObject?=null
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
            safety();val cfg=configure(json,output,fps,focus,allowProvisional);config=cfg
            val check={require(!stop.get()){reason.get() ?: "Live preparation stopped"};safety()}
            gpuProof=RawLogGpuProbe.run(check)
            val chosen=LiveBackendProbe.run(app.cacheDir,output.width,output.height,fps,check){update(id,State(busy=true,message=it))}
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
        } catch(e:Exception){reason.compareAndSet(null,e.message ?: e.javaClass.simpleName);stop.set(true)}
        finally {
            stop.set(true);camera.post{closeCamera()};cameraClosed.await(3,TimeUnit.SECONDS)
            while(true){val p=frames.poll() ?: break;recycle(p.first);droppedAtStop++}
            recording.set(false);monitor=null
            update(id,State(busy=true,message="Finalizing retained video and verifying its actual timestamps…"))
            if(encoder!=null) {
                try {
                    encoding=encoder.finish();encoder.close();encoder=null
                    val times=clock.presentationTimes()
                    proof=LogP010Codec.verify(requireNotNull(partial),output.width,output.height,fps,times.size,{safety()},times){_,_->Unit}
                    proof.put("pixelSourceComparison",false).put("physicalCameraCertified",false)
                    media=File(directory,"live-$take.mp4")
                    require(!media.exists() && partial!!.renameTo(media)){"Checked video retained under partial name; final rename failed"}
                } catch(e:Exception){reason.set(listOfNotNull(reason.get(),"Finalization: ${e.message}").joinToString("; "))}
            }
            encoder?.close()
            runCatching{display?.close()}
            runCatching{gpu?.close()}
            if(display==null || display.cleanupConfirmed)runCatching{env?.close()}
            else reason.compareAndSet(null,"Preview cleanup unconfirmed; shared EGL display retained")
            cameraThread.quitSafely();stopCamera=null;free.clear()
            try {
                directory.mkdirs();val cfg=config
                val report=JSONObject().put("schemaVersion",1).put("kind","live-raw-logc3").put("device",jsonValue(ModeEvidence.device()))
                    .put("status",if(media!=null)"container_checked" else "not_completed").put("reason",reason.get() ?: JSONObject.NULL)
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
            }catch(e:Exception){reason.compareAndSet(null,"Video retained; report/library failed: ${e.message}")}
            update(id,State(message=if(media!=null)"Saved live LogC3/AWG3: ${clock.count} frames; cadence ${if(clock.withinTolerance)"within tolerance" else "unqualified"}. ${reason.get().orEmpty()}"
                else reason.get() ?: "Live preview stopped; no video recorded.",media=media,report=reportFile,error=reason.get()))
        }
    }
}
