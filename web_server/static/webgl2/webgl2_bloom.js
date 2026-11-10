/**
 * webgl2_bloom.js - Bloom + composite post-processing pass
 *
 * Half-res bloom: bright-pass the rendered scene, separable 9-tap gaussian
 * blur (two iterations for a wider glow), then composite scene + bloom over
 * a fullscreen triangle onto the canvas. The composite pass also applies a
 * soft vignette and a whisper of film grain — both are nearly free in the
 * same shader and recover the Babylon DefaultRenderingPipeline's polish.
 *
 * Opt out with ?bloom=0 — the renderer then draws straight to the canvas,
 * identical to the Phase 1 path.
 *
 * Render targets:
 *  - sceneFBO: full-res scene color (RGBA16F if the EXT_color_buffer_float
 *    extension is available, otherwise RGBA8) + depth renderbuffer.
 *  - blurA / blurB: half-res ping-pong textures for the blur.
 */

const GLSL_VERSION = '#version 300 es\n';

const VERT_FULLSCREEN = `${GLSL_VERSION}
layout(location = 0) in vec2 aPosition;   // clip-space triangle
out vec2 vUV;
void main() {
    vUV = aPosition * 0.5 + 0.5;
    gl_Position = vec4(aPosition, 0.0, 1.0);
}`;

const FRAG_BRIGHT = `${GLSL_VERSION}
precision highp float;
in vec2 vUV;
uniform sampler2D uScene;
uniform float uThreshold;
out vec4 fragColor;
void main() {
    vec3 c = texture(uScene, vUV).rgb;
    float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
    float over = max(lum - uThreshold, 0.0);
    // Keep the hue, drop everything below the knee to black.
    fragColor = vec4(c * (over / max(lum, 1e-4)), 1.0);
}`;

const FRAG_BLUR = `${GLSL_VERSION}
precision highp float;
in vec2 vUV;
uniform sampler2D uTexture;
uniform vec2 uDirection;   // (1/w, 0) or (0, 1/h)
out vec4 fragColor;
void main() {
    // 9-tap gaussian, sigma ~2px at this kernel size.
    const float weights[5] = float[5](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    vec3 result = texture(uTexture, vUV).rgb * weights[0];
    for (int i = 1; i < 5; i++) {
        vec2 offset = uDirection * float(i);
        result += texture(uTexture, vUV + offset).rgb * weights[i];
        result += texture(uTexture, vUV - offset).rgb * weights[i];
    }
    fragColor = vec4(result, 1.0);
}`;

const FRAG_COMPOSITE = `${GLSL_VERSION}
precision highp float;
in vec2 vUV;
uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform float uBloomStrength;
uniform float uTimeSeed;
uniform float uGrain;
uniform float uVignette;
out vec4 fragColor;
void main() {
    vec3 scene = texture(uScene, vUV).rgb;
    vec3 bloom = texture(uBloom, vUV).rgb;
    vec3 color = scene + bloom * uBloomStrength;

    // Soft vignette — keeps the eye on the board center.
    vec2 d = vUV - 0.5;
    color *= 1.0 - dot(d, d) * uVignette;

    // Static-hash film grain, amplitude ~ a few 8-bit steps.
    float n = fract(sin(dot(vUV * uTimeSeed, vec2(12.9898, 78.233))) * 43758.5453);
    color += (n - 0.5) * uGrain;

    fragColor = vec4(color, 1.0);
}`;

function createProgram(gl, vsSource, fsSource, uniformNames) {
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, vsSource);
    gl.compileShader(vs);
    if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {
        throw new Error('Bloom vertex shader: ' + gl.getShaderInfoLog(vs));
    }
    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, fsSource);
    gl.compileShader(fs);
    if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
        throw new Error('Bloom fragment shader: ' + gl.getShaderInfoLog(fs));
    }
    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        throw new Error('Bloom program link: ' + gl.getProgramInfoLog(program));
    }
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    const uniforms = {};
    for (const name of uniformNames) {
        uniforms[name] = gl.getUniformLocation(program, name);
    }
    return { program, uniforms };
}

function createColorTexture(gl, width, height, internalFormat, format, type) {
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, width, height, 0, format, type, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.bindTexture(gl.TEXTURE_2D, null);
    return texture;
}

class BloomPass {
    constructor(gl) {
        this.gl = gl;
        this.available = false;
        this.width = 0;
        this.height = 0;

        const hasFloatTarget = !!gl.getExtension('EXT_color_buffer_float');
        this.sceneInternalFormat = hasFloatTarget ? gl.RGBA16F : gl.RGBA8;
        this.sceneType = hasFloatTarget ? gl.HALF_FLOAT : gl.UNSIGNED_BYTE;
        this.usingHalfFloat = hasFloatTarget;

        this.brightProgram = createProgram(gl, VERT_FULLSCREEN, FRAG_BRIGHT, ['uScene', 'uThreshold']);
        this.blurProgram = createProgram(gl, VERT_FULLSCREEN, FRAG_BLUR, ['uTexture', 'uDirection']);
        this.compositeProgram = createProgram(gl, VERT_FULLSCREEN, FRAG_COMPOSITE,
            ['uScene', 'uBloom', 'uBloomStrength', 'uTimeSeed', 'uGrain', 'uVignette']);

        // Fullscreen triangle (covers the viewport with one primitive).
        this.vao = gl.createVertexArray();
        gl.bindVertexArray(this.vao);
        this.triangleBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, this.triangleBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
        gl.bindVertexArray(null);

        // Scene render target (full res).
        this.sceneColor = null;
        this.depthBuffer = gl.createRenderbuffer();
        this.sceneFBO = gl.createFramebuffer();

        // Half-res ping-pong for the blur.
        this.blurA = null;
        this.blurB = null;
        this.blurA_FBO = gl.createFramebuffer();
        this.blurB_FBO = gl.createFramebuffer();

        this.bloomThreshold = 0.55;
        this.bloomStrength = 0.9;
        this.grain = 0.045;
        this.vignette = 0.55;
    }

    /** Allocate/resize targets. Returns true if the scene FBO is usable. */
    resize(width, height) {
        const gl = this.gl;
        if (width === this.width && height === this.height && this.sceneColor) {
            return this.available;
        }
        this.width = width;
        this.height = height;

        // Free old targets.
        if (this.sceneColor) gl.deleteTexture(this.sceneColor);
        if (this.blurA) gl.deleteTexture(this.blurA);
        if (this.blurB) gl.deleteTexture(this.blurB);

        this.sceneColor = createColorTexture(gl, width, height, this.sceneInternalFormat, gl.RGBA, this.sceneType);
        gl.bindRenderbuffer(gl.RENDERBUFFER, this.depthBuffer);
        gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, width, height);
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.sceneFBO);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.sceneColor, 0);
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, this.depthBuffer);

        const bw = Math.max(1, width >> 1);
        const bh = Math.max(1, height >> 1);
        const bf = gl.RGBA16F === this.sceneInternalFormat ? [gl.RGBA16F, gl.RGBA, gl.HALF_FLOAT] : [gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE];
        this.blurA = createColorTexture(gl, bw, bh, bf[0], bf[1], bf[2]);
        this.blurB = createColorTexture(gl, bw, bh, bf[0], bf[1], bf[2]);
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.blurA_FBO);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.blurA, 0);
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.blurB_FBO);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.blurB, 0);

        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.bindRenderbuffer(gl.RENDERBUFFER, null);

        // Verify both FBOs are complete.
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.sceneFBO);
        const sceneOK = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.blurA_FBO);
        const blurAOK = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.blurB_FBO);
        const blurBOK = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);

        this.available = sceneOK && blurAOK && blurBOK;
        if (!this.available) {
            console.warn('[webgl2] bloom disabled: framebuffer incomplete (scene/half-float target unsupported?)');
        }
        return this.available;
    }

    /** Bind the scene FBO. Call before clearing and drawing the scene. */
    beginScene(width, height) {
        if (!this.resize(width, height)) return false;
        this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, this.sceneFBO);
        this.gl.viewport(0, 0, this.width, this.height);
        return true;
    }

    /**
     * Resolve the scene to the canvas with bloom, vignette and grain.
     * Call after all scene draws have completed.
     */
    endScene(timeSeconds) {
        const gl = this.gl;
        const bw = Math.max(1, this.width >> 1);
        const bh = Math.max(1, this.height >> 1);

        gl.disable(gl.DEPTH_TEST);
        gl.depthMask(false);
        gl.bindVertexArray(this.vao);

        // --- Bright pass: scene -> blurA (half res) ---
        gl.bindFramebuffer(gl.FRAMEBUFFER, this.blurA_FBO);
        gl.viewport(0, 0, bw, bh);
        gl.disable(gl.BLEND);
        gl.useProgram(this.brightProgram.program);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.sceneColor);
        gl.uniform1i(this.brightProgram.uniforms.uScene, 0);
        gl.uniform1f(this.brightProgram.uniforms.uThreshold, this.bloomThreshold);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        // --- Blur: two ping-pong iterations (horizontal then vertical) ---
        for (let i = 0; i < 2; i++) {
            // horizontal: blurA -> blurB
            gl.bindFramebuffer(gl.FRAMEBUFFER, this.blurB_FBO);
            gl.viewport(0, 0, bw, bh);
            gl.useProgram(this.blurProgram.program);
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, this.blurA);
            gl.uniform1i(this.blurProgram.uniforms.uTexture, 0);
            gl.uniform2f(this.blurProgram.uniforms.uDirection, 1.0 / bw, 0.0);
            gl.drawArrays(gl.TRIANGLES, 0, 3);
            // vertical: blurB -> blurA
            gl.bindFramebuffer(gl.FRAMEBUFFER, this.blurA_FBO);
            gl.viewport(0, 0, bw, bh);
            gl.bindTexture(gl.TEXTURE_2D, this.blurB);
            gl.uniform2f(this.blurProgram.uniforms.uDirection, 0.0, 1.0 / bh);
            gl.drawArrays(gl.TRIANGLES, 0, 3);
        }

        // --- Composite: scene + bloom -> canvas ---
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, this.width, this.height);
        gl.useProgram(this.compositeProgram.program);
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.sceneColor);
        gl.uniform1i(this.compositeProgram.uniforms.uScene, 0);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, this.blurA);
        gl.uniform1i(this.compositeProgram.uniforms.uBloom, 1);
        gl.uniform1f(this.compositeProgram.uniforms.uBloomStrength, this.bloomStrength);
        gl.uniform1f(this.compositeProgram.uniforms.uTimeSeed, (timeSeconds * 61.7) + 11.3);
        gl.uniform1f(this.compositeProgram.uniforms.uGrain, this.grain);
        gl.uniform1f(this.compositeProgram.uniforms.uVignette, this.vignette);
        gl.drawArrays(gl.TRIANGLES, 0, 3);

        gl.activeTexture(gl.TEXTURE0);
        gl.bindVertexArray(null);
        gl.depthMask(true);
        gl.enable(gl.DEPTH_TEST);
    }

    dispose() {
        const gl = this.gl;
        if (this.sceneColor) gl.deleteTexture(this.sceneColor);
        if (this.blurA) gl.deleteTexture(this.blurA);
        if (this.blurB) gl.deleteTexture(this.blurB);
        gl.deleteFramebuffer(this.sceneFBO);
        gl.deleteFramebuffer(this.blurA_FBO);
        gl.deleteFramebuffer(this.blurB_FBO);
        gl.deleteRenderbuffer(this.depthBuffer);
        gl.deleteBuffer(this.triangleBuffer);
        gl.deleteVertexArray(this.vao);
        gl.deleteProgram(this.brightProgram.program);
        gl.deleteProgram(this.blurProgram.program);
        gl.deleteProgram(this.compositeProgram.program);
        this.available = false;
    }
}

export { BloomPass };
