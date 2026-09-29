package com.s23log.probe.core

/** Fail-closed, deadline-bounded transition; missing metadata is never treated as confirmation. */
class ManualExposureGate(startedAtMs: Long, private val timeoutMs: Long = 5_000) {
    enum class Stage { CONVERGING, LOCKING, APPLYING, COMPLETE, FAILED }
    enum class Action { WAIT, LOCK, APPLY, COMPLETE, REJECT }
    data class Evidence(val converged: Boolean = false, val locked: Boolean = false, val applied: Boolean = false, val focusFailed: Boolean = false)
    var stage: Stage = Stage.CONVERGING
        private set
    private var stageAt = startedAtMs
    init { require(timeoutMs > 0) }
    fun accept(nowMs: Long, evidence: Evidence): Action {
        if (stage == Stage.COMPLETE) return Action.COMPLETE
        if (stage == Stage.FAILED) return Action.REJECT
        if (nowMs - stageAt >= timeoutMs || evidence.focusFailed) { stage = Stage.FAILED; return Action.REJECT }
        val next = when {
            stage == Stage.CONVERGING && evidence.converged -> Stage.LOCKING to Action.LOCK
            stage == Stage.LOCKING && evidence.locked -> Stage.APPLYING to Action.APPLY
            stage == Stage.APPLYING && evidence.applied -> Stage.COMPLETE to Action.COMPLETE
            else -> return Action.WAIT
        }
        stage = next.first
        stageAt = nowMs
        return next.second
    }
}
