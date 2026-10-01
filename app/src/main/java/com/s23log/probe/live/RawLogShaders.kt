package com.s23log.probe.live

/** RAW integer samples -> scene-linear colour -> LogC3. No display curve is in this shader. */
object RawLogShaders {
    val raw = """#version 300 es
        precision highp float;
        precision highp int;
        uniform highp usampler2D source;
        uniform ivec4 crop;
        uniform int cfa;
        uniform int reduction;
        uniform vec4 black;
        uniform vec4 gain;
        uniform float white;
        uniform mat3 toAwg;
        uniform float sceneScale;
        out vec4 colour;
        int phase(ivec2 p) { return (p.y & 1)*2+(p.x & 1); }
        int channel(ivec2 p) {
            int k=phase(p);
            if(cfa==0) return k==0?0:(k==3?2:1);
            if(cfa==1) return k==1?0:(k==2?2:1);
            if(cfa==2) return k==2?0:(k==1?2:1);
            return k==3?0:(k==0?2:1);
        }
        ivec2 reflected(ivec2 p) {
            return ivec2(p.x<0?-p.x:(p.x>=crop.z?2*crop.z-2-p.x:p.x),
                         p.y<0?-p.y:(p.y>=crop.w?2*crop.w-2-p.y:p.y));
        }
        float sampleRaw(ivec2 p) {
            p=reflected(p); int k=phase(p);
            float v=float(texelFetch(source,p+crop.xy,0).r);
            return (v-black[k])*gain[k]/(white-black[k]);
        }
        vec3 demosaic(ivec2 p) {
            vec3 rgb=vec3(0.0);
            for(int c=0;c<3;c++) {
                if(channel(p)==c) rgb[c]=sampleRaw(p);
                else {
                    float sum=0.0; float weight=0.0;
                    for(int dy=-1;dy<=1;dy++) for(int dx=-1;dx<=1;dx++) {
                        ivec2 q=reflected(p+ivec2(dx,dy));
                        if(channel(q)==c) {
                            float w=float((dx==0?2:1)*(dy==0?2:1));
                            sum+=sampleRaw(q)*w;weight+=w;
                        }
                    }
                    rgb[c]=sum/weight;
                }
            }
            return rgb;
        }
        float logc(float x) {
            return x>.010591 ? .247190*log(5.555556*x+.052272)/log(10.0)+.385537 : 5.367655*x+.092809;
        }
        void main() {
            ivec2 origin=ivec2(gl_FragCoord.xy)*reduction;
            vec3 linear=vec3(0.0);
            for(int y=0;y<4;y++) for(int x=0;x<4;x++) {
                if(x<reduction && y<reduction) linear+=toAwg*demosaic(origin+ivec2(x,y));
            }
            linear*=sceneScale/float(reduction*reduction);
            colour=vec4(logc(linear.r),logc(linear.g),logc(linear.b),1.0);
        }
    """.trimIndent()
    val pack = """#version 300 es
        precision highp float;
        precision highp int;
        uniform highp sampler2D source;
        uniform int outputHeight;
        layout(location=0) out uvec4 codes;
        vec3 rgb(ivec2 p) { return clamp(texelFetch(source,p,0).rgb,0.0,1.0); }
        float luma(vec3 r) { return dot(r,vec3(.2126,.7152,.0722)); }
        void main() {
            ivec2 p=ivec2(gl_FragCoord.xy); uint a;uint b;
            if(p.y<outputHeight) {
                a=uint(floor(64.0+876.0*luma(rgb(ivec2(p.x*2,p.y)))+.5));
                b=uint(floor(64.0+876.0*luma(rgb(ivec2(p.x*2+1,p.y)))+.5));
            } else {
                ivec2 q=ivec2(p.x*2,(p.y-outputHeight)*2);
                vec3 r=(rgb(q)+rgb(q+ivec2(1,0))+rgb(q+ivec2(0,1))+rgb(q+ivec2(1,1)))*.25;
                float y=luma(r);
                a=uint(clamp(floor(512.0+896.0*(r.b-y)/1.8556+.5),64.0,960.0));
                b=uint(clamp(floor(512.0+896.0*(r.r-y)/1.5748+.5),64.0,960.0));
            }
            a<<=6;b<<=6;codes=uvec4(a&255u,a>>8,b&255u,b>>8);
        }
    """.trimIndent()
    val clipping = """#version 300 es
        precision highp float;
        uniform highp sampler2D source;
        out vec4 colour;
        void main() {
            vec3 v=texelFetch(source,ivec2(gl_FragCoord.xy),0).rgb;
            if(all(greaterThanEqual(v,vec3(0.0))) && all(lessThanEqual(v,vec3(1.0)))) discard;
            colour=vec4(1.0);
        }
    """.trimIndent()
    val monitor = """#version 300 es
        precision highp float;
        uniform highp sampler2D source;
        uniform int logView;
        in highp vec2 uv;
        out vec4 colour;
        float linear(float y) {return y>.149658 ? (pow(10.0,(y-.385537)/.247190)-.052272)/5.555556 : (y-.092809)/5.367655;}
        float srgb(float x) {return x<=.0031308?12.92*x:1.055*pow(x,1.0/2.4)-.055;}
        void main() {
            vec3 logValue=texture(source,uv).rgb;
            if(logView==1){colour=vec4(clamp(logValue,0.0,1.0),1.0);return;}
            vec3 a=vec3(linear(logValue.r),linear(logValue.g),linear(logValue.b));
            // AWG3 -> XYZ D65 -> linear Rec.709, row-major coefficients.
            vec3 r=vec3(dot(a,vec3(1.617523,-.537286,-.080237)),
                        dot(a,vec3(-.070573,1.334613,-.264040)),
                        dot(a,vec3(-.021102,-.226954,1.248056)));
            r=max(r,0.0);r=r/(1.0+r);
            colour=vec4(srgb(r.r),srgb(r.g),srgb(r.b),1.0);
        }
    """.trimIndent()
    // The RAW row convention is top-down. Surface queues consume a top-down video image.
    val surface = """#version 300 es
        precision highp float;
        uniform highp sampler2D source;
        in highp vec2 uv;
        out vec4 colour;
        void main(){colour=vec4(clamp(texture(source,vec2(uv.x,1.0-uv.y)).rgb,0.0,1.0),1.0);}
    """.trimIndent()
}
