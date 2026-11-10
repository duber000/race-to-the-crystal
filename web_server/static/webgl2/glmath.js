/**
 * glmath.js - Minimal vector and matrix math for the WebGL2 renderer.
 *
 * Column-major Float32Array(16) mat4, matching WebGL's uniform layout.
 * Only what the game needs: construction, perspective/lookAt projection,
 * matrix multiply/invert, TRS composition, and a small Vec3 class with the
 * operations the camera controller uses.
 */

export class Vec3 {
    constructor(x = 0, y = 0, z = 0) {
        this.x = x;
        this.y = y;
        this.z = z;
    }

    clone() {
        return new Vec3(this.x, this.y, this.z);
    }

    copyFrom(other) {
        this.x = other.x;
        this.y = other.y;
        this.z = other.z;
        return this;
    }

    set(x, y, z) {
        this.x = x;
        this.y = y;
        this.z = z;
        return this;
    }

    add(other) {
        return new Vec3(this.x + other.x, this.y + other.y, this.z + other.z);
    }

    subtract(other) {
        return new Vec3(this.x - other.x, this.y - other.y, this.z - other.z);
    }

    scale(scalar) {
        return new Vec3(this.x * scalar, this.y * scalar, this.z * scalar);
    }

    length() {
        return Math.hypot(this.x, this.y, this.z);
    }

    lengthSquared() {
        return this.x * this.x + this.y * this.y + this.z * this.z;
    }

    normalize() {
        const len = this.length();
        if (len < 1e-12) return new Vec3(0, 0, 0);
        return new Vec3(this.x / len, this.y / len, this.z / len);
    }

    cross(other) {
        return new Vec3(
            this.y * other.z - this.z * other.y,
            this.z * other.x - this.x * other.z,
            this.x * other.y - this.y * other.x,
        );
    }

    dot(other) {
        return this.x * other.x + this.y * other.y + this.z * other.z;
    }
}

export const Vec3Lerp = (a, b, t) => new Vec3(
    a.x + (b.x - a.x) * t,
    a.y + (b.y - a.y) * t,
    a.z + (b.z - a.z) * t,
);

// --- mat4 -----------------------------------------------------------------

export function mat4Identity() {
    const m = new Float32Array(16);
    m[0] = 1; m[5] = 1; m[10] = 1; m[15] = 1;
    return m;
}

export function mat4Multiply(a, b) {
    const out = new Float32Array(16);
    for (let col = 0; col < 4; col++) {
        for (let row = 0; row < 4; row++) {
            out[col * 4 + row] =
                a[row] * b[col * 4] +
                a[4 + row] * b[col * 4 + 1] +
                a[8 + row] * b[col * 4 + 2] +
                a[12 + row] * b[col * 4 + 3];
        }
    }
    return out;
}

export function mat4Perspective(fovYRad, aspect, near, far) {
    const f = 1.0 / Math.tan(fovYRad / 2);
    const nf = 1 / (near - far);
    const out = new Float32Array(16);
    out[0] = f / aspect;
    out[5] = f;
    out[10] = (far + near) * nf;
    out[11] = -1;
    out[14] = 2 * far * near * nf;
    return out;
}

export function mat4LookAt(eye, target, up) {
    const zAxis = eye.subtract(target).normalize();
    const xAxis = up.cross(zAxis).normalize();
    const yAxis = zAxis.cross(xAxis);

    const out = new Float32Array(16);
    out[0] = xAxis.x; out[1] = yAxis.x; out[2] = zAxis.x; out[3] = 0;
    out[4] = xAxis.y; out[5] = yAxis.y; out[6] = zAxis.y; out[7] = 0;
    out[8] = xAxis.z; out[9] = yAxis.z; out[10] = zAxis.z; out[11] = 0;
    out[12] = -(xAxis.dot(eye));
    out[13] = -(yAxis.dot(eye));
    out[14] = -(zAxis.dot(eye));
    out[15] = 1;
    return out;
}

export function mat4Invert(m) {
    const out = new Float32Array(16);

    const a00 = m[0], a01 = m[1], a02 = m[2], a03 = m[3];
    const a10 = m[4], a11 = m[5], a12 = m[6], a13 = m[7];
    const a20 = m[8], a21 = m[9], a22 = m[10], a23 = m[11];
    const a30 = m[12], a31 = m[13], a32 = m[14], a33 = m[15];

    const b00 = a00 * a11 - a01 * a10;
    const b01 = a00 * a12 - a02 * a10;
    const b02 = a00 * a13 - a03 * a10;
    const b03 = a01 * a12 - a02 * a11;
    const b04 = a01 * a13 - a03 * a11;
    const b05 = a02 * a13 - a03 * a12;
    const b06 = a20 * a31 - a21 * a30;
    const b07 = a20 * a32 - a22 * a30;
    const b08 = a20 * a33 - a23 * a30;
    const b09 = a21 * a32 - a22 * a31;
    const b10 = a21 * a33 - a23 * a31;
    const b11 = a22 * a33 - a23 * a32;

    let det = b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06;
    if (!det) return null;
    det = 1.0 / det;

    out[0] = (a11 * b11 - a12 * b10 + a13 * b09) * det;
    out[1] = (a02 * b10 - a01 * b11 - a03 * b09) * det;
    out[2] = (a31 * b05 - a32 * b04 + a33 * b03) * det;
    out[3] = (a22 * b04 - a21 * b05 - a23 * b03) * det;
    out[4] = (a12 * b08 - a10 * b11 - a13 * b07) * det;
    out[5] = (a00 * b11 - a02 * b08 + a03 * b07) * det;
    out[6] = (a32 * b02 - a30 * b05 - a33 * b01) * det;
    out[7] = (a20 * b05 - a22 * b02 + a23 * b01) * det;
    out[8] = (a10 * b10 - a11 * b08 + a13 * b06) * det;
    out[9] = (a01 * b08 - a00 * b10 - a03 * b06) * det;
    out[10] = (a30 * b04 - a31 * b02 + a33 * b00) * det;
    out[11] = (a21 * b02 - a20 * b04 - a23 * b00) * det;
    out[12] = (a11 * b07 - a10 * b09 - a12 * b06) * det;
    out[13] = (a00 * b09 - a01 * b07 + a02 * b06) * det;
    out[14] = (a31 * b01 - a30 * b03 - a32 * b00) * det;
    out[15] = (a20 * b03 - a21 * b01 + a22 * b00) * det;
    return out;
}

export function mat4Translation(x, y, z) {
    const m = mat4Identity();
    m[12] = x;
    m[13] = y;
    m[14] = z;
    return m;
}

export function mat4Scaling(x, y, z) {
    const m = new Float32Array(16);
    m[0] = x; m[5] = y; m[10] = z; m[15] = 1;
    return m;
}

export function mat4RotationX(rad) {
    const m = mat4Identity();
    const c = Math.cos(rad), s = Math.sin(rad);
    m[5] = c; m[6] = s;
    m[9] = -s; m[10] = c;
    return m;
}

export function mat4RotationY(rad) {
    const m = mat4Identity();
    const c = Math.cos(rad), s = Math.sin(rad);
    m[0] = c; m[2] = -s;
    m[8] = s; m[10] = c;
    return m;
}

export function mat4RotationZ(rad) {
    const m = mat4Identity();
    const c = Math.cos(rad), s = Math.sin(rad);
    m[0] = c; m[1] = s;
    m[4] = -s; m[5] = c;
    return m;
}

// Compose model = T * R * S (rotateY, rotateX, rotateZ applied in ZYX order,
// matching how the renderer rotates the crystal frames and rings).
export function mat4ComposeTRS(translation, rotationEuler, scale) {
    const t = mat4Translation(translation.x, translation.y, translation.z);
    let r = mat4Identity();
    if (rotationEuler) {
        r = mat4Multiply(mat4RotationY(rotationEuler.y || 0), mat4Identity());
        r = mat4Multiply(r, mat4RotationX(rotationEuler.x || 0));
        r = mat4Multiply(r, mat4RotationZ(rotationEuler.z || 0));
    }
    const s = mat4Scaling(
        scale ? scale.x : 1,
        scale ? scale.y : 1,
        scale ? scale.z : 1,
    );
    return mat4Multiply(t, mat4Multiply(r, s));
}

/** Transform a world-space point by a column-major mat4; returns x/y/z/w. */
export function mat4TransformPoint(m, p) {
    const x = m[0] * p.x + m[4] * p.y + m[8] * p.z + m[12];
    const y = m[1] * p.x + m[5] * p.y + m[9] * p.z + m[13];
    const z = m[2] * p.x + m[6] * p.y + m[10] * p.z + m[14];
    const w = m[3] * p.x + m[7] * p.y + m[11] * p.z + m[15];
    return { x, y, z, w };
}
