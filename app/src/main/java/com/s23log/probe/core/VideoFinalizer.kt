package com.s23log.probe.core

/** Media outcome and auxiliary reporting are independent transactions. */
enum class VideoDisposition { PUBLISHED, RECOVERABLE, EMPTY, RETENTION_FAILED }
data class VideoCompletion<V, U>(
    val disposition: VideoDisposition,
    val uri: U?,
    val verification: V?,
    val errors: List<String>,
    val reportError: String? = null
)

object VideoFinalizer {
    fun <V, U> finish(
        samples: Int,
        initialError: Exception?,
        verify: () -> V,
        publish: () -> U,
        retain: (String) -> U,
        discardEmpty: () -> Unit,
        saveReport: (VideoCompletion<V, U>) -> Unit
    ): VideoCompletion<V, U> {
        val errors = mutableListOf<String>()
        initialError?.let { errors += describe(it) }
        var verification: V? = null
        var uri: U? = null
        var disposition: VideoDisposition
        if (samples == 0) {
            errors += "No encoded samples arrived"
            disposition = VideoDisposition.EMPTY
            try { discardEmpty() } catch (e: Exception) { errors += describe(e) }
        } else {
            // Even a one-frame or interrupted file may contain valuable recoverable footage.
            try { verification = verify() } catch (e: Exception) { errors += describe(e) }
            disposition = VideoDisposition.RECOVERABLE
            if (errors.isEmpty()) {
                try { uri = publish(); disposition = VideoDisposition.PUBLISHED }
                catch (e: Exception) { errors += "Publication: ${describe(e)}" }
            }
            if (disposition != VideoDisposition.PUBLISHED) {
                try { uri = retain(errors.joinToString("; ")) }
                catch (e: Exception) { errors += "Retention: ${describe(e)}"; disposition = VideoDisposition.RETENTION_FAILED }
            }
        }
        val result = VideoCompletion(disposition, uri, verification, errors.toList())
        return try { saveReport(result); result } catch (e: Exception) {
            // Never undo media retention/publication because its sidecar could not be saved.
            result.copy(reportError = describe(e))
        }
    }
    private fun describe(error: Exception) = "${error.javaClass.simpleName}: ${error.message}"
}
