package com.s23log.probe.core

enum class BitratePreset { LOW, STANDARD, HIGH;
    companion object { fun fromStored(value: String?) = entries.firstOrNull { it.name == value } ?: STANDARD }
}

object BitratePolicy {
    data class Selection(val requested: Long, val effective: Int) { val limited: Boolean get() = requested != effective.toLong() }
    fun select(base: Int, minimum: Int, maximum: Int, preset: BitratePreset): Selection {
        require(minimum > 0 && maximum >= minimum && base in minimum..maximum) { "Invalid advertised bitrate range" }
        val target = when (preset) { BitratePreset.LOW -> base.toLong() / 2; BitratePreset.STANDARD -> base.toLong(); BitratePreset.HIGH -> base.toLong() * 3 / 2 }
        return Selection(target, target.coerceIn(minimum.toLong(), maximum.toLong()).toInt())
    }
}
