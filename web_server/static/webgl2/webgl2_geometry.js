/**
 * webgl2_geometry.js - Geometry builders for the WebGL2 renderer.
 *
 * Each builder returns plain typed arrays (positions/normals/uvs/indices);
 * webgl2_core.js uploads them to GPU buffers. Nothing here touches WebGL.
 *
 * NOTE: the renderer does not cull backfaces. The meshes are tiny (the
 * whole scene is a few hundred triangles beyond a proxy sphere), so winding
 * order is kept correct anyway for hygiene but is not load-bearing.
 */

/** Ground quad on the XZ plane (y = 0), UV-mapped 0..1, normal +Y. */
export function buildGround(width, depth) {
    return {
        positions: new Float32Array([
            0, 0, 0,
            width, 0, 0,
            width, 0, depth,
            0, 0, depth,
        ]),
        normals: new Float32Array([
            0, 1, 0,
            0, 1, 0,
            0, 1, 0,
            0, 1, 0,
        ]),
        uvs: new Float32Array([
            0, 0,
            1, 0,
            1, 1,
            0, 1,
        ]),
        indices: new Uint16Array([0, 2, 1, 0, 3, 2]),
    };
}

/** Box centered on the origin, flat normals per face (24 vertices). */
export function buildBox(sx, sy, sz) {
    const x = sx / 2, y = sy / 2, z = sz / 2;
    const faces = [
        { n: [0, 1, 0], v: [[-x, y, z], [x, y, z], [x, y, -z], [-x, y, -z]] },
        { n: [0, -1, 0], v: [[-x, -y, -z], [x, -y, -z], [x, -y, z], [-x, -y, z]] },
        { n: [0, 0, 1], v: [[-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]] },
        { n: [0, 0, -1], v: [[x, -y, -z], [-x, -y, -z], [-x, y, -z], [x, y, -z]] },
        { n: [1, 0, 0], v: [[x, -y, z], [x, -y, -z], [x, y, -z], [x, y, z]] },
        { n: [-1, 0, 0], v: [[-x, -y, -z], [-x, -y, z], [-x, y, z], [-x, y, -z]] },
    ];

    const positions = [];
    const normals = [];
    const indices = [];
    let base = 0;
    for (const face of faces) {
        for (const v of face.v) {
            positions.push(v[0], v[1], v[2]);
            normals.push(face.n[0], face.n[1], face.n[2]);
        }
        indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
        base += 4;
    }
    return {
        positions: new Float32Array(positions),
        normals: new Float32Array(normals),
        indices: new Uint16Array(indices),
    };
}

/**
 * Cylinder / hex prism on the Y axis, centered on the origin.
 * flatNormals=true duplicates vertices per side face so a hexagon reads as a
 * prism rather than a smooth tube.
 */
export function buildCylinder(radius, height, segments, flatNormals = false) {
    const positions = [];
    const normals = [];
    const indices = [];
    const half = height / 2;
    const step = (Math.PI * 2) / segments;

    // --- Side band ---
    if (flatNormals) {
        // One quad per face with duplicated vertices and a face normal.
        let base = 0;
        for (let i = 0; i < segments; i++) {
            const a0 = i * step;
            const a1 = (i + 1) * step;
            const mid = (a0 + a1) / 2;
            const nx = Math.cos(mid);
            const nz = Math.sin(mid);
            const corners = [
                [Math.cos(a0) * radius, half, Math.sin(a0) * radius],
                [Math.cos(a1) * radius, half, Math.sin(a1) * radius],
                [Math.cos(a1) * radius, -half, Math.sin(a1) * radius],
                [Math.cos(a0) * radius, -half, Math.sin(a0) * radius],
            ];
            for (const c of corners) {
                positions.push(c[0], c[1], c[2]);
                normals.push(nx, 0, nz);
            }
            indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
            base += 4;
        }
    } else {
        for (let i = 0; i <= segments; i++) {
            const angle = i * step;
            const nx = Math.cos(angle);
            const nz = Math.sin(angle);
            positions.push(nx * radius, half, nz * radius, nx * radius, -half, nz * radius);
            normals.push(nx, 0, nz, nx, 0, nz);
        }
        for (let i = 0; i < segments; i++) {
            const a = i * 2;
            const b = a + 2;
            indices.push(a, b, a + 1, b, b + 1, a + 1);
        }
    }

    // --- Caps (fans; winding toward the viewer of each cap) ---
    const topCenter = positions.length / 3;
    positions.push(0, half, 0);
    normals.push(0, 1, 0);
    const bottomCenter = positions.length / 3;
    positions.push(0, -half, 0);
    normals.push(0, -1, 0);

    const capRingBase = positions.length / 3;
    for (let i = 0; i <= segments; i++) {
        const angle = i * step;
        const cx = Math.cos(angle) * radius, sz = Math.sin(angle) * radius;
        positions.push(cx, half, sz);
        normals.push(0, 1, 0);
        positions.push(cx, -half, sz);
        normals.push(0, -1, 0);
    }
    for (let i = 0; i < segments; i++) {
        const t0 = capRingBase + i * 2;
        const t1 = capRingBase + (i + 1) * 2;
        indices.push(topCenter, t0, t1);        // +Y facing
        indices.push(bottomCenter, t1, t0);     // -Y facing
    }

    return {
        positions: new Float32Array(positions),
        normals: new Float32Array(normals),
        indices: new Uint32Array(indices),
    };
}

/** UV sphere (with UVs — used for the starfield skybox); normals radial outward. */
export function buildUVSphere(radius, rings = 16, sectors = 24) {
    const positions = [];
    const normals = [];
    const uvs = [];
    const indices = [];

    for (let ring = 0; ring <= rings; ring++) {
        const theta = (ring / rings) * Math.PI; // 0 = top pole
        const sinT = Math.sin(theta);
        const cosT = Math.cos(theta);
        for (let sector = 0; sector <= sectors; sector++) {
            const phi = (sector / sectors) * Math.PI * 2;
            const x = sinT * Math.cos(phi);
            const y = cosT;
            const z = sinT * Math.sin(phi);
            positions.push(radius * x, radius * y, radius * z);
            normals.push(x, y, z);
            uvs.push(sector / sectors, ring / rings);
        }
    }

    const stride = sectors + 1;
    for (let ring = 0; ring < rings; ring++) {
        for (let sector = 0; sector < sectors; sector++) {
            const a = ring * stride + sector;
            const b = a + stride;
            indices.push(a, a + 1, b, a + 1, b + 1, b);
        }
    }

    return {
        positions: new Float32Array(positions),
        normals: new Float32Array(normals),
        uvs: new Float32Array(uvs),
        indices: new Uint32Array(indices),
    };
}

/** Torus lying on the XZ plane (flat "donut" ring, tube centered on Y). */
export function buildTorus(majorRadius, minorRadius, radialSegments = 24, tubularSegments = 16) {
    const positions = [];
    const normals = [];
    const indices = [];

    for (let i = 0; i <= radialSegments; i++) {
        const u = (i / radialSegments) * Math.PI * 2;
        const cosU = Math.cos(u), sinU = Math.sin(u);
        for (let j = 0; j <= tubularSegments; j++) {
            const v = (j / tubularSegments) * Math.PI * 2;
            const cosV = Math.cos(v), sinV = Math.sin(v);
            const ringX = majorRadius + minorRadius * cosV;
            const x = ringX * cosU;
            const y = minorRadius * sinV;
            const z = ringX * sinU;
            positions.push(x, y, z);
            normals.push(cosV * cosU, sinV, cosV * sinU);
        }
    }

    const stride = tubularSegments + 1;
    for (let i = 0; i < radialSegments; i++) {
        for (let j = 0; j < tubularSegments; j++) {
            const a = i * stride + j;
            const b = a + stride;
            indices.push(a, a + 1, b, a + 1, b + 1, b);
        }
    }

    return {
        positions: new Float32Array(positions),
        normals: new Float32Array(normals),
        indices: new Uint32Array(indices),
    };
}

/** Flat quad in the XY plane facing +Z (billboards, labels, pips). */
export function buildQuad(width, height) {
    const w = width / 2, h = height / 2;
    return {
        positions: new Float32Array([
            -w, -h, 0,
            w, -h, 0,
            w, h, 0,
            -w, h, 0,
        ]),
        normals: new Float32Array([
            0, 0, 1,
            0, 0, 1,
            0, 0, 1,
            0, 0, 1,
        ]),
        uvs: new Float32Array([
            0, 0,
            1, 0,
            1, 1,
            0, 1,
        ]),
        indices: new Uint16Array([0, 1, 2, 0, 2, 3]),
    };
}

/**
 * Icosphere: base icosahedron + midpoint subdivision. Returns a triangle
 * soup (positions/normals, no indices) plus a welded edge list for the
 * wireframe gold frames.
 */
export function buildIcoSphere(radius, subdivisions = 1) {
    const t = (1 + Math.sqrt(5)) / 2;
    const verts = [
        -1, t, 0, 1, t, 0, -1, -t, 0, 1, -t, 0,
        0, -1, t, 0, 1, t, 0, -1, -t, 0, 1, -t,
        t, 0, -1, t, 0, 1, -t, 0, -1, -t, 0, 1,
    ];

    let faces = [
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1],
    ];

    for (let s = 0; s < subdivisions; s++) {
        const midpointCache = new Map();
        const newFaces = [];
        const midpoint = (a, b) => {
            const key = a < b ? `${a}_${b}` : `${b}_${a}`;
            if (midpointCache.has(key)) return midpointCache.get(key);
            verts.push(
                (verts[a * 3] + verts[b * 3]) / 2,
                (verts[a * 3 + 1] + verts[b * 3 + 1]) / 2,
                (verts[a * 3 + 2] + verts[b * 3 + 2]) / 2,
            );
            const idx = verts.length / 3 - 1;
            midpointCache.set(key, idx);
            return idx;
        };
        for (const [a, b, c] of faces) {
            const ab = midpoint(a, b);
            const bc = midpoint(b, c);
            const ca = midpoint(c, a);
            newFaces.push([a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]);
        }
        faces = newFaces;
    }

    const pos = new Float32Array(faces.length * 9);
    for (let f = 0; f < faces.length; f++) {
        const [a, b, c] = faces[f];
        for (let k = 0; k < 3; k++) {
            const src = [a, b, c][k] * 3;
            const dst = f * 9 + k * 3;
            const len = Math.hypot(verts[src], verts[src + 1], verts[src + 2]) || 1;
            pos[dst] = (verts[src] / len) * radius;
            pos[dst + 1] = (verts[src + 1] / len) * radius;
            pos[dst + 2] = (verts[src + 2] / len) * radius;
        }
    }
    const nrm = new Float32Array(pos.length);
    for (let i = 0; i < pos.length; i += 3) {
        const len = Math.hypot(pos[i], pos[i + 1], pos[i + 2]) || 1;
        nrm[i] = pos[i] / len;
        nrm[i + 1] = pos[i + 1] / len;
        nrm[i + 2] = pos[i + 2] / len;
    }

    // Welded edge list for GL_LINES (the gold wireframe look).
    const edgeSet = new Set();
    const edges = [];
    for (const [a, b, c] of faces) {
        for (const [i, j] of [[a, b], [b, c], [c, a]]) {
            const key = i < j ? `${i}_${j}` : `${j}_${i}`;
            if (edgeSet.has(key)) continue;
            edgeSet.add(key);
            // Endpoint positions must be normalized to the sphere surface —
            // reuse the original (unnormalized) verts and normalize here.
            for (const v of [i, j]) {
                const src = v * 3;
                const len = Math.hypot(verts[src], verts[src + 1], verts[src + 2]) || 1;
                edges.push(
                    (verts[src] / len) * radius,
                    (verts[src + 1] / len) * radius,
                    (verts[src + 2] / len) * radius,
                );
            }
        }
    }

    return {
        positions: pos,
        normals: nrm,
        indices: null, // triangle soup; draw directly
        edges: new Float32Array(edges),
    };
}

/** LINE_LOOP of a circle in the XZ plane (threat rings on tokens). */
export function buildCircleLine(radius, segments = 40) {
    const positions = new Float32Array(segments * 3);
    for (let i = 0; i < segments; i++) {
        const angle = (i / segments) * Math.PI * 2;
        positions[i * 3] = Math.cos(angle) * radius;
        positions[i * 3 + 1] = 0;
        positions[i * 3 + 2] = Math.sin(angle) * radius;
    }
    return { positions };
}

/** LINE_LOOP of a square in the XZ plane. */
export function buildSquareLine(size) {
    const h = size / 2;
    return {
        positions: new Float32Array([
            -h, 0, -h,
            h, 0, -h,
            h, 0, h,
            -h, 0, h,
        ]),
    };
}
