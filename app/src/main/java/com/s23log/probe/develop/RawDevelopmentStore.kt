package com.s23log.probe.develop

import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import androidx.core.content.FileProvider
import com.s23log.probe.core.*
import com.s23log.probe.BuildConfig
import com.s23log.probe.diagnostics.atomicWrite
import com.s23log.probe.storage.CaptureHistory
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.UUID
import java.util.concurrent.CancellationException
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.pow
import kotlin.math.roundToInt

/** Application-owned single worker; rotation reattaches observers. Leaving the screen cancels work.
 * Sources and imported profiles are read-only. Unverified MP4s remain explicitly named partial.
 */
class RawDevelopmentStore(context:Context,
    private val qualifyCodec:(File,Int,Int,Int,()->Unit,(String)->Unit)->LogP010Codec.Choice = LogP010Codec::qualify
) {
    data class Preview(val width:Int,val height:Int,val argb:IntArray,val rawWidth:Int,val rawHeight:Int)
    data class State(val busy:Boolean=false,val message:String="Select a retained RAW sequence.",
        val index:RawSourceIndex?=null,val preview:Preview?=null,val profile:RawColourProfile?=null,
        val profileFile:File?=null,val savedProfiles:List<File> = emptyList(),val media:File?=null,
        val sidecar:File?=null,val error:String?=null,val evidenceReport:File?=null)
    private val app=context.applicationContext
    private val main=Handler(Looper.getMainLooper())
    private val worker=Executors.newSingleThreadExecutor()
    private val observers=linkedSetOf<(State)->Unit>()
    private val cancelled=AtomicBoolean()
    private var serial=0L
    @Volatile var state=State(); private set
    private val sources=File(app.filesDir,"exports/raw-sequences")
    private val profiles=File(app.filesDir,"exports/raw-profiles")
    val outputDirectory=File(app.filesDir,"exports/logc3")
    val evidenceDirectory=File(app.filesDir,"exports/raw-development-evidence")
    fun observe(observer:(State)->Unit) { check(Looper.myLooper()==Looper.getMainLooper()); observers+=observer; observer(state) }
    fun remove(observer:(State)->Unit) { observers-=observer }
    private fun publish(value:State) { state=value; observers.toList().forEach { it(value) } }
    fun cancel() { if(state.busy)cancelled.set(true) }
    private fun task(label:String,checkBeforeBody:Boolean=true,body:(State,()->Unit,(String)->Unit)->State) {
        check(Looper.myLooper()==Looper.getMainLooper()); if(state.busy)return
        val previous=state; val id=++serial; cancelled.set(false); publish(previous.copy(busy=true,message=label,error=null))
        worker.execute {
            var lastSafety=0L
            val check={
                if(cancelled.get())throw CancellationException("Development cancelled; source and any partial output retained")
                val now=System.nanoTime()
                if(now-lastSafety>250_000_000L) {
                    lastSafety=now
                    if(Build.VERSION.SDK_INT>=29 && app.getSystemService(PowerManager::class.java).currentThermalStatus>=PowerManager.THERMAL_STATUS_SEVERE)
                        throw IllegalStateException("Severe thermal pressure; development stopped without deleting source")
                    require(app.filesDir.usableSpace>=64L*1024*1024) { "Storage reserve reached; development stopped" }
                }
                Unit
            }
            val progress:(String)->Unit={ message -> main.post { if(id==serial && state.busy)publish(state.copy(message=message)) }; Unit }
            val result=try { if(checkBeforeBody)check(); body(previous,check,progress) }
                catch(e:Exception) { previous.copy(message=e.message ?: e.javaClass.simpleName,error=e.message ?: e.javaClass.simpleName) }
            main.post { if(id==serial)publish(result.copy(busy=false)) }
        }
    }
    fun inspect(name:String) = task("Checking every RAW frame checksum…") { _,check,_ ->
        require(name.matches(Regex("raw-[0-9a-f-]+\\.s23raw"))) { "Invalid retained RAW name" }
        val file=File(sources,name); require(file.canonicalFile.parentFile==sources.canonicalFile)
        val index=RawSourceReader.scan(file,check)
        val saved=profiles.listFiles().orEmpty().filter { it.isFile && it.extension=="json" && it.length() in 1..1_048_576 }
            .sortedByDescending { it.lastModified() }.take(128).filter { p -> check(); runCatching { RawColourProfile.parse(RawJson.parse(p.readBytes()),index,true) }.isSuccess }
        State(message="${index.width} × ${index.height}, ${index.frames.size} RAW frames. Select or create a colour profile. This is offline development on the phone, not live Log recording.",
            index=index,preview=preview(index,check),savedProfiles=saved)
    }
    fun importProfile(uri:Uri) = task("Reading colour profile…") { previous,check,_ ->
        val index=requireNotNull(previous.index)
        val bytes=app.contentResolver.openInputStream(uri)?.use { input ->
            val out=ByteArrayOutputStream(); val buffer=ByteArray(16*1024)
            while(true) { check(); val n=input.read(buffer); if(n<0)break; require(out.size()+n<=1_048_576) { "Profile exceeds 1 MiB" }; out.write(buffer,0,n) }
            out.toByteArray()
        } ?: error("Cannot open selected profile")
        val profile=RawColourProfile.parse(RawJson.parse(bytes),index,true)
        val saved=saveProfile(profile.json)
        previous.copy(profile=profile,profileFile=saved,savedProfiles=(listOf(saved)+previous.savedProfiles).distinct(),
            message="Profile loaded: ${profile.status}. Imported calibration claims are not independently certified.",error=null)
    }
    fun selectProfile(file:File) = task("Checking saved profile…") { previous,_,_ ->
        require(file.canonicalFile.parentFile==profiles.canonicalFile && file.length() in 1..1_048_576)
        val profile=RawColourProfile.parse(RawJson.parse(file.readBytes()),requireNotNull(previous.index),true)
        previous.copy(profile=profile,profileFile=file,message="Saved profile loaded: ${profile.status}.",error=null)
    }
    fun deriveProfile(endpoint:Int,grey:IntArray) = task("Deriving a provisional profile from captured metadata and your grey reference…") { previous,check,_ ->
        val index=requireNotNull(previous.index); index.unchanged()
        val json=RawColourProfile.fromMetadata(index,endpoint,grey,RawJson.hash(index.file,check),check)
        val profile=RawColourProfile.parse(json,index,true); val file=saveProfile(json)
        previous.copy(profile=profile,profileFile=file,savedProfiles=(listOf(file)+previous.savedProfiles).distinct(),
            message="Manufacturer-metadata starting profile created. Grey exposure normalized; colour is provisional, not measured/certified.",error=null)
    }
    private fun saveProfile(json:JSONObject):File {
        check(profiles.isDirectory || profiles.mkdirs())
        return File(profiles,"profile-${UUID.randomUUID()}.json").also { atomicWrite(it,json.toString(2)) }
    }
    fun develop(divisor:Int,allowProvisional:Boolean,allowClipping:Boolean)=task("Validating source, profile and timing…",checkBeforeBody=false) { previous,check,progress ->
        val attempt=DevelopmentAttempt(evidenceDirectory,BuildConfig.SOURCE_REVISION,
            JSONObject().put("developmentDevice",JSONObject().put("model",Build.MODEL).put("fingerprint",Build.FINGERPRINT))
                .put("environment","android_saved_raw_development").put("sourceName",previous.index?.file?.name ?: JSONObject.NULL)
                .put("profileName",previous.profileFile?.name ?: JSONObject.NULL).put("linearBoxReductionDivisor",divisor)
                .put("provisionalExplicitlyAllowed",allowProvisional).put("outputClippingExplicitlyAllowed",allowClipping),::atomicWrite)
        attempt.start()
        var result=previous.copy(media=null,sidecar=null,evidenceReport=null)
        try {
            val (index,timing,sourceHash)=attempt.step(DevelopmentStage.SOURCE) { facts ->
                check()
                val source=RawSourceReader.scan(requireNotNull(previous.index).file,check)
                val timing=source.timing();val hash=RawJson.hash(source.file,check)
                val span=source.frames.last().metadata.getLong("sensorTimestampNs")-source.frames.first().metadata.getLong("sensorTimestampNs")
                facts.put("source",JSONObject().put("name",source.file.name).put("sha256",hash).put("byteCount",source.bytes))
                    .put("sourceBinding",source.binding()).put("frames",source.frames.size).put("allFrameChecksumsChecked",true)
                    .put("timestampSpanNs",span).put("durationUnit","ns").put("durationDomain","source_sensor_timestamp_span").put("timing",timing)
                attempt.context("sourceBinding",source.binding());attempt.context("sourceSha256",hash)
                attempt.context("expectedFrames",source.frames.size);attempt.context("fps",source.fps)
                attempt.context("timestampSpanNs",span)
                Triple(source,timing,hash)
            }
            lateinit var profileFile:File
            val (profile,p,profileHash)=attempt.step(DevelopmentStage.PROFILE) { facts ->
                profileFile=requireNotNull(previous.profileFile) { "Select a colour profile" }
                require(profileFile.length() in 1..1_048_576)
                val profile=RawColourProfile.parse(RawJson.parse(profileFile.readBytes()),index,allowProvisional)
                val p=profile.parameters(index,index.frames.first(),divisor)
                require(p.width.toLong()*p.height*3<=128L*1024*1024) { "Output exceeds this milestone's native codec buffer budget" }
                val hash=RawJson.hash(profileFile,check)
                facts.put("profile",JSONObject().put("name",profileFile.name).put("sha256",hash).put("byteCount",profileFile.length()))
                    .put("sourceBindingChecked",true).put("calibrationStatus",profile.status).put("width",p.width).put("height",p.height)
                attempt.context("width",p.width);attempt.context("height",p.height);attempt.context("profileSha256",hash)
                attempt.context("calibrationStatus",profile.status)
                Triple(profile,p,hash)
            }
            val choice=attempt.step(DevelopmentStage.CODEC) { facts ->
                if(Build.VERSION.SDK_INT<33)throw DevelopmentUnavailable("Explicit P010 encoding requires Android 13/API 33 or newer")
                val choice=qualifyCodec(app.cacheDir,p.width,p.height,index.fps,check,progress)
                facts.put("codec",choice.name).put("qualification",choice.qualification)
                attempt.context("codec",choice.name);choice
            }
            val id=attempt.id;val partial=File(outputDirectory,"logc3-$id.partial.mp4")
            val output=File(outputDirectory,"logc3-$id.mp4");val sidecar=File(outputDirectory,"logc3-$id.mp4.logc3.json")
            val frameDeveloper=RawFrameDeveloper();val counts=DevelopCounts()
            val encoded=attempt.step(DevelopmentStage.ENCODED) { facts ->
                check(outputDirectory.isDirectory || outputDirectory.mkdirs())
                val encoded=LogP010Codec.encode(partial,choice.name,p.width,p.height,index.fps,index.frames.size,check) { number,sink ->
                    progress("Developing frame ${number+1} / ${index.frames.size} as LogC3…")
                    val frame=index.frames[number]
                    val value=index.rows(frame).use { rows -> frameDeveloper.develop(rows,profile.parameters(index,frame,divisor),allowClipping,check,sink) }
                    counts.sensorSaturated+=value.sensorSaturated;counts.below+=value.below;counts.above+=value.above
                }
                facts.put("encoder",encoded).put("name",partial.name).put("byteCount",partial.length());encoded
            }
            var maxY=0.0;var maxC=0.0;var maxCode=0
            val verification=attempt.step(DevelopmentStage.DECODED) { facts ->
                val verified=LogP010Codec.verify(partial,p.width,p.height,index.fps,index.frames.size,check) { number,actual ->
                    progress("Checking decoded pixels ${number+1} / ${index.frames.size}…")
                    val compare=LogFrameComparison(actual);val frame=index.frames[number]
                    index.rows(frame).use { rows -> frameDeveloper.develop(rows,profile.parameters(index,frame,divisor),allowClipping,check,compare) }
                    val value=compare.result();maxY=maxOf(maxY,value.getDouble("meanLumaCodeError"));maxC=maxOf(maxC,value.getDouble("meanChromaCodeError"));maxCode=maxOf(maxCode,value.getInt("maximumCodeError"))
                }
                val hash=RawJson.hash(partial,check)
                verified.put("mediaIdentity",JSONObject().put("algorithm","SHA-256").put("sha256",hash).put("byteCount",partial.length()).put("name",partial.name))
                    .put("maximumFrameMeanLumaCodeError",maxY).put("maximumFrameMeanChromaCodeError",maxC).put("maximumCodeError",maxCode)
                    .put("comparison","Every decoded Y/Cb/Cr sample against developed RAW after explicit 4:2:0 subsampling")
                    .put("meanErrorLimitCodes",4.0).put("peakErrorLimitCodes",64)
                facts.put("verification",verified);verified
            }
            attempt.step(DevelopmentStage.UNCHANGED) { facts ->
                index.unchanged()
                val currentSource=RawJson.hash(index.file,check);val currentProfile=RawJson.hash(profileFile,check)
                facts.put("sourceBefore",sourceHash).put("sourceAfter",currentSource).put("profileBefore",profileHash).put("profileAfter",currentProfile)
                require(sourceHash==currentSource && profileHash==currentProfile) { "Source or profile changed during development" }
            }
            val hash=verification.getJSONObject("mediaIdentity").getString("sha256")
            val report=JSONObject().put("schemaVersion",1).put("kind","raw-derived-logc3").put("status","checked")
                .put("developmentAppCommit",BuildConfig.SOURCE_REVISION).put("developmentVersion",BuildConfig.VERSION_NAME)
                .put("source",index.file.name).put("sourceSha256",sourceHash).put("sourceHeader",index.header)
                .put("profileSha256",profileHash).put("profile",profile.json).put("calibrationStatus",profile.status)
                .put("calibrationClaimIndependentlyVerified",false).put("outputSha256",hash).put("output",output.name)
                .put("transfer","ARRI_LogC3_EI800_exposure").put("primaries","ARRI_Wide_Gamut_3").put("whitePoint","D65")
                .put("dataLevels","video").put("storageBits",10).put("yuvMatrix","BT709_coefficients_not_primaries")
                .put("encoder",encoded).put("precisionQualification",choice.qualification).put("verification",verification)
                .put("timing",timing).put("selectedMode",JSONObject().put("fps",index.fps))
                .put("clipping",JSONObject().put("sensorSaturatedSamples",counts.sensorSaturated).put("outputBelowZero",counts.below).put("outputAboveOne",counts.above))
                .put("outputClippingExplicitlyAllowed",allowClipping).put("provisionalExplicitlyAllowed",allowProvisional)
                .put("demosaic","bilinear_reference_cpu_row_streaming").put("linearBoxReductionDivisor",divisor)
                .put("orientationDegrees",index.header.optInt("orientationDegrees",0)).put("orientationApplied",false)
                .put("audio","none").put("realTime",false).put("physicalCameraCertified",false).put("arriSensorDynamicRangeClaimed",false)
                .put("editorImport","Assign ARRI Wide Gamut 3 / LogC3, video data levels; apply stated orientation separately. A generic player is not a colour-correct monitor.")
            report.put("developmentEvidenceFile",attempt.file.name)
            attempt.step(DevelopmentStage.PUBLICATION) { facts ->
                check();require(!output.exists() && partial.renameTo(output)) { "Verified video retained as ${partial.name}; final naming failed" }
                facts.put("renamedWithoutOverwrite",true).put("name",output.name).put("byteCount",output.length())
            }
            // Once a verified movie exists, auxiliary report/library failures must not delete it.
            result=try {
                atomicWrite(sidecar,report.toString(2))
                val validation=File(app.filesDir,"exports/validation/developed-$id.json")
                check(validation.parentFile!!.isDirectory || validation.parentFile!!.mkdirs());atomicWrite(validation,report.toString(2))
                val uri=FileProvider.getUriForFile(app,"${app.packageName}.files",output)
                CaptureHistory.save(app,listOf(uri),validation,"RAW-derived LogC3/AWG3 · ${profile.status} profile · video only · offline phone development")
                result.copy(media=output,sidecar=sidecar,message="Saved ${p.width} × ${p.height} LogC3/AWG3 video. Every frame decoded and compared. ${profile.status} profile; no physical camera certification.",error=null)
            } catch(e:Exception) {
                attempt.context("auxiliaryReportError",e.message ?: e.javaClass.simpleName)
                result.copy(media=output,sidecar=sidecar.takeIf { it.isFile },message="Verified video retained at ${output.name}; report/library publication failed: ${e.message}",error=e.message)
            }
        } catch(e:Exception) {
            attempt.context("attemptError",e.message ?: e.javaClass.simpleName)
            result=result.copy(message=e.message ?: e.javaClass.simpleName,error=e.message ?: e.javaClass.simpleName)
        } finally {
            attempt.context("retainedOutputs",JSONArray(listOf("logc3-${attempt.id}.partial.mp4","logc3-${attempt.id}.mp4").mapNotNull { name ->
                File(outputDirectory,name).takeIf { it.isFile }?.let { JSONObject().put("name",it.name).put("byteCount",it.length()) }
            }))
            attempt.finish()
        }
        val reportError=attempt.persistenceError
        result.copy(evidenceReport=attempt.retainedReport,
            message=result.message+(reportError?.let { " Evidence report write issue: $it. Sources and outputs were not deleted." } ?: ""))
    }
    private fun preview(index:RawSourceIndex,check:()->Unit):Preview {
        val scale=minOf(512.0/index.width,320.0/index.height,1.0)
        val w=(index.width*scale).toInt().coerceAtLeast(1);val h=(index.height*scale).toInt().coerceAtLeast(1)
        val pixels=IntArray(w*h);val row0=ShortArray(index.width);val row1=ShortArray(index.width)
        val meta=index.frames.first().metadata;val (black,white)=RawSourceReader.levels(meta)
        val neutral=runCatching { RawJson.array(meta,"neutralColorPoint",3) }.getOrNull()?.takeIf { it.all { v -> v>0 } }
        val wb=neutral?.map { neutral[1]/it }?.toDoubleArray() ?: doubleArrayOf(1.0,1.0,1.0)
        index.rows(index.frames.first()).use { source ->
            for(y in 0 until h) {
                check();val sy=((y.toLong()*index.height/h).toInt() and -2).coerceAtMost(index.height-2)
                source.readRow(sy,row0);source.readRow(sy+1,row1)
                for(x in 0 until w) {
                    val sx=((x.toLong()*index.width/w).toInt() and -2).coerceAtMost(index.width-2)
                    val rgb=DoubleArray(3);val count=IntArray(3)
                    for(i in 0..3) { val c="RGB".indexOf(RawDevelopMath.BAYER[index.cfa][i]);val v=(if(i<2)row0 else row1)[sx+i%2].toInt() and 65535
                        rgb[c]+=(v-black[i])/(white-black[i])*wb[c];count[c]++ }
                    var colour=0xff000000.toInt()
                    for(c in 0..2){val v=(rgb[c]/count[c]).coerceIn(0.0,1.0).pow(1/2.2);colour=colour or ((v*255).roundToInt() shl (16-8*c))}
                    pixels[y*w+x]=colour
                }
            }
        }
        return Preview(w,h,pixels,index.width,index.height)
    }
}
