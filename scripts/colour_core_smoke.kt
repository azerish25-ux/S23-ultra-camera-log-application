import com.s23log.probe.core.*
import kotlin.math.abs
import kotlin.math.round

fun main() {
    var checks=0
    fun verify(value:Boolean) { check(value);checks++ }
    val direct=RecordingMode(1920,1080,30,DynamicRange.HLG10,"encoder","video/hevc",10000000,false,true)
    val gpu=direct.copy(processing=ProcessingPath.GPU_HLG10,previewDuringRecording=true)
    verify(direct.key+":GPU_HLG10"==gpu.key)
    verify(ProcessingPolicy.rejection(33,direct,true,true,false)==null)
    verify(ProcessingPolicy.rejection(33,direct,true,false,false)!=null)
    verify(ProcessingPolicy.rejection(32,direct,true,true,true)!=null)
    verify(ProcessingPolicy.rejection(35,direct.copy(width=7680,height=4320),true,true,true)!=null)
    verify(ProcessingPolicy.rejection(35,direct.copy(fps=60),true,true,true)!=null)
    verify(ProcessingPolicy.rejection(35,direct,false,true,true)!=null)
    verify(ColourPrecision.assessRamp(DoubleArray(1024){it/1023.0}).passed)
    verify(!ColourPrecision.assessRamp(DoubleArray(1024){round(it/1023.0*255)/255}).passed)
    verify((0..10000).all { val x=it/10000.0;abs(ColourMath.referenceLogDecode(ColourMath.referenceLogEncode(x))-x)<1e-12 })
    verify((-1000..2000).all { val x=it/2000.0;abs(ColourMath.hlgEncode(ColourMath.hlgDecode(x))-x)<1e-7 })
    val rgb=doubleArrayOf(.1,.5,.9);val yuv=ColourMath.hlgToLimitedYuv10(rgb[0],rgb[1],rgb[2])
    val back=ColourMath.limitedYuv10ToHlg(yuv[0],yuv[1],yuv[2]);verify(rgb.indices.all{abs(rgb[it]-back[it])<1e-9})
    verify(runCatching{ColourMath.referenceLogEncode(-1.0)}.isFailure)
    val clock=ProcessingFrameClock(30);verify(clock.accept(10000000000,10001000000));verify(clock.accept(10100000000,10101000000))
    verify(clock.largeIntervals==1L);clock.stop();verify(!clock.accept(10200000000,10201000000))
    verify(runCatching{ProcessingFrameClock(24).accept(1,10000000000)}.isFailure)
    println("Colour policy checks: $checks passed (CPU/reference checks, not camera or GPU execution)")
}
