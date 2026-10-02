package com.s23log.probe

import com.s23log.probe.core.*
import com.s23log.probe.live.LiveAttempt
import org.json.JSONObject
import org.junit.After
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.util.concurrent.CancellationException

/** Authored numerical facts exercise the actual producer and IO boundary, not camera/codec quality. */
class LiveAttemptTest {
    private val root=Files.createTempDirectory("live-attempt-test").toFile()
    private val fixture=javaClass.getResourceAsStream("/live-attempt-authored-contract.json")!!.bufferedReader().use { JSONObject(it.readText()) }
    private val revision=fixture.getString("sourceRevision")
    @After fun cleanup(){root.deleteRecursively()}
    private fun facts(stage:LiveStage)=JSONObject(fixture.getJSONObject("observations").getString(stage.wire+"-observation")).getJSONObject("facts")
    private fun attempt(kind:LiveAttemptKind=LiveAttemptKind.CAMERA,schedule:(()->Unit)->Unit={it()},writer:(File,String)->Unit={f,s->f.writeText(s)}):LiveAttempt {
        val context=JSONObject(fixture.getJSONObject("context").toString())
        if(kind==LiveAttemptKind.BACKEND){context.remove("sourceBinding");context.put("profilePayload",JSONObject.NULL);context.put("profileSha256",JSONObject.NULL)}
        return LiveAttempt(root,revision,kind,context,writer,schedule,fixture.getString("attemptId")).also{it.start()}
    }
    private fun stage(a:LiveAttempt,s:LiveStage):JSONObject {
        val rows=a.snapshot().getJSONArray("stages")
        return (0 until rows.length()).map(rows::getJSONObject).single{it.getString("stage")==s.wire}
    }
    private fun all(a:LiveAttempt,except:Set<LiveStage> = emptySet()) {
        a.requestRecording()
        for(s in LiveStage.values()) if(s !in except && fixture.getJSONObject("observations").has(s.wire+"-observation"))
            a.observe(s,DevelopmentOutcome.PASSED,"Authored numerical fixture only",facts(s))
    }
    private fun verdict(a:LiveAttempt)=a.snapshot().getJSONObject("classification")
    @Test fun completeAuthoredObservationChainIsNotPhysicalQualification(){
        val a=attempt();all(a);a.close()
        assertTrue(verdict(a).getBoolean("recordingSucceeded"));assertFalse(verdict(a).getBoolean("physicalCameraCertified"))
        assertFalse(verdict(a).getBoolean("pixelSourceComparison"))
        val retained=JSONObject(a.file.readText());assertEquals(a.id,retained.getString("attemptId"))
        val row=stage(a,LiveStage.GPU);val payload=retained.getJSONObject("observations").getString(row.getString("evidenceRef"))
        assertEquals(row.getString("evidenceSha256"),com.s23log.probe.develop.DevelopmentAttempt.hash(payload))
    }
    @Test fun unavailableRouteKeepsGpuButDoesNotInventCamera(){
        val a=attempt(LiveAttemptKind.BACKEND)
        a.observe(LiveStage.GPU,DevelopmentOutcome.PASSED,"Authored GPU result",facts(LiveStage.GPU))
        // An unavailable route has no selected backend in its context.
        val ctx=JSONObject(fixture.getJSONObject("context").toString()).apply{remove("sourceBinding");remove("selectedBackend");put("profilePayload",JSONObject.NULL);put("profileSha256",JSONObject.NULL)}
        val b=LiveAttempt(root,revision,LiveAttemptKind.BACKEND,ctx,{f,s->f.writeText(s)});b.start()
        b.observe(LiveStage.GPU,DevelopmentOutcome.PASSED,"Authored GPU result",facts(LiveStage.GPU))
        val raw=facts(LiveStage.BACKEND).getJSONObject("report").put("status","unavailable").put("routes",org.json.JSONArray())
            .put("selectedCodec",JSONObject.NULL).put("selectedInput",JSONObject.NULL)
        b.observe(LiveStage.BACKEND,DevelopmentOutcome.UNAVAILABLE,"No accessible route",JSONObject().put("report",raw));b.close()
        assertEquals("passed",stage(b,LiveStage.GPU).getString("outcome"));assertEquals("unavailable",stage(b,LiveStage.BACKEND).getString("outcome"))
        assertFalse(verdict(b).getBoolean("cameraFramesObserved"));assertFalse(verdict(b).getBoolean("recordingSucceeded"))
    }
    @Test fun cancellationHasItsOwnOutcomeAndDoesNotFabricateLaterStages(){
        val a=attempt(LiveAttemptKind.BACKEND)
        try{a.step<Unit>(LiveStage.GPU){throw CancellationException("deliberate cancellation")};fail("Expected cancellation")}catch(_:CancellationException){}
        a.close();assertEquals("blocked",stage(a,LiveStage.GPU).getString("outcome"))
        assertEquals("not_run",stage(a,LiveStage.BACKEND).getString("outcome"))
    }
    @Test fun unexpectedExceptionRemainsFailure(){
        val a=attempt()
        try{a.step<Unit>(LiveStage.PROFILE){throw java.io.IOException("deliberate IO failure")};fail("Expected IO failure")}catch(_:java.io.IOException){}
        a.close();assertEquals("failed",stage(a,LiveStage.PROFILE).getString("outcome"))
    }
    @Test fun beginningStagePersistsIncompleteCheckpoint(){
        val a=attempt();a.begin(LiveStage.PROFILE)
        val report=JSONObject(a.file.readText());assertFalse(report.getBoolean("closed"));assertEquals("profile_validation",report.getString("activeStage"))
        assertFalse(verdict(a).getBoolean("recordingSucceeded"))
    }
    @Test fun queueKeepsWritesOffCallerAndRetainsClosedSnapshot(){
        val queue=mutableListOf<()->Unit>();val a=attempt(schedule={queue+=it});all(a);a.close()
        assertFalse(a.file.exists());queue.forEach{it()};assertTrue(JSONObject(a.file.readText()).getBoolean("closed"))
    }
    @Test fun duplicateAttemptCannotOverwriteEarlierBytes(){
        val a=attempt();a.close();val bytes=a.file.readBytes();val b=attempt();b.close()
        assertNotNull(b.persistenceError);assertArrayEquals(bytes,a.file.readBytes())
    }
    @Test fun observationContextAndClosedRecordsAreImmutable(){
        val a=attempt();val f=facts(LiveStage.GPU);a.observe(LiveStage.GPU,DevelopmentOutcome.PASSED,"Authored comparison",f)
        f.getJSONObject("report").put("maximumLogRgbError",999);a.close();val bytes=a.file.readBytes()
        a.observe(LiveStage.GPU,DevelopmentOutcome.FAILED,"late callback");assertArrayEquals(bytes,a.file.readBytes())
        assertEquals("passed",stage(a,LiveStage.GPU).getString("outcome"))
    }
    @Test fun missingProvenanceCannotBecomeValidProfile(){
        val ctx=JSONObject(fixture.getJSONObject("context").toString());val profile=JSONObject(ctx.getString("profilePayload"))
        profile.getJSONObject("calibration").remove("evidence");val payload=profile.toString()
        ctx.put("profilePayload",payload).put("profileSha256",com.s23log.probe.develop.DevelopmentAttempt.hash(payload))
        val a=LiveAttempt(root,revision,LiveAttemptKind.CAMERA,ctx,{f,s->f.writeText(s)});a.start()
        a.observe(LiveStage.PROFILE,DevelopmentOutcome.PASSED,"False profile pass",facts(LiveStage.PROFILE));a.close()
        assertEquals("failed",stage(a,LiveStage.PROFILE).getString("outcome"))
    }
    @Test fun falselyRejectedEightBitControlMustContainFailingMeasurements(){
        val a=attempt();val f=facts(LiveStage.BACKEND)
        val r=f.getJSONObject("report").getJSONArray("routes").getJSONObject(0).getJSONObject("eightBitNegative")
        r.put("meanCodeError",.1).put("maximumCodeError",1).put("distinctRampLevels",800)
        a.observe(LiveStage.BACKEND,DevelopmentOutcome.PASSED,"False negative control",f);a.close()
        assertEquals("failed",stage(a,LiveStage.BACKEND).getString("outcome"))
    }
    @Test fun changedDurationUnitCannotPassFullDecode(){
        val a=attempt();val f=facts(LiveStage.DECODED).put("durationUnit","ns")
        a.observe(LiveStage.DECODED,DevelopmentOutcome.PASSED,"Wrong unit",f);a.close()
        assertEquals("failed",stage(a,LiveStage.DECODED).getString("outcome"))
    }
    @Test fun failedRenameRetainsSourceAndDoesNotCreatePublishedReference(){
        val a=attempt();all(a,setOf(LiveStage.PUBLICATION))
        val partial=File(root,"live-${a.id}.partial.mp4").apply{writeText("nonempty fixture, not valid video")}
        val result=LivePublication.publish(partial,File(root,"live-${a.id}.mp4")){_,_->false}
        a.observe(LiveStage.PUBLICATION,DevelopmentOutcome.FAILED,requireNotNull(result.error),JSONObject().put("retainedName",partial.name));a.close(listOf(result.error!!))
        assertNull(result.published);assertEquals(partial,result.retained);assertEquals("nonempty fixture, not valid video",partial.readText())
        assertTrue(verdict(a).getBoolean("outputDecoded"));assertFalse(verdict(a).getBoolean("publishedOutput"))
    }
    @Test fun existingDestinationNeverBecomesThisAttemptsPublishedMovie(){
        val source=File(root,"partial.mp4").apply{writeText("source")};val destination=File(root,"movie.mp4").apply{writeText("earlier movie")}
        val r=LivePublication.publish(source,destination){_,_->error("Rename must not run")}
        assertNull(r.published);assertEquals("source",source.readText());assertEquals("earlier movie",destination.readText())
    }
    @Test fun failedAuxiliaryWritesDoNotRevokePublication(){
        val a=attempt(writer={_,_->throw java.io.IOException("Disk fault")});all(a)
        a.noteReportError("Library failed after movie publication");a.close()
        assertEquals("Disk fault",a.persistenceError);assertTrue(verdict(a).getBoolean("publishedOutput"));assertTrue(verdict(a).getBoolean("recordingSucceeded"))
    }
    @Test fun publicationMustHaveTheDecodedIdentity(){
        val a=attempt();all(a,setOf(LiveStage.PUBLICATION));val f=facts(LiveStage.PUBLICATION)
        f.getJSONObject("mediaIdentity").put("sha256","f".repeat(64));a.observe(LiveStage.PUBLICATION,DevelopmentOutcome.PASSED,"Wrong movie",f);a.close()
        assertTrue(verdict(a).getBoolean("outputDecoded"));assertFalse(verdict(a).getBoolean("publishedOutput"))
    }
    @Test fun queuedWriteFailureNotifiesTheObserverWithoutChangingMediaState(){
        val queue=mutableListOf<()->Unit>();val errors=mutableListOf<String>()
        val a=LiveAttempt(root,revision,LiveAttemptKind.CAMERA,fixture.getJSONObject("context"),
            {_,_->throw java.io.IOException("disk-full")},schedule={queue+=it},onPersistenceFailure={errors+=it})
        a.start();a.close();assertTrue(errors.isEmpty());queue.forEach{it()}
        assertTrue(errors.isNotEmpty());assertTrue(errors.all{it=="disk-full"});assertTrue(a.snapshot().getBoolean("closed"))
        assertFalse(verdict(a).getBoolean("publishedOutput"))
    }
    @Test fun cameraEvidenceCannotBeAddedToBackendOnlyAttempt(){
        val a=attempt(LiveAttemptKind.BACKEND);a.observe(LiveStage.CONFIGURED,DevelopmentOutcome.PASSED,"Invented camera",facts(LiveStage.CONFIGURED));a.close()
        assertFalse(verdict(a).getBoolean("cameraFramesObserved"));assertFalse(verdict(a).getBoolean("recordingSucceeded"))
    }
}
