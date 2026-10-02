package com.s23log.probe

import com.s23log.probe.core.*
import com.s23log.probe.develop.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.util.concurrent.CancellationException

/** JSON observations are fabricated contract fixtures; none constitutes phone/codec execution. */
class DevelopmentAttemptTest {
    private val rev="a".repeat(40)
    private fun artifact(name:String="fixture.bin")=JSONObject().put("name",name).put("sha256","b".repeat(64)).put("byteCount",4096)
    private fun signal()=JSONObject().put("fullDecodeVerified",true).put("lumaBitDepth",10).put("chromaBitDepth",10)
        .put("colorPrimariesCode",2).put("transferCharacteristicsCode",2).put("matrixCoefficientsCode",1).put("decodedFrames",4).put("measuredFps",24.0)
    private fun ramp(bad:Boolean)=signal().put("meanCodeError",if(bad)1.0 else .1).put("maximumCodeError",if(bad)3 else 1)
        .put("distinctRampLevels",if(bad)220 else 820).put("passed",!bad)
    private fun facts(stage:DevelopmentStage)=when(stage) {
        DevelopmentStage.SOURCE -> JSONObject().put("source",artifact()).put("sourceBinding",JSONObject().put("fingerprint","synthetic"))
            .put("frames",4).put("allFrameChecksumsChecked",true).put("timestampSpanNs",125000000L)
            .put("durationUnit","ns").put("durationDomain","source_sensor_timestamp_span")
        DevelopmentStage.PROFILE -> JSONObject().put("profile",artifact("profile.json")).put("sourceBindingChecked",true)
            .put("calibrationStatus","synthetic").put("width",128).put("height",128)
        DevelopmentStage.CODEC -> JSONObject().put("codec","synthetic-codec").put("qualification",JSONObject().put("status","qualified")
            .put("positive",ramp(false)).put("eightBitNegative",ramp(true)))
        DevelopmentStage.ENCODED -> JSONObject().put("encoder",JSONObject().put("frames",4).put("name","synthetic-codec")).put("byteCount",4096).put("name","output.partial.mp4")
        DevelopmentStage.DECODED -> JSONObject().put("verification",signal().put("width",128).put("height",128)
            .put("maximumFrameMeanLumaCodeError",.2).put("maximumFrameMeanChromaCodeError",.3).put("maximumCodeError",2)
            .put("meanErrorLimitCodes",4.0).put("peakErrorLimitCodes",64).put("mediaIdentity",artifact("output.partial.mp4")))
        DevelopmentStage.UNCHANGED -> JSONObject().put("sourceBefore","b".repeat(64)).put("sourceAfter","b".repeat(64))
            .put("profileBefore","b".repeat(64)).put("profileAfter","b".repeat(64))
        DevelopmentStage.PUBLICATION -> JSONObject().put("renamedWithoutOverwrite",true).put("name","output.mp4").put("byteCount",4096)
        else -> error("No fixture for camera stages")
    }
    private fun context()=JSONObject().put("expectedFrames",4).put("width",128).put("height",128).put("fps",24)
        .put("sourceSha256","b".repeat(64)).put("profileSha256","b".repeat(64)).put("sourceBinding",JSONObject().put("fingerprint","synthetic")).put("codec","synthetic-codec")
    private fun copy(source:JSONObject,target:JSONObject){source.keys().forEach { target.put(it,source.get(it)) }}
    private fun outcome(a:DevelopmentAttempt,stage:DevelopmentStage):String {
        val rows=a.snapshot().getJSONArray("stages")
        return (0 until rows.length()).map(rows::getJSONObject).first { it.getString("stage")==stage.wire }.getString("outcome")
    }
    private fun withAttempt(block:(DevelopmentAttempt,File)->Unit) {
        val directory=Files.createTempDirectory("p003-").toFile()
        try { block(DevelopmentAttempt(directory,rev,context(),{f,s->f.writeText(s)}),directory) } finally { directory.deleteRecursively() }
    }
    @Test fun syntheticSuccessNeverCertifiesPhone()=withAttempt { a,_ ->
        a.start();for(s in DevelopmentClassifier.outputStages)a.step(s) { copy(facts(s),it) }
        assertFalse(a.snapshot().getJSONObject("classification").getBoolean("verifiedOutput"))
        a.finish();val report=JSONObject(a.file.readText())
        assertTrue(report.getJSONObject("classification").getBoolean("verifiedOutput"))
        assertFalse(report.getBoolean("physicalCameraCertified"));assertEquals("not_run",outcome(a,DevelopmentStage.PHYSICAL))
    }
    @Test fun tcP00301UnavailableDoesNotBecomeSuccess()=withAttempt { a,_ ->
        try{a.step(DevelopmentStage.CODEC){throw DevelopmentUnavailable("No P010 route")};fail()}catch(_:DevelopmentUnavailable){}
        a.finish();assertEquals("unavailable",outcome(a,DevelopmentStage.CODEC))
        assertEquals("not_run",outcome(a,DevelopmentStage.DECODED));assertFalse(a.snapshot().getJSONObject("classification").getBoolean("verifiedOutput"))
    }
    @Test fun tcP00301AdvertisedOrDecodedCannotCertify() {
        for(s in listOf(DevelopmentStage.ADVERTISED,DevelopmentStage.CONFIGURED,DevelopmentStage.DECODED)) {
            val r=DevelopmentStageResult(s,DevelopmentOutcome.PASSED,"Fixture",rev,"ref","b".repeat(64),listOf(DevelopmentCheck("one",DevelopmentOutcome.PASSED,"Fixture")))
            val result=DevelopmentClassifier.classify(listOf(r),rev,true)
            assertFalse(result.physicalCameraCertified);assertFalse(result.verifiedOutput)
        }
    }
    @Test fun tcP00302MixedRevisionsCannotPass() {
        val rows=DevelopmentClassifier.outputStages.map { DevelopmentStageResult(it,DevelopmentOutcome.PASSED,"Fixture",rev,"ref","b".repeat(64),listOf(DevelopmentCheck("one",DevelopmentOutcome.PASSED,"Fixture"))) }
        assertTrue(DevelopmentClassifier.classify(rows,rev,true).verifiedOutput)
        assertFalse(DevelopmentClassifier.classify(rows,"c".repeat(40),true).verifiedOutput)
    }
    @Test fun tcP00303MissingSourceHashIsNotAValidObservation()=withAttempt { a,_ ->
        val f=facts(DevelopmentStage.SOURCE).apply { getJSONObject("source").remove("sha256") }
        try { a.step(DevelopmentStage.SOURCE){copy(f,it)};fail() }catch(_:Exception){}
        assertEquals("failed",outcome(a,DevelopmentStage.SOURCE));a.finish()
    }
    @Test fun tcP00304PositiveLabelDoesNotOverrideBadRamp()=withAttempt { a,_ ->
        val f=facts(DevelopmentStage.CODEC).apply { getJSONObject("qualification").getJSONObject("positive").put("distinctRampLevels",220) }
        try{a.step(DevelopmentStage.CODEC){copy(f,it)};fail()}catch(_:IllegalArgumentException){}
        assertEquals("failed",outcome(a,DevelopmentStage.CODEC));a.finish()
    }
    @Test fun tcP00304NegativeMustActuallyDecodeAndFailPrecision()=withAttempt { a,_ ->
        val f=facts(DevelopmentStage.CODEC).apply { getJSONObject("qualification").getJSONObject("eightBitNegative").put("fullDecodeVerified",false) }
        try{a.step(DevelopmentStage.CODEC){copy(f,it)};fail()}catch(_:IllegalArgumentException){}
        assertEquals("failed",outcome(a,DevelopmentStage.CODEC));a.finish()
    }
    @Test fun tcP00305DurationUnitsMustBeExplicit()=withAttempt { a,_ ->
        val f=facts(DevelopmentStage.SOURCE).put("durationUnit","ms")
        try{a.step(DevelopmentStage.SOURCE){copy(f,it)};fail()}catch(_:IllegalArgumentException){}
        assertEquals("failed",outcome(a,DevelopmentStage.SOURCE));a.finish()
    }
    @Test fun tcP00306CannotRelaxPixelThreshold()=withAttempt { a,_ ->
        val f=facts(DevelopmentStage.DECODED).apply { getJSONObject("verification").put("meanErrorLimitCodes",40.0) }
        try{a.step(DevelopmentStage.DECODED){copy(f,it)};fail()}catch(_:IllegalArgumentException){}
        assertEquals("failed",outcome(a,DevelopmentStage.DECODED));a.finish()
    }
    @Test fun tcP00307ChangedSourceCannotBePreserved()=withAttempt { a,_ ->
        val f=facts(DevelopmentStage.UNCHANGED).put("sourceAfter","c".repeat(64))
        try{a.step(DevelopmentStage.UNCHANGED){copy(f,it)};fail()}catch(_:IllegalArgumentException){}
        assertEquals("failed",outcome(a,DevelopmentStage.UNCHANGED));a.finish()
    }
    @Test fun cancellationIsBlockedNotUnavailable()=withAttempt { a,_ ->
        try{a.step(DevelopmentStage.SOURCE){throw CancellationException("Cancelled")};fail()}catch(_:CancellationException){}
        a.finish();assertEquals("blocked",outcome(a,DevelopmentStage.SOURCE))
    }
    @Test fun reportWriteFailureNeverDeletesExistingFiles()=withAttempt { _,directory ->
        val source=File(directory,"precious.s23raw").apply{writeText("original bytes")}
        val a=DevelopmentAttempt(directory,rev,context(),{_,_->throw java.io.IOException("Injected write failure")})
        a.start();a.finish();assertEquals("original bytes",source.readText());assertNotNull(a.persistenceError)
    }
    @Test fun tcP00308ReportCanBeReopenedWithoutPrivateState()=withAttempt { a,_ ->
        a.start();a.step(DevelopmentStage.SOURCE){copy(facts(DevelopmentStage.SOURCE),it)};a.finish()
        val report=JSONObject(a.file.readText());val first=report.getJSONArray("stages").getJSONObject(2)
        val payload=report.getJSONObject("observations").getString(first.getString("evidenceRef"))
        assertEquals(DevelopmentAttempt.hash(payload),first.getString("evidenceSha256"))
        assertEquals("passed",first.getString("outcome"));assertTrue(report.getBoolean("closed"))
    }
    @Test fun incompleteAttemptStaysUnverified()=withAttempt { a,_ ->
        a.start();a.step(DevelopmentStage.SOURCE){copy(facts(DevelopmentStage.SOURCE),it)}
        assertFalse(JSONObject(a.file.readText()).getBoolean("closed"))
        assertFalse(JSONObject(a.file.readText()).getJSONObject("classification").getBoolean("verifiedOutput"))
    }
    @Test fun retryCannotOverwriteAnExistingAttempt()=withAttempt { a,directory ->
        a.start();a.finish();val original=a.file.readBytes()
        val collision=DevelopmentAttempt(directory,rev,context(),{f,s->f.writeText(s)},a.id)
        collision.start();collision.finish();assertArrayEquals(original,a.file.readBytes());assertNull(collision.retainedReport)
    }
}
