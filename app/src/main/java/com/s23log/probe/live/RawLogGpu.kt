package com.s23log.probe.live

import android.opengl.EGL14
import android.opengl.EGLExt
import android.opengl.EGLSurface
import android.opengl.GLES30 as GL
import android.view.Surface
import com.s23log.probe.core.*
import com.s23log.probe.gpu.GlEnvironment
import com.s23log.probe.gpu.GlTools
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** One GL owner. RAW upload is copied; P010 uses a GPU->CPU transfer. Zero-copy/speed is not claimed. */
class RawLogGpu(val environment: GlEnvironment, val rawWidth: Int, val rawHeight: Int,
                val width: Int, val height: Int): AutoCloseable {
    private var rawTexture=0
    var logTexture=0; private set
    private var logFbo=0
    private var packedTexture=0
    private var packedFbo=0
    private var clipBuffer=0
    private var clipFbo=0
    private var rawProgram=0
    private var packProgram=0
    private var clipProgram=0
    private var surfaceProgram=0
    private val query=IntArray(1)
    private val transfer=ByteBuffer.allocateDirect(width*height*3).order(ByteOrder.LITTLE_ENDIAN)
    var packedReadbackType=0;private set
    var frames=0L; private set
    var clippedFrames=0L; private set
    var maximumRenderNs=0L; private set
    var maximumReadbackNs=0L; private set
    init {
        require(rawWidth>0 && rawHeight>0 && width>0 && height>0 && width%2==0 && height%2==0)
        try {
            environment.current(); GL.glDisable(GL.GL_DITHER);GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT,1)
            val limit=IntArray(1);GL.glGetIntegerv(GL.GL_MAX_TEXTURE_SIZE,limit,0)
            require(maxOf(rawWidth,rawHeight,width,height+height/2)<=limit[0]) { "GPU texture limit excludes this mode" }
            rawTexture=integerTexture(rawWidth,rawHeight,GL.GL_R16UI)
            logTexture=GlTools.texture(width,height,GL.GL_RGBA16F);logFbo=GlTools.fbo(logTexture)
            // RGBA8 contains byte pairs, NOT an 8-bit RGB working image. Each
            // ten-bit sample occupies two channels with its six low padding bits.
            packedTexture=GlTools.texture(width/2,height+height/2,GL.GL_RGBA8);packedFbo=GlTools.fbo(packedTexture)
            val rb=IntArray(1);GL.glGenRenderbuffers(1,rb,0);clipBuffer=rb[0]
            GL.glBindRenderbuffer(GL.GL_RENDERBUFFER,clipBuffer);GL.glRenderbufferStorage(GL.GL_RENDERBUFFER,GL.GL_RGBA4,width,height)
            val f=IntArray(1);GL.glGenFramebuffers(1,f,0);clipFbo=f[0];GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,clipFbo)
            GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER,GL.GL_COLOR_ATTACHMENT0,GL.GL_RENDERBUFFER,clipBuffer)
            check(GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)==GL.GL_FRAMEBUFFER_COMPLETE)
            rawProgram=GlTools.program(RawLogShaders.raw);packProgram=GlTools.program(RawLogShaders.pack)
            clipProgram=GlTools.program(RawLogShaders.clipping);surfaceProgram=GlTools.program(RawLogShaders.surface)
            GL.glGenQueries(1,query,0);GlTools.check("RAW GPU setup")
        } catch(e:Exception) { close();throw e }
    }
    private fun integerTexture(w:Int,h:Int,format:Int):Int {
        val id=IntArray(1);GL.glGenTextures(1,id,0)
        try {
            GL.glBindTexture(GL.GL_TEXTURE_2D,id[0]);GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MIN_FILTER,GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_WRAP_S,GL.GL_CLAMP_TO_EDGE);GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_WRAP_T,GL.GL_CLAMP_TO_EDGE)
            GL.glTexStorage2D(GL.GL_TEXTURE_2D,1,format,w,h);GlTools.check("integer texture");return id[0]
        } catch(e:Exception) { GL.glDeleteTextures(1,id,0);throw e }
    }
    fun render(raw:ByteBuffer,p:RawDevelopParameters,allowClipping:Boolean):Boolean {
        require(p.width==width && p.height==height && p.crop[0].toLong()+p.crop[2]<=rawWidth && p.crop[1].toLong()+p.crop[3]<=rawHeight)
        require(raw.remaining()==rawWidth*rawHeight*2)
        val start=System.nanoTime();environment.current()
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT,1);GL.glPixelStorei(GL.GL_UNPACK_ROW_LENGTH,0)
        GL.glBindTexture(GL.GL_TEXTURE_2D,rawTexture)
        GL.glTexSubImage2D(GL.GL_TEXTURE_2D,0,0,0,rawWidth,rawHeight,GL.GL_RED_INTEGER,GL.GL_UNSIGNED_SHORT,raw.duplicate())
        GL.glUseProgram(rawProgram)
        fun at(name:String)=GL.glGetUniformLocation(rawProgram,name)
        GL.glUniform4iv(at("crop"),1,p.crop,0);GL.glUniform1i(at("cfa"),p.cfa);GL.glUniform1i(at("reduction"),p.divisor)
        GL.glUniform4fv(at("black"),1,p.black.map { it.toFloat() }.toFloatArray(),0)
        GL.glUniform4fv(at("gain"),1,p.wb.map { it.toFloat() }.toFloatArray(),0)
        GL.glUniform1f(at("white"),p.white.toFloat());GL.glUniform1f(at("sceneScale"),p.sceneScale.toFloat())
        val m=RawDevelopMath.multiply(RawDevelopMath.XYZ_TO_AWG3,p.cameraToXyz)
        val matrix=FloatArray(9) { m[(it%3)*3+it/3].toFloat() }
        require(matrix.all { it.isFinite() } && p.sceneScale.toFloat().isFinite() && p.wb.all {it.toFloat().isFinite()}) { "Profile exceeds finite GPU arithmetic range" }
        GL.glUniformMatrix3fv(at("toAwg"),1,false,matrix,0)
        GlTools.draw(rawProgram,rawTexture,logFbo,width,height)
        val clipped=hasClipping()
        require(!clipped || allowClipping) { "Live LogC3 exceeds storage range; explicit output clipping permission is required" }
        if(clipped)clippedFrames++
        frames++;maximumRenderNs=maxOf(maximumRenderNs,System.nanoTime()-start)
        return clipped
    }
    private fun hasClipping():Boolean {
        GL.glColorMask(false,false,false,false)
        try {
            GL.glBeginQuery(GL.GL_ANY_SAMPLES_PASSED,query[0])
            try { GlTools.draw(clipProgram,logTexture,clipFbo,width,height) } finally { GL.glEndQuery(GL.GL_ANY_SAMPLES_PASSED) }
            val result=IntArray(1);GL.glGetQueryObjectuiv(query[0],GL.GL_QUERY_RESULT,result,0)
            GlTools.check("Log storage boundary query");return result[0]!=0
        } finally { GL.glColorMask(true,true,true,true) }
    }
    fun p010():ByteBuffer {
        val began=System.nanoTime();environment.current()
        GL.glUseProgram(packProgram);GL.glUniform1i(GL.glGetUniformLocation(packProgram,"outputHeight"),height)
        GlTools.draw(packProgram,logTexture,packedFbo,width/2,height+height/2)
        // Use the core normalized RGBA/UNSIGNED_BYTE transfer. The integer
        // framebuffer transfer failed the API-36 emulator comparison despite
        // matching floating-point RGB. Encoding exact byte/255 values avoids that
        // driver path without quantizing the Log image to eight bits.
        transfer.clear()
        GL.glBindBuffer(GL.GL_PIXEL_PACK_BUFFER,0)
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT,1)
        GL.glPixelStorei(GL.GL_PACK_ROW_LENGTH,0)
        GL.glPixelStorei(GL.GL_PACK_SKIP_ROWS,0)
        GL.glPixelStorei(GL.GL_PACK_SKIP_PIXELS,0)
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
        packedReadbackType=GL.GL_UNSIGNED_BYTE
        GL.glReadPixels(0,0,width/2,height+height/2,GL.GL_RGBA,GL.GL_UNSIGNED_BYTE,transfer)
        GlTools.check("GPU packed P010 readback")
        transfer.position(0);transfer.limit(width*height*3)
        maximumReadbackNs=maxOf(maximumReadbackNs,System.nanoTime()-began)
        return transfer.duplicate().order(ByteOrder.LITTLE_ENDIAN)
    }
    /** Small synthetic/test inputs only; never used to manufacture camera frames. */
    fun fixture(values:FloatArray) {
        require(values.size==width*height*4);environment.current()
        GL.glBindTexture(GL.GL_TEXTURE_2D,logTexture)
        GL.glTexSubImage2D(GL.GL_TEXTURE_2D,0,0,0,width,height,GL.GL_RGBA,GL.GL_FLOAT,GlTools.floats(values))
        GlTools.check("Log fixture upload")
    }
    fun referencePixels():FloatArray { environment.current();return GlTools.readFloatRgba(logFbo,width,height) }
    fun encoderWindow(surface:Surface):EGLSurface {
        environment.current()
        val ext=EGL14.eglQueryString(environment.display,EGL14.EGL_EXTENSIONS).orEmpty().split(' ')
        require("EGL_KHR_gl_colorspace" in ext) { "Explicit linear EGL storage unavailable" }
        // LINEAR requests no sRGB framebuffer operation. Samples already carry the Log encoding.
        val result=EGL14.eglCreateWindowSurface(environment.display,environment.config,surface,
            intArrayOf(0x309D,0x308A,EGL14.EGL_NONE),0)
        require(result!=EGL14.EGL_NO_SURFACE) { "RGB10 linear-storage encoder surface rejected" }
        environment.current(result)
        val bits=IntArray(1);GL.glGetIntegerv(GL.GL_RED_BITS,bits,0)
        if(bits[0]!=10){environment.destroy(result);error("Encoder window does not expose ten red bits")}
        return result
    }
    fun submit(window:EGLSurface,ptsUs:Long) {
        environment.current(window);GL.glDisable(GL.GL_DITHER)
        GlTools.draw(surfaceProgram,logTexture,0,width,height)
        check(EGLExt.eglPresentationTimeANDROID(environment.display,window,ptsUs*1000))
        check(EGL14.eglSwapBuffers(environment.display,window)) { "Encoder surface swap failed" }
        environment.current()
    }
    override fun close() {
        environment.current()
        for(p in intArrayOf(rawProgram,packProgram,clipProgram,surfaceProgram))if(p!=0)GL.glDeleteProgram(p)
        for(f in intArrayOf(logFbo,packedFbo,clipFbo))if(f!=0)GL.glDeleteFramebuffers(1,intArrayOf(f),0)
        for(t in intArrayOf(rawTexture,logTexture,packedTexture))if(t!=0)GL.glDeleteTextures(1,intArrayOf(t),0)
        if(clipBuffer!=0)GL.glDeleteRenderbuffers(1,intArrayOf(clipBuffer),0)
        if(query[0]!=0)GL.glDeleteQueries(1,query,0)
        rawProgram=0;packProgram=0;clipProgram=0;surfaceProgram=0;logFbo=0;packedFbo=0;clipFbo=0;rawTexture=0;logTexture=0;packedTexture=0;clipBuffer=0;query[0]=0
    }
}
