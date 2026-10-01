package com.s23log.probe.live

import android.opengl.EGL14
import android.opengl.GLES30 as GL
import android.os.Handler
import android.os.HandlerThread
import android.view.Surface
import com.s23log.probe.gpu.GlEnvironment
import com.s23log.probe.gpu.GlTools
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Independent display worker and three copied preview buffers. Display cannot own RAW/record buffers. */
class LiveLogMonitor(private val parent:GlEnvironment, private val surface:Surface,
                     private val width:Int, private val height:Int):AutoCloseable {
    private data class Slot(val texture:Int,val fbo:Int,val busy:AtomicBoolean=AtomicBoolean())
    private val slots=mutableListOf<Slot>()
    private val thread=HandlerThread("S23Log-live-monitor").apply { start() }
    private val handler=Handler(thread.looper)
    private var program=0
    private var display:GlEnvironment?=null
    private var window=EGL14.EGL_NO_SURFACE
    private var copy=0
    private val ready=CountDownLatch(1)
    private val stopping=AtomicBoolean()
    @Volatile var error:String?=null; private set
    @Volatile var logView=false
    @Volatile var shown=0L; private set
    var skipped=0L;private set
    var cleanupConfirmed=false;private set
    init {
        try {
            parent.current();program=GlTools.program(RawLogShaders.monitor)
            repeat(3){val t=GlTools.texture(width,height,GL.GL_RGBA8);slots+=Slot(t,GlTools.fbo(t))}
            handler.post {
                try {
                    val env=GlEnvironment.create(share=parent);display=env
                    window=env.window(surface,false);env.current(window);copy=GlTools.program(RawLogShaders.surface)
                } catch(e:Exception){error=e.message ?: e.javaClass.simpleName}
                finally{ready.countDown()}
            }
            require(ready.await(5,TimeUnit.SECONDS)) { "Live preview setup timed out" }
            require(error==null) { "Live preview unavailable: $error" }
        } catch(e:Exception){close();throw e}
    }
    fun offer(gpu:RawLogGpu) {
        if(stopping.get() || error!=null){skipped++;return}
        val slot=slots.firstOrNull { it.busy.compareAndSet(false,true) } ?: run { skipped++;return }
        parent.current();GL.glUseProgram(program);GL.glUniform1i(GL.glGetUniformLocation(program,"logView"),if(logView)1 else 0)
        var fence=0L
        try {
            GlTools.draw(program,gpu.logTexture,slot.fbo,width,height)
            fence=GL.glFenceSync(GL.GL_SYNC_GPU_COMMANDS_COMPLETE,0);check(fence!=0L);GL.glFlush()
            val sync=fence
            if(!handler.post {
                try {
                    val env=requireNotNull(display);env.current(window);GL.glWaitSync(sync,0,GL.GL_TIMEOUT_IGNORED)
                    if(!stopping.get()) {
                        GlTools.draw(copy,slot.texture,0,width,height)
                        check(EGL14.eglSwapBuffers(env.display,window));GL.glFinish();shown++
                    }
                } catch(e:Exception){error=e.message ?: e.javaClass.simpleName}
                finally{GL.glDeleteSync(sync);slot.busy.set(false)}
            }) {GL.glDeleteSync(sync);slot.busy.set(false)}
        } catch(e:Exception){if(fence!=0L)GL.glDeleteSync(fence);slot.busy.set(false);error=e.message}
    }
    override fun close() {
        if(stopping.getAndSet(true))return
        val done=CountDownLatch(1)
        if(handler.post {
            try {display?.let {it.current();if(copy!=0)GL.glDeleteProgram(copy);it.destroy(window);it.close()}}
            catch(e:Exception){error=e.message}
            finally{done.countDown();thread.quitSafely()}
        } && done.await(3,TimeUnit.SECONDS)) {
            parent.current();if(program!=0)GL.glDeleteProgram(program)
            slots.forEach {GL.glDeleteFramebuffers(1,intArrayOf(it.fbo),0);GL.glDeleteTextures(1,intArrayOf(it.texture),0)}
            slots.clear();cleanupConfirmed=true
        } else error="Preview driver cleanup timed out; shared resources retained"
    }
}
