package com.s23log.probe.diagnostics

import org.json.JSONArray
import org.json.JSONObject

/** Every property has an explicit state; unknown is not the same as unsupported. */
data class ProbeValue(val status: String, val value: Any? = null, val detail: String? = null) {
    fun json(): JSONObject = JSONObject().put("status", status).put("value", jsonValue(value))
        .put("detail", detail ?: JSONObject.NULL)
}

class ProbeSection(val kind: String, val id: String) {
    val fields = linkedMapOf<String, ProbeValue>()
    fun query(name: String, block: () -> Any?) {
        fields[name] = try {
            val value = block()
            ProbeValue(if (value == null) "not_reported" else "reported", value)
        } catch (error: Exception) {
            ProbeValue("query_failed", detail = "${error.javaClass.simpleName}: ${error.message}")
        }
    }
    fun unavailable(name: String, detail: String) { fields[name] = ProbeValue("unsupported", detail = detail) }
    fun json(): JSONObject = JSONObject().put("kind", kind).put("id", id).put("fields",
        JSONObject().also { obj -> fields.forEach { (key, value) -> obj.put(key, value.json()) } })
}

class ProbeReport(val generatedAt: String, val sections: List<ProbeSection>,
    val sourceRevision: String? = null, val deviceBuild: String? = null) {
    private val reportId = java.util.UUID.randomUUID().toString()
    val errorCount: Int get() = sections.sumOf { s -> s.fields.values.sumOf { (if (it.status == "query_failed") 1 else 0) + nestedQueryErrors(it.value) } }
    fun json(): String = JSONObject().put("schemaVersion", 2).put("generatedAt", generatedAt)
        .put("evidence", "advertised_only").put("queryErrors", errorCount)
        .put("reportId", reportId).put("sourceRevision", sourceRevision ?: JSONObject.NULL).put("deviceBuild", deviceBuild ?: JSONObject.NULL)
        .put("stageEvidence", JSONObject().put("schemaVersion", 1).put("stage", "advertised")
            .put("outcome", if (errorCount == 0 && sourceRevision?.matches(Regex("[0-9a-f]{40}")) == true && !deviceBuild.isNullOrBlank()) "passed" else "inconclusive")
            .put("scope", "API query results only; individual unsupported and missing values remain distinct")
            .put("recordingVerified", false).put("physicalCameraCertified", false))
        .put("sections", JSONArray().also { array -> sections.forEach { array.put(it.json()) } }).toString(2)
    fun text(): String = buildString {
        appendLine("S23LOG CAPABILITY REPORT / schema 2")
        appendLine("Generated: $generatedAt")
        appendLine("Evidence: advertised only; not proof of a working recording configuration.")
        appendLine("Query errors: $errorCount (other results are retained)")
        sections.forEach { section ->
            appendLine("\n=== ${section.kind}: ${section.id} ===")
            section.fields.forEach { (key, field) ->
                appendLine("$key [${field.status}]: ${field.detail ?: jsonValue(field.value)}")
            }
        }
        appendLine("\nHLG10 is processed HDR, not proprietary Samsung Log or RAW sensor access.")
        appendLine("P010 buffer input is not a prerequisite for the separate encoder Surface path.")
    }
}

fun jsonValue(value: Any?): Any = when (value) {
    null -> JSONObject.NULL
    is Map<*, *> -> JSONObject().also { obj -> value.forEach { (key, item) -> obj.put(key.toString(), jsonValue(item)) } }
    is Iterable<*> -> JSONArray().also { array -> value.forEach { array.put(jsonValue(it)) } }
    is Array<*> -> JSONArray().also { array -> value.forEach { array.put(jsonValue(it)) } }
    is IntArray -> jsonValue(value.toList())
    is LongArray -> jsonValue(value.toList())
    is FloatArray -> jsonValue(value.toList())
    is Double -> if (value.isFinite()) value else JSONObject.NULL
    is Float -> if (value.isFinite()) value else JSONObject.NULL
    is String, is Number, is Boolean, is JSONObject, is JSONArray -> value
    else -> value.toString()
}
