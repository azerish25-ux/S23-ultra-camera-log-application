package com.s23log.probe.core

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs
import kotlin.math.sqrt

/** Profiles are assertions with provenance, never a claim of ARRI hardware or certified colour. */
data class RawColourProfile(val json:JSONObject,val matrix:DoubleArray,val wb:DoubleArray,val scale:Double,
                            val crop:IntArray,val status:String,val iso:Long,val exposure:Long) {
    fun parameters(index:RawSourceIndex,frame:RawFrameRef,divisor:Int=1):RawDevelopParameters {
        require(abs(frame.metadata.getLong("iso").toDouble()/iso-1)<=.05 && abs(frame.metadata.getLong("exposureNs").toDouble()/exposure-1)<=.05) { "Frame exposure does not match the profile's 5% tolerance" }
        val (black,white)=RawSourceReader.levels(frame.metadata)
        return RawDevelopParameters(index.cfa,crop,black,white,wb,matrix,scale,divisor)
    }
    companion object {
        fun parse(json:JSONObject,index:RawSourceIndex,allowProvisional:Boolean):RawColourProfile {
            require(RawJson.integer(json,"schemaVersion")==1L && json.getString("kind")=="raw-colour-profile")
            val binding=index.binding(); val supplied=json.getJSONObject("source")
            val keys=listOf("fingerprint","logicalCamera","physicalCamera","width","height","cfa")
            require(supplied.length()==keys.size && keys.all { supplied.has(it) && supplied.get(it)==binding.get(it) }) { "Profile is not bound to this exact source firmware, lens and Bayer layout" }
            val calibration=json.getJSONObject("calibration"); val status=calibration.getString("status")
            require(status=="measured" || (allowProvisional && status=="provisional") || (status=="synthetic" && index.header.getJSONObject("device").optString("model")=="SYNTHETIC_FIXTURE")) {
                "Measured profile required, or explicitly enable provisional development"
            }
            require(calibration.getString("evidence").isNotBlank() && calibration.getString("illuminant").isNotBlank())
            val result=RawColourProfile(JSONObject(json.toString()),RawJson.matrix(json,"cameraToXyzD65"),RawJson.array(json,"bayerWhiteBalance",4),
                RawJson.number(json,"sceneScale"),RawJson.ints(json,"crop",4),status,RawJson.integer(json,"iso"),RawJson.integer(json,"exposureNs"))
            require(result.iso>0 && result.exposure>0)
            for(frame in index.frames) result.parameters(index,frame).also {
                require(it.crop[0].toLong()+it.crop[2]<=index.width && it.crop[1].toLong()+it.crop[3]<=index.height)
            }
            return result
        }
        /** User identifies an actual 18% grey reference in frame zero and the reference illuminant.
         * Requires captured forward AND calibration matrices; missing data is not replaced by identity. */
        fun fromMetadata(index:RawSourceIndex,endpoint:Int,grey:IntArray,sourceHash:String,check:()->Unit={}):JSONObject {
            require(endpoint in 1..2 && grey.size==4 && grey.all { it>=0 && it%2==0 } && grey[2]>=4 && grey[3]>=4)
            require(grey[0].toLong()+grey[2]<=index.width && grey[1].toLong()+grey[3]<=index.height)
            val snapshot=requireNotNull(index.header.optJSONObject("rawCalibration")) { "This source has no capture-time calibration snapshot. Capture a new RAW sequence or import a measured profile." }
            val forward=RawJson.matrix(snapshot,"forwardMatrix$endpoint"); val calibration=RawJson.matrix(snapshot,"calibrationTransform$endpoint")
            val illuminant=RawJson.integer(snapshot,"referenceIlluminant$endpoint")
            val first=index.frames.first(); val neutral=RawJson.array(first.metadata,"neutralColorPoint",3)
            val (matrix,wb3)=RawDevelopMath.metadataMatrix(forward,calibration,neutral)
            val wb=RawDevelopMath.BAYER[index.cfa].map { wb3["RGB".indexOf(it)] }.toDoubleArray()
            val (black,white)=RawSourceReader.levels(first.metadata)
            val sum=DoubleArray(4); val sum2=DoubleArray(4); val counts=IntArray(4); val row=ShortArray(index.width)
            index.rows(first).use { source ->
                for(y in grey[1] until grey[1]+grey[3]) {
                    check(); source.readRow(y,row)
                    for(x in grey[0] until grey[0]+grey[2]) {
                        val p=(y%2)*2+x%2; val raw=row[x].toInt() and 65535
                        require(raw<white && raw>black[p]+2) { "Grey reference includes saturated or near-black samples" }
                        val v=(raw-black[p])/(white-black[p])*wb[p]; sum[p]+=v; sum2[p]+=v*v; counts[p]++
                    }
                }
            }
            val means=DoubleArray(4) { sum[it]/counts[it] }
            require((0..3).all { sqrt((sum2[it]/counts[it]-means[it]*means[it]).coerceAtLeast(0.0))/means[it]<.15 }) { "Choose a uniformly lit grey patch, not a textured area" }
            val rgb=DoubleArray(3) { c -> RawDevelopMath.BAYER[index.cfa].indices.filter { RawDevelopMath.BAYER[index.cfa][it]=="RGB"[c] }.map { means[it] }.average() }
            require(rgb.max()/rgb.min()<1.3) { "Selected patch is not neutral under the captured white balance" }
            val greyY=RawDevelopMath.apply(matrix,rgb)[1]; require(greyY>0 && greyY.isFinite())
            return JSONObject().put("schemaVersion",1).put("kind","raw-colour-profile").put("source",index.binding())
                .put("calibration",JSONObject().put("status","provisional").put("origin","camera2_reference_endpoint_and_user_grey")
                    .put("evidence","Source SHA-256 $sourceHash; first frame; user-identified 18% grey ROI ${grey.joinToString()}")
                    .put("illuminant","Camera2 reference illuminant $endpoint = $illuminant; user-selected, no automatic CCT interpolation")
                    .put("referenceEndpoint",endpoint).put("greyRoi",JSONArray(grey.toList())).put("greyReferenceReflectance",.18)
                    .put("cameraMetadata",snapshot).put("independentlyMeasuredColour",false))
                .put("cameraToXyzD65",RawJson.matrixJson(matrix)).put("bayerWhiteBalance",JSONArray(wb.toList()))
                .put("sceneScale",.18/greyY).put("crop",JSONArray(listOf(0,0,index.width,index.height)))
                .put("iso",first.metadata.getLong("iso")).put("exposureNs",first.metadata.getLong("exposureNs"))
        }
    }
}
