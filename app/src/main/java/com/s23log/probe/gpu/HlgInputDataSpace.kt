package com.s23log.probe.gpu

import android.annotation.TargetApi
import android.hardware.DataSpace

/** Accept only the two complete camera encodings handled by the YUV renderer. */
@TargetApi(33)
internal object HlgInputDataSpace {
    // DataSpace fields already occupy their packed bit positions. Combining the
    // public API 33 constants also supports limited HLG, which has no named constant.
    private const val FULL = DataSpace.STANDARD_BT2020 or DataSpace.TRANSFER_HLG or DataSpace.RANGE_FULL
    private const val LIMITED = DataSpace.STANDARD_BT2020 or DataSpace.TRANSFER_HLG or DataSpace.RANGE_LIMITED

    /** null rejects unspecified, incompatible and reserved-bit encodings. */
    fun fullRange(dataSpace: Int): Boolean? = when (dataSpace) {
        FULL -> true
        LIMITED -> false
        else -> null
    }
}
