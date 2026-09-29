package com.s23log.probe.gpu

import android.opengl.EGL14
import android.opengl.EGLConfig
import android.opengl.EGLContext
import android.opengl.EGLDisplay
import android.opengl.EGLSurface
import android.opengl.EGLExt
import android.opengl.GLES11Ext
import android.opengl.GLES30 as GL
import android.view.Surface
import com.s23log.probe.core.ColourMath
import com.s23log.probe.core.ColourPrecision
import com.s23log.probe.core.MonitorTransform
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs

/** One EGL context; only its owning worker may call it. No implicit 8-bit fallback. */
class GlEnvironment private constructor(val display: EGLDisplay, val config: EGLConfig,
    val context: EGLContext, val pbuffer: EGLSurface, private val initializedDisplay: Boolean) : AutoCloseable {
    fun current(surface: EGLSurface = pbuffer) {
        check(EGL14.eglMakeCurrent(display, surface, surface, context)) { "EGL make-current failed: ${EGL14.eglGetError()}" }
    }
    fun window(surface: Surface, hlg: Boolean): EGLSurface {
        if (hlg) {
            val extensions = EGL14.eglQueryString(display, EGL14.EGL_EXTENSIONS).orEmpty().split(' ')
            require("EGL_EXT_gl_colorspace_bt2020_hlg" in extensions) { "EGL BT.2020 HLG colourspace unavailable" }
        }
        // EGL_EXT_gl_colorspace_bt2020_hlg: already HLG-encoded RGB, not linear-light output.
        val attributes = if (hlg) intArrayOf(0x309D, 0x3540, EGL14.EGL_NONE) else intArrayOf(EGL14.EGL_NONE)
        return EGL14.eglCreateWindowSurface(display, config, surface, attributes, 0).also {
            check(it != EGL14.EGL_NO_SURFACE) { "EGL ${if (hlg) "RGB10 HLG" else "SDR monitor"} window rejected: ${EGL14.eglGetError()}" }
        }
    }
    fun destroy(surface: EGLSurface) { if (surface != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(display, surface) }
    fun describe(): Map<String, Any> = mapOf("glVersion" to GL.glGetString(GL.GL_VERSION).orEmpty(),
        "renderer" to GL.glGetString(GL.GL_RENDERER).orEmpty(), "eglRedBits" to attribute(EGL14.EGL_RED_SIZE),
        "eglGreenBits" to attribute(EGL14.EGL_GREEN_SIZE), "eglBlueBits" to attribute(EGL14.EGL_BLUE_SIZE),
        "eglAlphaBits" to attribute(EGL14.EGL_ALPHA_SIZE))
    private fun attribute(name: Int): Int = IntArray(1).also {
        check(EGL14.eglGetConfigAttrib(display, config, name, it, 0))
    }[0]
    override fun close() {
        EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
        EGL14.eglDestroySurface(display, pbuffer); EGL14.eglDestroyContext(display, context)
        if (initializedDisplay) EGL14.eglTerminate(display)
        EGL14.eglReleaseThread()
    }
    companion object {
        fun create(rgb10: Boolean = false, share: GlEnvironment? = null): GlEnvironment {
            val display = share?.display ?: EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
            check(display != EGL14.EGL_NO_DISPLAY)
            var initialized = false
            var context = EGL14.EGL_NO_CONTEXT; var pb = EGL14.EGL_NO_SURFACE
            try {
                if (share == null) { val v = IntArray(2); check(EGL14.eglInitialize(display, v, 0, v, 1)); initialized = true }
                val bits = if (rgb10) 10 else 8
                val attributes = intArrayOf(EGL14.EGL_RED_SIZE, bits, EGL14.EGL_GREEN_SIZE, bits, EGL14.EGL_BLUE_SIZE, bits,
                    EGL14.EGL_ALPHA_SIZE, if (rgb10) 2 else 8, EGL14.EGL_RENDERABLE_TYPE, EGLExt.EGL_OPENGL_ES3_BIT_KHR,
                    EGL14.EGL_SURFACE_TYPE, EGL14.EGL_PBUFFER_BIT or EGL14.EGL_WINDOW_BIT,
                    EGLExt.EGL_RECORDABLE_ANDROID, 1, EGL14.EGL_NONE)
                val configs = arrayOfNulls<EGLConfig>(32); val count = IntArray(1)
                check(EGL14.eglChooseConfig(display, attributes, 0, configs, 0, configs.size, count, 0))
                val config = configs.take(count[0].coerceAtMost(configs.size)).filterNotNull().firstOrNull { candidate ->
                    listOf(EGL14.EGL_RED_SIZE, EGL14.EGL_GREEN_SIZE, EGL14.EGL_BLUE_SIZE, EGL14.EGL_ALPHA_SIZE).all { key ->
                        val result = IntArray(1); EGL14.eglGetConfigAttrib(display, candidate, key, result, 0) &&
                            result[0] == (if (key == EGL14.EGL_ALPHA_SIZE && rgb10) 2 else bits)
                    }
                } ?: error("No exact ${bits}-bit recordable EGL config; no format fallback performed")
                context = EGL14.eglCreateContext(display, config, share?.context ?: EGL14.EGL_NO_CONTEXT,
                    intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 3, EGL14.EGL_NONE), 0)
                check(context != EGL14.EGL_NO_CONTEXT) { "OpenGL ES 3 context unavailable" }
                pb = EGL14.eglCreatePbufferSurface(display, config, intArrayOf(EGL14.EGL_WIDTH, 1, EGL14.EGL_HEIGHT, 1, EGL14.EGL_NONE), 0)
                check(pb != EGL14.EGL_NO_SURFACE)
                return GlEnvironment(display, config, context, pb, initialized).also { it.current() }
            } catch (e: Exception) {
                if (pb != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(display, pb)
                if (context != EGL14.EGL_NO_CONTEXT) EGL14.eglDestroyContext(display, context)
                if (initialized) EGL14.eglTerminate(display)
                throw e
            }
        }
    }
}

/** GLSL implementations use highp for arithmetic AND samplers. Monitor never mutates the working image. */
object ColourShaders {
    val vertex = """#version 300 es
        precision highp float;
        out highp vec2 uv;
        void main() {
            vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
            uv = p; gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
        }
    """.trimIndent()
    val math = """
        float decodeHlg(float v) {
            float x = abs(v);
            return sign(v) * (x <= 0.5 ? x*x/3.0 : (exp((x-0.55991073)/0.17883277)+0.28466892)/12.0);
        }
        float encodeHlg(float v) {
            float x = abs(v);
            return sign(v) * (x <= 0.083333333333 ? sqrt(3.0*x) : 0.17883277*log(max(12.0*x-0.28466892, 0.0000001))+0.55991073);
        }
        vec3 inverseHlg(vec3 x) { return vec3(decodeHlg(x.r), decodeHlg(x.g), decodeHlg(x.b)); }
        vec3 forwardHlg(vec3 x) { return vec3(encodeHlg(x.r), encodeHlg(x.g), encodeHlg(x.b)); }
        vec3 limitedYuv10(vec3 x) {
            float y = (x.x*1023.0-64.0)/876.0;
            float u = (x.y*1023.0-512.0)/896.0;
            float v = (x.z*1023.0-512.0)/896.0;
            return vec3(y+1.4746*v, y-0.164553126844*u-0.571353126844*v, y+1.8814*u);
        }
        float srgb(float t) { return t <= 0.0031308 ? 12.92*t : 1.055*pow(t,1.0/2.4)-0.055; }
        vec3 monitorSdr(vec3 rgb) {
            vec3 r = vec3(dot(rgb,vec3(1.660491,-0.587641,-0.072850)),
                dot(rgb,vec3(-0.124550,1.132900,-0.008349)), dot(rgb,vec3(-0.018151,-0.100579,1.118730)));
            r = max(r,vec3(0.0))*4.0; r = r/(vec3(1.0)+r);
            return vec3(srgb(r.r),srgb(r.g),srgb(r.b));
        }
    """.trimIndent()
    fun input(externalYuv: Boolean) = "#version 300 es\n" +
        (if (externalYuv) "#extension GL_EXT_YUV_target : require\n" else "") + """
        precision highp float;
        uniform highp ${if (externalYuv) "__samplerExternal2DY2YEXT" else "sampler2D"} source;
        uniform mat4 textureMatrix;
        uniform int sourceIsYuv;
        uniform int fullRange;
        in highp vec2 uv;
        out vec4 colour;
        $math
        void main() {
            vec3 signal = texture(source,(textureMatrix*vec4(uv,0.0,1.0)).xy).rgb;
            if (sourceIsYuv == 1) {
                if (fullRange == 1) {
                    float u = signal.g-512.0/1023.0; float v = signal.b-512.0/1023.0; float y = signal.r;
                    signal = vec3(y+1.4746*v, y-0.164553126844*u-0.571353126844*v, y+1.8814*u);
                } else signal = limitedYuv10(signal);
            }
            colour = vec4(inverseHlg(signal),1.0);
        }
    """.trimIndent()
    val output = """#version 300 es
        precision highp float;
        uniform highp sampler2D source;
        uniform int transform;
        in highp vec2 uv;
        out vec4 colour;
        $math
        void main() {
            vec3 x = texture(source,uv).rgb;
            vec3 y = forwardHlg(x);
            if (transform == 1) y = monitorSdr(x);
            // Reference-only. Production recording always calls transform 0.
            if (transform == 2) y = log2(vec3(1.0)+63.0*max(x,vec3(0.0)))/6.0;
            colour = vec4(y,1.0);
        }
    """.trimIndent()
    val copy = """#version 300 es
        precision highp float;
        uniform highp sampler2D source;
        in highp vec2 uv;
        out vec4 colour;
        void main() { colour = texture(source,uv); }
    """.trimIndent()
}

object GlTools {
    fun check(label: String) { val code = GL.glGetError(); check(code == GL.GL_NO_ERROR) { "$label: GL error 0x${code.toString(16)}" } }
    fun program(fragment: String): Int {
        fun compile(type: Int, text: String): Int {
            val shader = GL.glCreateShader(type); check(shader != 0)
            GL.glShaderSource(shader, text); GL.glCompileShader(shader)
            val ok = IntArray(1); GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS, ok, 0)
            if (ok[0] == 0) { val error = GL.glGetShaderInfoLog(shader); GL.glDeleteShader(shader); error("GL shader rejected: $error") }
            return shader
        }
        val vs = compile(GL.GL_VERTEX_SHADER, ColourShaders.vertex)
        var fs = 0; var p = 0
        try {
            fs = compile(GL.GL_FRAGMENT_SHADER, fragment); p = GL.glCreateProgram()
            GL.glAttachShader(p, vs); GL.glAttachShader(p, fs); GL.glLinkProgram(p)
            val ok = IntArray(1); GL.glGetProgramiv(p, GL.GL_LINK_STATUS, ok, 0)
            check(ok[0] != 0) { "GL link rejected: ${GL.glGetProgramInfoLog(p)}" }; return p
        } catch (e: Exception) { if (p != 0) GL.glDeleteProgram(p); throw e }
        finally { GL.glDeleteShader(vs); if (fs != 0) GL.glDeleteShader(fs) }
    }
    fun texture(width: Int, height: Int, internal: Int, pixels: ByteBuffer? = null): Int {
        val id = IntArray(1); GL.glGenTextures(1,id,0); GL.glBindTexture(GL.GL_TEXTURE_2D,id[0])
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MIN_FILTER,GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_WRAP_S,GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_WRAP_T,GL.GL_CLAMP_TO_EDGE)
        val type = when(internal) { GL.GL_RGBA16F -> if (pixels == null) GL.GL_HALF_FLOAT else GL.GL_FLOAT
            GL.GL_RGB10_A2 -> GL.GL_UNSIGNED_INT_2_10_10_10_REV; else -> GL.GL_UNSIGNED_BYTE }
        try { GL.glTexImage2D(GL.GL_TEXTURE_2D,0,internal,width,height,0,GL.GL_RGBA,type,pixels); check("texture allocation"); return id[0] }
        catch (e: Exception) { GL.glDeleteTextures(1,id,0); throw e }
    }
    fun fbo(texture: Int): Int {
        val id=IntArray(1); GL.glGenFramebuffers(1,id,0); GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,id[0])
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER,GL.GL_COLOR_ATTACHMENT0,GL.GL_TEXTURE_2D,texture,0)
        if(GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)!=GL.GL_FRAMEBUFFER_COMPLETE) {
            GL.glDeleteFramebuffers(1,id,0); error("Required colour framebuffer is not renderable")
        }
        return id[0]
    }
    fun floats(values: FloatArray): ByteBuffer = ByteBuffer.allocateDirect(values.size*4).order(ByteOrder.nativeOrder()).apply { asFloatBuffer().put(values) }
    fun readFloatRgba(fbo: Int, width: Int, height: Int): FloatArray {
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,fbo)
        val b=ByteBuffer.allocateDirect(width*height*16).order(ByteOrder.nativeOrder())
        GL.glReadPixels(0,0,width,height,GL.GL_RGBA,GL.GL_FLOAT,b); check("float pixel readback")
        return FloatArray(width*height*4).also { b.asFloatBuffer().get(it) }
    }
    fun readRgb10(fbo: Int, width: Int, height: Int): IntArray {
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,fbo)
        val b=ByteBuffer.allocateDirect(width*height*4).order(ByteOrder.nativeOrder())
        GL.glReadPixels(0,0,width,height,GL.GL_RGBA,GL.GL_UNSIGNED_INT_2_10_10_10_REV,b); check("RGB10 pixel readback")
        return IntArray(width*height).also { b.asIntBuffer().get(it) }
    }
    fun draw(program: Int, texture: Int, fbo: Int, width: Int, height: Int, target: Int = GL.GL_TEXTURE_2D) {
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,fbo);GL.glViewport(0,0,width,height)
        GL.glDisable(GL.GL_BLEND); GL.glDisable(GL.GL_DEPTH_TEST); GL.glDisable(GL.GL_SCISSOR_TEST); GL.glDisable(GL.GL_DITHER)
        GL.glColorMask(true,true,true,true); GL.glUseProgram(program)
        GL.glActiveTexture(GL.GL_TEXTURE0); GL.glBindTexture(target,texture)
        GL.glUniform1i(GL.glGetUniformLocation(program,"source"),0)
        GL.glDrawArrays(GL.GL_TRIANGLES,0,3); check("colour draw")
    }
}

/** Owned by one GL thread. External import never invokes the driver's implicit YUV colour matrix. */
class ColourRenderer(val width: Int, val height: Int, externalYuv: Boolean = false,
                     internalFormat: Int = GL.GL_RGBA16F) : AutoCloseable {
    private var inputProgram = 0; private var outputProgram = 0
    var workingTexture = 0; private set
    var workingFbo = 0; private set
    private val external = externalYuv
    init {
        try {
            if (external) require(GL.glGetString(GL.GL_EXTENSIONS).orEmpty().split(' ').contains("GL_EXT_YUV_target")) { "GL_EXT_YUV_target is required for explicit 10-bit YUV import" }
            inputProgram = GlTools.program(ColourShaders.input(external)); outputProgram = GlTools.program(ColourShaders.output)
            workingTexture = GlTools.texture(width,height,internalFormat); workingFbo=GlTools.fbo(workingTexture)
        } catch (e: Exception) { close(); throw e }
    }
    fun import(texture: Int, matrix: FloatArray = IDENTITY, yuv: Boolean = external, fullRange: Boolean = false) {
        require(matrix.size==16)
        GL.glUseProgram(inputProgram); GL.glUniformMatrix4fv(GL.glGetUniformLocation(inputProgram,"textureMatrix"),1,false,matrix,0)
        GL.glUniform1i(GL.glGetUniformLocation(inputProgram,"sourceIsYuv"),if(yuv)1 else 0)
        GL.glUniform1i(GL.glGetUniformLocation(inputProgram,"fullRange"),if(fullRange)1 else 0)
        GlTools.draw(inputProgram,texture,workingFbo,width,height,if(external) GLES11Ext.GL_TEXTURE_EXTERNAL_OES else GL.GL_TEXTURE_2D)
    }
    fun record(fbo: Int = 0, outputWidth: Int = width, outputHeight: Int = height) = output(fbo,outputWidth,outputHeight,0)
    fun monitor(fbo: Int, outputWidth: Int, outputHeight: Int, transform: MonitorTransform) =
        output(fbo,outputWidth,outputHeight,if(transform==MonitorTransform.SDR_TONEMAP)1 else 0)
    fun referenceLog(fbo: Int) = output(fbo,width,height,2)
    private fun output(fbo: Int,w:Int,h:Int,transform:Int) {
        GL.glUseProgram(outputProgram);GL.glUniform1i(GL.glGetUniformLocation(outputProgram,"transform"),transform)
        GlTools.draw(outputProgram,workingTexture,fbo,w,h)
    }
    override fun close() {
        if(inputProgram!=0) GL.glDeleteProgram(inputProgram);inputProgram=0
        if(outputProgram!=0) GL.glDeleteProgram(outputProgram);outputProgram=0
        if(workingFbo!=0) GL.glDeleteFramebuffers(1,intArrayOf(workingFbo),0);workingFbo=0
        if(workingTexture!=0) GL.glDeleteTextures(1,intArrayOf(workingTexture),0);workingTexture=0
    }
    companion object {
        val IDENTITY = floatArrayOf(1f,0f,0f,0f,0f,1f,0f,0f,0f,0f,1f,0f,0f,0f,0f,1f)
    }
}

/** Deliberate small readback only at setup/test time, never on live full-resolution camera frames. */
object ColourGpuProbe {
    fun run(): Map<String, Any> {
        val ramp=FloatArray(1024*4) { i -> if(i%4==3)1f else (i/4)/1023f }
        var source=0;var dst=0;var dstFbo=0;var monitor=0;var monitorFbo=0;var floatOut=0;var floatFbo=0
        try {
            source=GlTools.texture(1024,1,GL.GL_RGBA16F,GlTools.floats(ramp))
            dst=GlTools.texture(1024,1,GL.GL_RGB10_A2);dstFbo=GlTools.fbo(dst)
            monitor=GlTools.texture(1024,1,GL.GL_RGBA8);monitorFbo=GlTools.fbo(monitor)
            floatOut=GlTools.texture(1024,1,GL.GL_RGBA16F);floatFbo=GlTools.fbo(floatOut)
            var measured: Map<String, Any> = emptyMap(); var refError=0.0
            ColourRenderer(1024,1).use { renderer ->
                renderer.import(source);renderer.record(dstFbo)
                val before=GlTools.readRgb10(dstFbo,1024,1)
                val result=ColourPrecision.assessRamp(DoubleArray(1024) { (before[it] and 1023)/1023.0 })
                check(result.passed) { "GPU precision ramp failed: $result" };measured=result.describe()
                renderer.monitor(monitorFbo,1024,1,MonitorTransform.SDR_TONEMAP)
                renderer.record(dstFbo);check(before.contentEquals(GlTools.readRgb10(dstFbo,1024,1))) { "Monitor affected recording pixels" }
                renderer.monitor(monitorFbo,1024,1,MonitorTransform.HLG_SIGNAL)
                renderer.record(dstFbo);check(before.contentEquals(GlTools.readRgb10(dstFbo,1024,1)))
                renderer.referenceLog(floatFbo)
                val values=GlTools.readFloatRgba(floatFbo,1024,1)
                for(i in 0..1023) {
                    val expected=ColourMath.referenceLogEncode(ColourMath.hlgDecode(i/1023.0).coerceIn(0.0,1.0))
                    refError=maxOf(refError,abs(values[4*i]-expected))
                }
                check(refError<0.002) { "Reference Log CPU/GPU disagreement: $refError" }
            }
            val negative=ColourRenderer(1024,1,internalFormat=GL.GL_RGBA8).use { renderer ->
                renderer.import(source);renderer.record(dstFbo)
                val pixels=GlTools.readRgb10(dstFbo,1024,1)
                ColourPrecision.assessRamp(DoubleArray(1024){(pixels[it] and 1023)/1023.0})
            }
            check(!negative.passed) { "Precision checker accepted an 8-bit intermediate" }
            return mapOf("status" to "passed", "fp16ToRgb10" to measured,"negative8Bit" to negative.describe(),
                "monitorIndependent" to true,"referenceLogMaximumError" to refError,"referenceLogTolerance" to 0.002,
                "scope" to "Synthetic RGB texture -> production FP16 shader -> RGB10 framebuffer. Camera import/encoder are separate gates.")
        } finally {
            intArrayOf(dstFbo,monitorFbo,floatFbo).filter { it!=0 }.forEach { GL.glDeleteFramebuffers(1,intArrayOf(it),0) }
            intArrayOf(source,dst,monitor,floatOut).filter { it!=0 }.forEach { GL.glDeleteTextures(1,intArrayOf(it),0) }
        }
    }
}
