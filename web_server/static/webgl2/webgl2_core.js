/**
 * webgl2_core.js - WebGL2 plumbing: context, programs, vertex buffers.
 *
 * Attribute layout is fixed: location 0 = aPosition (vec3), location 1 =
 * aNormal (vec3), location 2 = aUV (vec2). Meshes are uploaded into VAOs.
 * Line meshes upload raw non-indexed positions only.
 */

export function getWebGL2Context(canvas, options = {}) {
    const gl = canvas.getContext('webgl2', {
        antialias: options.antialias !== false,
        alpha: false,
        powerPreference: 'high-performance',
        ...options,
    });
    return gl || null;
}

export function compileShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        const log = gl.getShaderInfoLog(shader);
        gl.deleteShader(shader);
        throw new Error(`Shader compile failed: ${log}`);
    }
    return shader;
}

export function createProgram(gl, vertexSource, fragmentSource, uniformNames = []) {
    const vs = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
    const fs = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
    const program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.bindAttribLocation(program, 0, 'aPosition');
    gl.bindAttribLocation(program, 1, 'aNormal');
    gl.bindAttribLocation(program, 2, 'aUV');
    gl.linkProgram(program);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        const log = gl.getProgramInfoLog(program);
        gl.deleteProgram(program);
        throw new Error(`Program link failed: ${log}`);
    }

    const uniforms = {};
    for (const name of uniformNames) {
        uniforms[name] = gl.getUniformLocation(program, name);
    }
    return { program, uniforms };
}

function createArrayBuffer(gl, data) {
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    return buffer;
}

/** Upload a built mesh (positions [normals] [uvs] [indices]) into a VAO. */
export function createMesh(gl, mesh) {
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);

    const positionBuffer = createArrayBuffer(gl, mesh.positions);
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);

    if (mesh.normals) {
        const normalBuffer = createArrayBuffer(gl, mesh.normals);
        gl.bindBuffer(gl.ARRAY_BUFFER, normalBuffer);
        gl.enableVertexAttribArray(1);
        gl.vertexAttribPointer(1, 3, gl.FLOAT, false, 0, 0);
    }
    if (mesh.uvs) {
        const uvBuffer = createArrayBuffer(gl, mesh.uvs);
        gl.bindBuffer(gl.ARRAY_BUFFER, uvBuffer);
        gl.enableVertexAttribArray(2);
        gl.vertexAttribPointer(2, 2, gl.FLOAT, false, 0, 0);
    }

    let indexBuffer = null;
    let vertexCount = mesh.positions.length / 3;
    if (mesh.indices) {
        indexBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);
        vertexCount = mesh.indices.length;
    }

    gl.bindVertexArray(null);
    return {
        vao,
        indexBuffer,
        draw: () => {
            gl.bindVertexArray(vao);
            if (indexBuffer) {
                const type = mesh.indices instanceof Uint16Array ? gl.UNSIGNED_SHORT : gl.UNSIGNED_INT;
                gl.drawElements(gl.TRIANGLES, vertexCount, type, 0);
            } else {
                gl.drawArrays(gl.TRIANGLES, 0, vertexCount);
            }
            gl.bindVertexArray(null);
        },
        dispose: () => {
            gl.deleteVertexArray(vao);
            gl.deleteBuffer(positionBuffer);
            if (indexBuffer) gl.deleteBuffer(indexBuffer);
        },
    };
}

/** Raw positions for GL_LINES / GL_LINE_LOOP (no attributes beyond location 0). */
export function createLineMesh(gl, positions) {
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const positionBuffer = createArrayBuffer(gl, positions);
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
    const vertexCount = positions.length / 3;
    return {
        vao,
        draw: (mode = gl.LINES) => {
            gl.bindVertexArray(vao);
            gl.drawArrays(mode, 0, vertexCount);
            gl.bindVertexArray(null);
        },
        dispose: () => {
            gl.deleteVertexArray(vao);
            gl.deleteBuffer(positionBuffer);
        },
    };
}

/**
 * VAO for CPU-simulated point sprites.
 * Attributes: 0 = position (vec3), 1 = style (vec2: size, alpha), 2 = color (vec3).
 * Positions/styles/colors are re-uploaded each frame.
 */
export function createPointMesh(gl, capacity) {
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, capacity * 3 * 4, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);

    const styleBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, styleBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, capacity * 2 * 4, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 0, 0);

    const colorBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, colorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, capacity * 3 * 4, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(2);
    gl.vertexAttribPointer(2, 3, gl.FLOAT, false, 0, 0);

    gl.bindVertexArray(null);
    return { vao, positionBuffer, styleBuffer, colorBuffer };
}
