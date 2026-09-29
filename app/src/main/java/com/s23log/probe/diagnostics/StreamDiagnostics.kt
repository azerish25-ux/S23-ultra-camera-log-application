package com.s23log.probe.diagnostics

/** Platform-independent query boundary so one optional format/class/timing failure cannot erase others. */
object StreamDiagnostics {
    data class Size(val width: Int, val height: Int)
    interface Queries {
        fun formats(): List<Int>
        fun sizes(format: Int): List<Size>
        fun minimumDuration(format: Int, size: Size): Long
        fun stallDuration(format: Int, size: Size): Long
        fun codecSizes(): List<String>?
    }
    fun collect(queries: Queries, fallbackFormats: List<Int>): List<Map<String, Any?>> {
        val rows = mutableListOf<Map<String, Any?>>()
        val reported = try { queries.formats() } catch (e: Exception) {
            rows += mapOf("outputClass" to "formatDiscovery", "status" to "query_failed", "error" to e.toString())
            emptyList()
        }
        (reported + fallbackFormats).distinct().sorted().forEach { format ->
            rows += try {
                val sizes = queries.sizes(format).sortedByDescending { it.width.toLong() * it.height }
                mapOf("format" to format, "status" to if (sizes.isEmpty()) "unsupported" else "reported", "outputs" to sizes.map { size ->
                    val row = linkedMapOf<String, Any?>("width" to size.width, "height" to size.height)
                    try { row["minFrameDurationNs"] = queries.minimumDuration(format, size) } catch (e: Exception) { row["minFrameDurationError"] = e.toString() }
                    try { row["stallDurationNs"] = queries.stallDuration(format, size) } catch (e: Exception) { row["stallDurationError"] = e.toString() }
                    row
                })
            } catch (e: Exception) { mapOf("format" to format, "status" to "query_failed", "error" to e.toString()) }
        }
        rows += try {
            val sizes = queries.codecSizes()
            mapOf("outputClass" to "MediaCodec", "status" to if (sizes == null) "not_reported" else if (sizes.isEmpty()) "unsupported" else "reported", "sizes" to sizes)
        } catch (e: Exception) { mapOf("outputClass" to "MediaCodec", "status" to "query_failed", "error" to e.toString()) }
        return rows
    }
}

internal fun nestedQueryErrors(value: Any?): Int = when (value) {
    is Map<*, *> -> (if (value["status"] == "query_failed") 1 else 0) + value.entries.sumOf { (key, item) ->
        if (key.toString() in setOf("minFrameDurationError", "stallDurationError", "queryError") && item != null) 1
        else nestedQueryErrors(item)
    }
    is Iterable<*> -> value.sumOf(::nestedQueryErrors)
    is Array<*> -> value.sumOf(::nestedQueryErrors)
    else -> 0
}
