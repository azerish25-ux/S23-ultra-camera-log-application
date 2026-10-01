package com.s23log.probe.camera

import android.hardware.camera2.CameraCharacteristics as C
import android.hardware.camera2.params.ColorSpaceTransform
import org.json.JSONArray
import org.json.JSONObject

/** Capture-time values, bound to the RAW source firmware/lens; never a later-device lookup. */
object RawCalibrationSnapshot {
    fun capture(c:C):JSONObject {
        val out=JSONObject().put("schemaVersion",1).put("origin","Camera2_characteristics_at_capture")
            .put("independentlyMeasured",false)
        fun matrix(name:String,key:C.Key<ColorSpaceTransform>) {
            runCatching { c[key] }.onSuccess { value ->
                out.put(name,if(value==null)JSONObject.NULL else JSONArray((0..2).map { row -> (0..2).map { col -> value.getElement(col,row).toDouble() } }))
            }.onFailure { out.put(name,JSONObject.NULL);out.put("${name}Error",it.javaClass.simpleName) }
        }
        matrix("forwardMatrix1",C.SENSOR_FORWARD_MATRIX1);matrix("forwardMatrix2",C.SENSOR_FORWARD_MATRIX2)
        matrix("calibrationTransform1",C.SENSOR_CALIBRATION_TRANSFORM1);matrix("calibrationTransform2",C.SENSOR_CALIBRATION_TRANSFORM2)
        matrix("colorTransform1",C.SENSOR_COLOR_TRANSFORM1);matrix("colorTransform2",C.SENSOR_COLOR_TRANSFORM2)
        out.put("referenceIlluminant1",runCatching { c[C.SENSOR_REFERENCE_ILLUMINANT1] }.getOrNull() ?: JSONObject.NULL)
        out.put("referenceIlluminant2",runCatching { c[C.SENSOR_REFERENCE_ILLUMINANT2] }.getOrNull() ?: JSONObject.NULL)
        return out
    }
}
