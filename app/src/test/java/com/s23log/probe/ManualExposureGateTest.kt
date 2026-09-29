package com.s23log.probe

import com.s23log.probe.core.ManualExposureGate
import com.s23log.probe.core.ManualExposureGate.*
import com.s23log.probe.core.CapturePolicy
import org.junit.Assert.*
import org.junit.Test

class ManualExposureGateTest {
    @Test fun needsThreeDistinctConfirmedStages() {
        val gate = ManualExposureGate(0)
        assertEquals(Action.LOCK, gate.accept(1, Evidence(converged = true)))
        assertEquals(Stage.LOCKING, gate.stage)
        assertEquals(Action.APPLY, gate.accept(2, Evidence(locked = true)))
        assertEquals(Action.COMPLETE, gate.accept(3, Evidence(applied = true)))
    }
    @Test fun appliedFlagCannotSkipConvergence() {
        assertEquals(Action.WAIT, ManualExposureGate(0).accept(1, Evidence(applied = true, locked = true)))
    }
    @Test fun convergenceCannotSkipLockAcknowledgement() {
        val gate = ManualExposureGate(0)
        gate.accept(1, Evidence(converged = true))
        assertEquals(Action.WAIT, gate.accept(2, Evidence(converged = true, applied = true)))
    }
    @Test fun lockCannotSkipManualResultAcknowledgement() {
        val gate = ManualExposureGate(0)
        gate.accept(1, Evidence(converged = true)); gate.accept(2, Evidence(locked = true))
        assertEquals(Action.WAIT, gate.accept(3, Evidence(locked = true)))
    }
    @Test fun missingMetadataTimesOut() {
        val gate = ManualExposureGate(0, 100)
        assertEquals(Action.WAIT, gate.accept(99, Evidence()))
        assertEquals(Action.REJECT, gate.accept(100, Evidence()))
    }
    @Test fun eachStageHasADeadline() {
        val gate = ManualExposureGate(0, 100)
        gate.accept(90, Evidence(converged = true))
        assertEquals(Action.WAIT, gate.accept(189, Evidence()))
        assertEquals(Action.REJECT, gate.accept(190, Evidence(locked = true)))
    }
    @Test fun failedFocusNeverProceedsToManual() {
        assertEquals(Action.REJECT, ManualExposureGate(0).accept(1, Evidence(converged = true, focusFailed = true)))
    }
    @Test fun lateFramesCannotReviveFailure() {
        val gate = ManualExposureGate(0, 100)
        gate.accept(101, Evidence())
        assertEquals(Action.REJECT, gate.accept(102, Evidence(converged = true, locked = true, applied = true)))
    }
    @Test fun completedGateIsIdempotent() {
        val gate = ManualExposureGate(0)
        gate.accept(1, Evidence(converged = true)); gate.accept(2, Evidence(locked = true)); gate.accept(3, Evidence(applied = true))
        assertEquals(Action.COMPLETE, gate.accept(10000, Evidence()))
    }
    @Test fun longShutterUsesChosenPreviewAndCaptureRate() {
        val requested = 40_000_000L
        val at24 = CapturePolicy.exposureForRate(requested, 1_000, 100_000_000, 24)
        val at30 = CapturePolicy.exposureForRate(requested, 1_000, 100_000_000, 30)
        assertEquals(requested, at24)
        assertEquals(33_333_333L, at30)
        assertEquals(at24, CapturePolicy.exposureForRate(requested, 1_000, 100_000_000, 24))
    }
    @Test fun adjustingStateCannotRecordOrSwitchCameras() {
        assertFalse(CapturePolicy.canStartRecording(com.s23log.probe.core.EngineState.ADJUSTING))
        assertFalse(CapturePolicy.canChangeCamera(com.s23log.probe.core.EngineState.ADJUSTING))
    }
}
