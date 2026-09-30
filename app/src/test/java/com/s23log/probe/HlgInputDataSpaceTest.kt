package com.s23log.probe

import android.hardware.DataSpace
import com.s23log.probe.gpu.HlgInputDataSpace
import org.junit.Assert.*
import org.junit.Test

class HlgInputDataSpaceTest {
    private val standard = DataSpace.STANDARD_BT2020
    private val transfer = DataSpace.TRANSFER_HLG

    @Test fun acceptsBothExplicitRangesWithoutSwappingThem() {
        assertEquals(true, HlgInputDataSpace.fullRange(standard or transfer or DataSpace.RANGE_FULL))
        assertEquals(false, HlgInputDataSpace.fullRange(standard or transfer or DataSpace.RANGE_LIMITED))
        assertEquals(true, HlgInputDataSpace.fullRange(DataSpace.DATASPACE_BT2020_HLG))
    }

    @Test fun rejectsIncompleteAndUnsupportedEncodings() {
        for (value in listOf(0, standard, transfer, standard or transfer,
            standard or transfer or DataSpace.RANGE_EXTENDED,
            standard or DataSpace.TRANSFER_ST2084 or DataSpace.RANGE_FULL,
            DataSpace.STANDARD_BT709 or transfer or DataSpace.RANGE_FULL,
            DataSpace.STANDARD_BT2020_CONSTANT_LUMINANCE or transfer or DataSpace.RANGE_FULL,
            DataSpace.DATASPACE_SRGB, DataSpace.DATASPACE_BT2020_PQ)) {
            assertNull("Unsupported dataspace $value", HlgInputDataSpace.fullRange(value))
        }
    }

    @Test fun rejectsReservedBitsInsteadOfSilentlyMaskingThem() {
        val valid = standard or transfer or DataSpace.RANGE_LIMITED
        for (bit in listOf(1, 1 shl 15, 1 shl 30, Int.MIN_VALUE)) {
            assertNull(HlgInputDataSpace.fullRange(valid or bit))
        }
    }
}
