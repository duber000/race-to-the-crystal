/**
 * webgl2_renderer.js - Vanilla WebGL2 Renderer3D
 *
 * A drop-in replacement for the Babylon.js Renderer3D, written against the
 * same public interface (duck-typed) as the original Renderer3D. The only
 * renderer since 2026-11-10 — Babylon.js was removed.
 *
 * The bloom/god-ray/PBR/cosmetics stack is on by default (see
 * docs/VANILLA-JS.md); ?bloom=0 / ?rays=0 / ?chroma=0 / ?sharpen=0 are the
 * opt-outs. Not implemented (documented decisions, see docs/VANILLA-JS.md):
 * shard-pillar refraction.
 *
 * Phase 1 goals: board, tokens, generators, crystal, indicators, camera,
 * picking, particles, health labels — playable end to end.
 * Phase 2 adds: bloom post-processing and the crystal effect animator
 * (fog/ghosts/lightning/whirlwind) — see webgl2_bloom.js and
 * webgl2_crystal_effects.js.
 */

import {
    BOARD_CONFIG, CELL_SIZE, BOARD_WIDTH, BOARD_HEIGHT, WALL_HEIGHT,
    TOKEN_HEIGHT, CRYSTAL_EFFECT,
} from '../game_client.constants.js';
import { AudioManager } from '../audio_manager.js';
import {
    Vec3, mat4Identity, mat4Multiply, mat4Perspective, mat4LookAt, mat4Invert,
    mat4Translation, mat4Scaling, mat4RotationX, mat4RotationY, mat4RotationZ,
    mat4ComposeTRS, mat4TransformPoint,
} from './glmath.js';
import {
    getWebGL2Context, createProgram, createMesh, createLineMesh, createPointMesh,
} from './webgl2_core.js';
import {
    buildGround, buildBox, buildCylinder, buildTorus, buildQuad,
    buildIcoSphere, buildCircleLine, buildSquareLine,
} from './webgl2_geometry.js';
import {
    createGridTexture, createHealthLabelTexture,
} from './webgl2_textures.js';
import { BloomPass } from './webgl2_bloom.js';
import { WebGL2CrystalEffectAnimator } from './webgl2_crystal_effects.js';

const TOKEN_CENTER_Y = Math.max(TOKEN_HEIGHT / 2, WALL_HEIGHT - TOKEN_HEIGHT / 2);
const GENERATOR_HEIGHT = Math.min(60, WALL_HEIGHT * 0.9);
const GENERATOR_CENTER_Y = WALL_HEIGHT - GENERATOR_HEIGHT / 2;
const CRYSTAL_HUB_Y = 60;
const CRYSTAL_BEAM_HUB_Y = 10;

// --- Palette (matches the Babylon renderer) --------------------------------
const CYAN_GLOW = [0.0, 0.78, 0.78];
const ORANGE_GLOW = [1.0, 0.65, 0.0];
const WHITE = [1.0, 1.0, 1.0];
const GREEN_GLOW = [0.0, 1.0, 0.0];
const RED_GLOW = [1.0, 0.0, 0.0];
const PLAYER_COLORS = [
    [0, 1, 1],     // Cyan
    [1, 0, 1],     // Magenta
    [1, 1, 0],     // Yellow
    [0, 1, 0],     // Green
];
const CRYSTAL_COLOR = [0, 0.8, 1.0];
const OBJECTIVE_PIP_EMPTY = [0.45, 0.45, 0.45];

const GLSL_VERSION = '#version 300 es\n';

const VERT_LIT = `${GLSL_VERSION}
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUV;
uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProj;
out vec3 vWorldPos;
out vec3 vNormal;
out vec2 vUV;
void main() {
    vec4 world = uModel * vec4(aPosition, 1.0);
    vWorldPos = world.xyz;
    // Normals: uniform scale and Y-axis rotations only, so mat3(uModel) is fine.
    vNormal = mat3(uModel) * aNormal;
    vUV = aUV;
    gl_Position = uProj * uView * world;
}`;

const FRAG_LIT = `${GLSL_VERSION}
precision highp float;
in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vUV;
uniform vec3 uColor;
uniform vec3 uEmissive;
uniform float uAlpha;
uniform vec3 uDirLightDir;      // points from the light toward the scene (legacy convention)
uniform vec3 uDirLightColor;
uniform float uMetallic;
uniform float uRoughness;
uniform vec3 uEyePos;
out vec4 fragColor;

// Analytic environment — a warm-dusty horizon, a deep-blue zenith and a
// near-black nadir, plus the sun. No environment texture; everything is
// evaluated per fragment, which is cheap at this scene size and removes
// the load-time IBL fetch entirely.
vec3 skyAmbient(vec3 d) {
    float y = d.y;
    vec3 zen = vec3(0.045, 0.062, 0.135);
    vec3 hor = vec3(0.46, 0.30, 0.185);
    vec3 gnd = vec3(0.022, 0.026, 0.043);
    vec3 col = mix(hor, zen, smoothstep(0.0, 0.7, y));
    col = mix(col, gnd, smoothstep(0.0, 0.5, -y));
    // Sun-side warmth, soft — no hard disk (that's the specular term's job).
    vec3 toSun = normalize(-uDirLightDir);
    col += uDirLightColor * pow(max(dot(d, toSun), 0.0), 2.5) * 0.18;
    return col;
}

vec3 skyColor(vec3 d, float roughness) {
    float y = d.y;
    vec3 zen = vec3(0.045, 0.062, 0.135);
    vec3 hor = vec3(0.46, 0.30, 0.185);
    vec3 gnd = vec3(0.022, 0.026, 0.043);
    vec3 col = mix(hor, zen, smoothstep(0.0, 0.7, y));
    col = mix(col, gnd, smoothstep(0.0, 0.5, -y));

    vec3 toSun = normalize(-uDirLightDir);
    float s = max(dot(d, toSun), 0.0);
    // Sun disk and tight halo, blurring away as roughness grows.
    float focus = mix(600.0, 5.0, roughness);
    col += uDirLightColor * pow(s, focus) * mix(18.0, 0.55, roughness);
    // Wide atmospheric forward-scatter lobe.
    col += uDirLightColor * pow(s, 3.0) * 0.22 * (1.0 - roughness * 0.6);
    // Warm band hugging the horizon on the sun's side.
    vec2 azD = normalize(d.xz + vec2(1e-5));
    vec2 azS = normalize(toSun.xz + vec2(1e-5));
    col += uDirLightColor * pow(max(dot(azD, azS), 0.0), 5.0) * exp(-abs(y) * 8.0) * 0.4;
    return col;
}

float distributionGGX(vec3 n, vec3 h, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float ndh = max(dot(n, h), 0.0);
    float d = ndh * ndh * (a2 - 1.0) + 1.0;
    return a2 / (3.14159265 * d * d);
}

float geometrySchlickGGX(float ndv, float roughness) {
    float r = roughness + 1.0;
    float k = (r * r) / 8.0;
    return ndv / (ndv * (1.0 - k) + k);
}

float geometrySmith(vec3 n, vec3 v, vec3 l, float roughness) {
    return geometrySchlickGGX(max(dot(n, v), 0.0), roughness)
         * geometrySchlickGGX(max(dot(n, l), 0.0), roughness);
}

vec3 fresnelSchlick(float cosTheta, vec3 f0) {
    return f0 + (1.0 - f0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

vec3 fresnelSchlickRoughness(float cosTheta, vec3 f0, float roughness) {
    vec3 f90 = max(vec3(1.0 - roughness), f0);
    return f0 + (f90 - f0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

void main() {
    vec3 n = normalize(vNormal);
    vec3 v = normalize(uEyePos - vWorldPos);
    vec3 l = normalize(-uDirLightDir);
    vec3 h = normalize(l + v);

    float roughness = clamp(uRoughness, 0.05, 1.0);
    float metallic = clamp(uMetallic, 0.0, 1.0);
    vec3 f0 = mix(vec3(0.04), uColor, metallic);

    // --- Direct key light (GGX / Smith / Schlick) ---
    float ndl = max(dot(n, l), 0.0);
    float ndv = max(dot(n, v), 0.0);
    float ndf = distributionGGX(n, h, roughness);
    float geo = geometrySmith(n, v, l, roughness);
    vec3 f = fresnelSchlick(max(dot(h, v), 0.0), f0);
    vec3 spec = (ndf * geo * f) / (4.0 * ndv * ndl + 0.001);
    vec3 kD = (1.0 - f) * (1.0 - metallic);
    vec3 Lo = (kD * uColor / 3.14159265 + spec) * uDirLightColor * ndl;

    // --- Image-based lighting from the analytic sky ---
    vec3 fibl = fresnelSchlickRoughness(ndv, f0, roughness);
    vec3 kD2 = (1.0 - fibl) * (1.0 - metallic);
    vec3 diffuseIBL = skyAmbient(n) * uColor * kD2;
    vec3 specularIBL = skyColor(reflect(-v, n), roughness) * fibl;

    vec3 color = Lo + diffuseIBL + specularIBL + uEmissive;
    fragColor = vec4(color, uAlpha);
}`;

const VERT_UNLIT = `${GLSL_VERSION}
layout(location = 0) in vec3 aPosition;
layout(location = 2) in vec2 aUV;   // location 1 is the normal (unused here)
uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProj;
out vec2 vUV;
void main() {
    vUV = aUV;
    gl_Position = uProj * uView * (uModel * vec4(aPosition, 1.0));
}`;

const FRAG_UNLIT = `${GLSL_VERSION}
precision highp float;
in vec2 vUV;
uniform vec3 uColor;
uniform float uAlpha;
uniform float uBrightness;
uniform bool uUseMap;
uniform sampler2D uMap;
out vec4 fragColor;
void main() {
    vec4 color = vec4(uColor * uBrightness, uAlpha);
    if (uUseMap) {
        color *= texture(uMap, vUV);
    }
    fragColor = color;
}`;

const VERT_POINTS = `${GLSL_VERSION}
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec2 aStyle;   // size (world units), alpha
layout(location = 2) in vec3 aColor;
uniform mat4 uView;
uniform mat4 uProj;
uniform float uPointScale;             // viewportHeight / (2 * tan(fov/2))
out vec3 vColor;
out float vAlpha;
void main() {
    vec4 viewPos = uView * vec4(aPosition, 1.0);
    vColor = aColor;
    vAlpha = aStyle.y;
    float dist = max(-viewPos.z, 1.0);
    gl_PointSize = clamp(aStyle.x * uPointScale / dist, 1.0, 64.0);
    gl_Position = uProj * viewPos;
}`;

const FRAG_POINTS = `${GLSL_VERSION}
precision highp float;
in vec3 vColor;
in float vAlpha;
out vec4 fragColor;
void main() {
    vec2 p = gl_PointCoord - vec2(0.5);
    float d = length(p);
    if (d > 0.5) discard;
    float falloff = smoothstep(0.5, 0.15, d);
    fragColor = vec4(vColor, vAlpha * falloff);
}`;

class VanillaRenderer3D {
    constructor(canvas, deviceCapabilities) {
        this.canvas = canvas;
        this.deviceCapabilities = deviceCapabilities;
        this.gl = null;

        this.tokens3D = new Map();
        this.specialCellObjects = [];
        this.validMoveMeshes = [];
        this.validAttackMeshes = [];
        this.threatMeshes = [];
        this.objectiveMeshes = [];
        this.hoverMesh = null;
        this.mysteryRings = [];
        this.mysteryAnimations = new Map();
        this.generatorMeshes = new Map();
        this.generatorLineMeshes = [];
        this.explosionParticles = [];   // JS-side particle sim
        this.confettiParticles = [];
        this.floatingTexts = [];
        this.crystalFrames = [];
        this.crystalMesh = null;

        this.localPlayerId = null;
        this.animationTime = 0;
        this.trauma = 0;
        this.lastGameState = null;
        this.lastProcessedMysteryEvent = null;
        this.lastProcessedCrystalEffect = null;
        this.hoveredCell = null;
        this._cameraUpdateCallback = null;
        this._rafId = null;
        this._lastFrameTime = null;
        this._resizeHandler = null;

        this.audioManager = new AudioManager();
        this.cleanupCallbacks = [];

        // Crystal effect animator — WebGL2 port of the Babylon animator
        // (webgl2_crystal_effects.js). Same interface; visuals spawn through
        // this renderer's particle system and transparent draw list.
        this.crystalEffectAnimator = new WebGL2CrystalEffectAnimator(this);

        // Scene facade for InputHandler compatibility: picking against the
        // ground plane. Decoration was never pickable in Babylon either.
        this.scene = {
            pick: (x, y) => this._pickGridCellRaw(x, y),
            render: () => {},
        };
        this.engine = {};

        this.cameraController = null;
        this.meshCache = new Map();
        this.textures = [];

        // Post-processing: half-res bloom + composite (vignette, grain).
        // ?bloom=0 disables it entirely and renders straight to the canvas.
        this.bloomEnabled = new URLSearchParams(window.location.search).get('bloom') !== '0';
        this.raysEnabled = new URLSearchParams(window.location.search).get('rays') !== '0';
        this.chromaEnabled = new URLSearchParams(window.location.search).get('chroma') !== '0';
        this.sharpenEnabled = new URLSearchParams(window.location.search).get('sharpen') !== '0';
        this.bloomPass = null;
    }

    // --- Setup ---------------------------------------------------------------

    initScene() {
        const renderConfig = this.deviceCapabilities ?
            this.deviceCapabilities.getRenderingConfig() :
            { hardwareScaling: 1.0, antialiasing: true };
        this.renderScale = Math.max(0.5, 1 / (renderConfig.hardwareScaling || 1.0));
        this.particleMaxCount = renderConfig.particleMaxCount || 1000;

        const gl = getWebGL2Context(this.canvas, { antialias: renderConfig.antialiasing !== false });
        if (!gl) {
            throw new Error('WebGL2 is not available in this browser');
        }
        this.gl = gl;

        gl.enable(gl.DEPTH_TEST);
        gl.disable(gl.CULL_FACE); // tiny scene; winding is not load-bearing
        gl.clearColor(0, 0, 0, 1);

        this._createPrograms();
        this._createMeshes();
        this._createBoard();
        this._createSkybox();
        this._createParticles();

        if (this.bloomEnabled) {
            try {
                this.bloomPass = new BloomPass(gl);
                this.bloomPass.chroma = this.chromaEnabled ? 0.006 : 0;
                this.bloomPass.sharpen = this.sharpenEnabled ? 0.25 : 0;
            } catch (error) {
                console.warn('[webgl2] bloom pass failed to initialize; continuing without post-processing.', error);
                this.bloomPass = null;
            }
        }
        return this.scene;
    }

    _createPrograms() {
        const gl = this.gl;
        this.programs = {
            lit: createProgram(gl, VERT_LIT, FRAG_LIT, [
                'uModel', 'uView', 'uProj', 'uColor', 'uEmissive', 'uAlpha',
                'uDirLightDir', 'uDirLightColor', 'uMetallic', 'uRoughness', 'uEyePos',
            ]),
            unlit: createProgram(gl, VERT_UNLIT, FRAG_UNLIT, [
                'uModel', 'uView', 'uProj', 'uColor', 'uAlpha', 'uBrightness', 'uUseMap', 'uMap',
            ]),
            points: createProgram(gl, VERT_POINTS, FRAG_POINTS, [
                'uView', 'uProj', 'uPointScale',
            ]),
        };
        // Static light parameters (warm key light + cool ambient).
        this.lightDir = new Vec3(-0.5, -1.4, -0.35).normalize();
        this.dirLightColor = new Vec3(0.9, 0.9, 0.85);

        gl.useProgram(this.programs.unlit.program);
        gl.uniform1i(this.programs.unlit.uniforms.uMap, 0);
        gl.useProgram(null);
    }

    _mesh(key, builder) {
        if (!this.meshCache.has(key)) {
            this.meshCache.set(key, createMesh(this.gl, builder()));
        }
        return this.meshCache.get(key);
    }

    _lineMesh(key, positions) {
        if (!this.meshCache.has(key)) {
            this.meshCache.set(key, createLineMesh(this.gl, positions));
        }
        return this.meshCache.get(key);
    }

    _createMeshes() {
        const CS = CELL_SIZE;
        this._mesh('ground', () => buildGround(BOARD_WIDTH * CS, BOARD_HEIGHT * CS));
        this._mesh('hexToken', () => buildCylinder(CS * 0.35, TOKEN_HEIGHT, 6, true));
        this._mesh('pillar', () => buildCylinder(12, GENERATOR_HEIGHT, 24, false));
        this._mesh('box', () => buildBox(1, 1, 1));
        this._mesh('beam', () => buildCylinder(0.5, 1, 8, false));
        this._mesh('mysteryTorus', () => buildTorus(CS * 0.35, 1.5, 24, 10));
        this._mesh('quad', () => buildQuad(1, 1));
        this._mesh('pipQuad', () => buildQuad(1, 1));
        this._mesh('icoHub', () => buildIcoSphere(40, 2));
        this._mesh('icoCore', () => buildIcoSphere(25, 1));
        this._mesh('threatCircle', () => buildCircleLine(CS * 0.4, 40));
        this._mesh('squareLine', () => buildSquareLine(CS * 0.8));
        this._mesh('hoverLine', () => buildSquareLine(CS * 0.7));

        this.gridTexture = createGridTexture(this.gl, BOARD_WIDTH);
        this.textures.push(this.gridTexture);
    }

    _createBoard() {
        const CS = CELL_SIZE;
        // Vertical wall lines at every grid intersection.
        const vertical = [];
        for (let x = 0; x <= BOARD_WIDTH; x++) {
            for (let y = 0; y <= BOARD_HEIGHT; y++) {
                vertical.push(x * CS, 0, y * CS, x * CS, WALL_HEIGHT, y * CS);
            }
        }
        this._lineMesh('gridVertical', new Float32Array(vertical));

        // Cage frame along the top of the walls.
        const cage = [];
        for (let y = 0; y <= BOARD_HEIGHT; y++) {
            for (let x = 0; x < BOARD_WIDTH; x++) {
                cage.push(x * CS, WALL_HEIGHT, y * CS, (x + 1) * CS, WALL_HEIGHT, y * CS);
            }
        }
        for (let x = 0; x <= BOARD_WIDTH; x++) {
            for (let y = 0; y < BOARD_HEIGHT; y++) {
                cage.push(x * CS, WALL_HEIGHT, y * CS, x * CS, WALL_HEIGHT, (y + 1) * CS);
            }
        }
        this._lineMesh('gridCage', new Float32Array(cage));
    }

    _createSkybox() {
        // The star field is drawn by _drawStars() from a static point batch —
        // no sky sphere. Pure black clear color behind it.
    }

    _createParticles() {
        this.particleCapacity = Math.min(this.particleMaxCount, 1024);
        this.particles = [];
        this.pointMesh = createPointMesh(this.gl, this.particleCapacity);
        this._pointPositions = new Float32Array(this.particleCapacity * 3);
        this._pointStyles = new Float32Array(this.particleCapacity * 2);
        this._pointColors = new Float32Array(this.particleCapacity * 3);
        this._createStarDome();
    }

    /**
     * Static star field: ~250 point sprites scattered over a large sphere
     * shell around the board. No texture, no UV seams, nothing to alias —
     * just dots, drawn with the same unlit point shader as the particles.
     */
    _createStarDome() {
        const gl = this.gl;
        const STAR_COUNT = 250;
        const shellRadius = 1400;
        const cx = (BOARD_WIDTH * CELL_SIZE) / 2;
        const cz = (BOARD_HEIGHT * CELL_SIZE) / 2;
        const positions = new Float32Array(STAR_COUNT * 3);
        const styles = new Float32Array(STAR_COUNT * 2);
        const colors = new Float32Array(STAR_COUNT * 3);

        for (let i = 0; i < STAR_COUNT; i++) {
            // Random direction on a sphere, biased upward so the field
            // reads as a sky rather than a full dome.
            let x = Math.random() * 2 - 1;
            let y = Math.random() * 2 - 1;
            let z = Math.random() * 2 - 1;
            const len = Math.hypot(x, y, z) || 1;
            x /= len; y /= len; z /= len;
            if (y < -0.15) {
                y = -y; // keep stars above the "horizon"
            }
            positions[i * 3] = cx + x * shellRadius;
            positions[i * 3 + 1] = y * shellRadius * 0.6 + 40;
            positions[i * 3 + 2] = cz + z * shellRadius;

            const size = 1.0 + Math.random() * 1.6;
            styles[i * 2] = size;
            styles[i * 2 + 1] = 0.35 + Math.random() * 0.65;

            // Mostly white, occasionally blue-tinted.
            const tint = Math.random();
            if (tint < 0.75) {
                colors[i * 3] = 1; colors[i * 3 + 1] = 1; colors[i * 3 + 2] = 1;
            } else if (tint < 0.9) {
                colors[i * 3] = 0.75; colors[i * 3 + 1] = 0.85; colors[i * 3 + 2] = 1.0;
            } else {
                colors[i * 3] = 1.0; colors[i * 3 + 1] = 0.9; colors[i * 3 + 2] = 0.75;
            }
        }

        this.starMesh = createPointMesh(gl, STAR_COUNT);
        gl.bindVertexArray(this.starMesh.vao);
        gl.bindBuffer(gl.ARRAY_BUFFER, this.starMesh.positionBuffer);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, positions);
        gl.bindBuffer(gl.ARRAY_BUFFER, this.starMesh.styleBuffer);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, styles);
        gl.bindBuffer(gl.ARRAY_BUFFER, this.starMesh.colorBuffer);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, colors);
        gl.bindVertexArray(null);
        this.starCount = STAR_COUNT;
    }

    // --- Picking ---------------------------------------------------------------

    _pickGridCellRaw(screenX, screenY) {
        const gl = this.gl;
        if (!gl || !this.cameraController) return null;
        const rect = this.canvas.getBoundingClientRect();
        const width = Math.max(rect.width, 1);
        const height = Math.max(rect.height, 1);

        const camera = this.cameraController.camera;
        if (!camera) return null;
        const proj = this._projectionMatrix(camera);
        const view = this._viewMatrix(camera);
        const invVP = mat4Invert(mat4Multiply(proj, view));
        if (!invVP) return null;

        const ndcX = (screenX / width) * 2 - 1;
        const ndcY = -((screenY / height) * 2 - 1);
        const near = this._unproject(invVP, ndcX, ndcY, -1);
        const far = this._unproject(invVP, ndcX, ndcY, 1);
        if (!near || !far) return null;

        const dir = far.subtract(near).normalize();
        if (Math.abs(dir.y) < 1e-8) return null;
        const t = -near.y / dir.y;
        if (t <= 0) return null;

        const px = near.x + dir.x * t;
        const pz = near.z + dir.z * t;
        if (px < 0 || pz < 0 || px >= BOARD_WIDTH * CELL_SIZE || pz >= BOARD_HEIGHT * CELL_SIZE) {
            return null;
        }
        return {
            hit: true,
            pickedPoint: { x: px, y: 0, z: pz },
        };
    }

    _unproject(invVP, x, y, z) {
        const clip = [x, y, z, 1];
        const out = [0, 0, 0, 0];
        for (let row = 0; row < 4; row++) {
            out[row] =
                invVP[row] * clip[0] +
                invVP[4 + row] * clip[1] +
                invVP[8 + row] * clip[2] +
                invVP[12 + row] * clip[3];
        }
        if (Math.abs(out[3]) < 1e-10) return null;
        return new Vec3(out[0] / out[3], out[1] / out[3], out[2] / out[3]);
    }

    // --- Frame matrices ---------------------------------------------------------

    _projectionMatrix(camera) {
        const rect = this.canvas.getBoundingClientRect();
        const aspect = Math.max(rect.width, 1) / Math.max(rect.height, 1);
        return mat4Perspective(camera.fov, aspect, camera.minZ || 1, camera.maxZ || 10000);
    }

    _viewMatrix(camera) {
        const shake = this.trauma * this.trauma;
        const t = this.animationTime;
        if (shake <= 0.0001) {
            return camera.getViewMatrix();
        }
        const eye = camera.position.clone();
        const amp = shake * 10;
        eye.x += Math.sin(t * 37.7) * amp + Math.cos(t * 17.3) * amp * 0.4;
        eye.y += Math.cos(t * 23.1) * amp * 0.6;
        eye.z += Math.sin(t * 29.4) * amp;
        return mat4LookAt(eye, camera.target, new Vec3(0, 1, 0));
    }

    _aspect() {
        const rect = this.canvas.getBoundingClientRect();
        return Math.max(rect.width, 1) / Math.max(rect.height, 1);
    }

    // --- Draw helpers ------------------------------------------------------------

    _computeModel(obj) {
        return mat4ComposeTRS(
            obj.pos || { x: 0, y: 0, z: 0 },
            obj.rot || { x: 0, y: 0, z: 0 },
            obj.scale || { x: 1, y: 1, z: 1 },
        );
    }

    _drawLit(gl, obj, view, proj, eyePos) {
        const program = this.programs.lit;
        gl.useProgram(program.program);
        gl.uniformMatrix4fv(program.uniforms.uModel, false, this._computeModel(obj));
        gl.uniformMatrix4fv(program.uniforms.uView, false, view);
        gl.uniformMatrix4fv(program.uniforms.uProj, false, proj);
        gl.uniform3fv(program.uniforms.uColor, obj.color || WHITE);
        gl.uniform3fv(program.uniforms.uEmissive, obj.emissive || [0, 0, 0]);
        gl.uniform1f(program.uniforms.uAlpha, obj.alpha !== undefined ? obj.alpha : 1);
        gl.uniform3fv(program.uniforms.uDirLightDir,
            [this.lightDir.x, this.lightDir.y, this.lightDir.z]);
        gl.uniform3fv(program.uniforms.uDirLightColor,
            [this.dirLightColor.x, this.dirLightColor.y, this.dirLightColor.z]);
        gl.uniform1f(program.uniforms.uMetallic, obj.metallic !== undefined ? obj.metallic : 0.0);
        gl.uniform1f(program.uniforms.uRoughness, obj.roughness !== undefined ? obj.roughness : 0.5);
        gl.uniform3fv(program.uniforms.uEyePos, [eyePos.x, eyePos.y, eyePos.z]);
        obj.mesh.draw();
    }

    _drawUnlit(gl, obj, view, proj) {
        const program = this.programs.unlit;
        gl.useProgram(program.program);
        gl.uniformMatrix4fv(program.uniforms.uModel, false, this._computeModel(obj));
        gl.uniformMatrix4fv(program.uniforms.uView, false, view);
        gl.uniformMatrix4fv(program.uniforms.uProj, false, proj);
        gl.uniform3fv(program.uniforms.uColor, obj.color || WHITE);
        gl.uniform1f(program.uniforms.uAlpha, obj.alpha !== undefined ? obj.alpha : 1);
        gl.uniform1f(program.uniforms.uBrightness, obj.brightness !== undefined ? obj.brightness : 1);
        gl.uniform1i(program.uniforms.uUseMap, obj.useMap ? 1 : 0);
        if (obj.useMap && obj.texture) {
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, obj.texture);
        }
        obj.mesh.draw();
    }

    _drawLine(gl, obj, view, proj) {
        const program = this.programs.unlit;
        gl.useProgram(program.program);
        gl.uniformMatrix4fv(program.uniforms.uModel, false, this._computeModel(obj));
        gl.uniformMatrix4fv(program.uniforms.uView, false, view);
        gl.uniformMatrix4fv(program.uniforms.uProj, false, proj);
        gl.uniform3fv(program.uniforms.uColor, obj.color || WHITE);
        gl.uniform1f(program.uniforms.uAlpha, obj.alpha !== undefined ? obj.alpha : 1);
        gl.uniform1f(program.uniforms.uBrightness, 1);
        gl.uniform1i(program.uniforms.uUseMap, 0);
        obj.mesh.draw(obj.lineLoop ? gl.LINE_LOOP : gl.LINES);
    }

    _drawBillboard(gl, obj, view, proj, eyePos) {
        // Face the camera: +Z of the quad points at the eye. Right/up span
        // the label's own width/height.
        const viewDir = new Vec3(
            eyePos.x - obj.pos.x,
            eyePos.y - obj.pos.y,
            eyePos.z - obj.pos.z,
        ).normalize();
        const right = new Vec3(0, 1, 0).cross(viewDir).normalize();
        const up = viewDir.cross(right);

        // buildQuad(1,1) spans ±0.5, so scaling by width/height (not width/2)
        // draws the billboard at its nominal size.
        const sx = obj.width || 1;
        const sy = obj.height || 1;

        const model = new Float32Array([
            right.x * sx, right.y * sx, right.z * sx, 0,
            up.x * sy, up.y * sy, up.z * sy, 0,
            viewDir.x, viewDir.y, viewDir.z, 0,
            obj.pos.x, obj.pos.y, obj.pos.z, 1,
        ]);

        const program = this.programs.unlit;
        gl.useProgram(program.program);
        gl.uniformMatrix4fv(program.uniforms.uModel, false, model);
        gl.uniformMatrix4fv(program.uniforms.uView, false, view);
        gl.uniformMatrix4fv(program.uniforms.uProj, false, proj);
        gl.uniform3fv(program.uniforms.uColor, obj.color || WHITE);
        gl.uniform1f(program.uniforms.uAlpha, obj.alpha !== undefined ? obj.alpha : 1);
        gl.uniform1f(program.uniforms.uBrightness, 1);
        gl.uniform1i(program.uniforms.uUseMap, obj.useMap ? 1 : 0);
        if (obj.useMap && obj.texture) {
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, obj.texture);
        }
        this._mesh('quad', () => buildQuad(1, 1)).draw();
    }

    // --- Public interface (Babylon-compatible) -----------------------------------

    initPipeline() {
        // No-op: no post-processing pipeline in the WebGL2 path.
    }

    startRenderLoop() {
        const frame = () => {
            const now = performance.now();
            const dt = this._lastFrameTime === null ? 1 / 60 : Math.min((now - this._lastFrameTime) / 1000, 0.1);
            this._lastFrameTime = now;
            this.animationTime += dt;

            this.updateAnimations();
            if (this._cameraUpdateCallback) {
                this._cameraUpdateCallback();
            }
            this.trauma = Math.max(0, this.trauma - dt * 2.0);
            this._renderFrame();

            this._rafId = requestAnimationFrame(frame);
        };
        this._rafId = requestAnimationFrame(frame);
    }

    setCameraUpdateCallback(callback) {
        this._cameraUpdateCallback = callback;
    }

    loadSounds() {
        this.audioManager.initAudioContext();
        this.audioManager.loadBackgroundMusic();
        this.audioManager.loadGeneratorHums();
        this.audioManager.loadSoundEffects();
    }

    playSound(soundName) {
        if (this.audioManager.soundEffects.has(soundName)) {
            this.audioManager.playSound(soundName);
        } else {
            this.audioManager.playSynthesizedSound(soundName);
        }
    }

    toggleMusic() {
        this.audioManager.toggleMusic();
    }

    updateGeneratorHums(generators) {
        this.audioManager.updateGeneratorHums(generators);
    }

    // --- Special cells (crystal, generators, mystery rings) ----------------------

    getPlayerColors(gameState) {
        const colors = {};
        let index = 0;
        for (const [playerId, player] of Object.entries(gameState.players || {})) {
            const colorIndex = player.color_index ?? player.color ?? index;
            colors[playerId] = PLAYER_COLORS[colorIndex % PLAYER_COLORS.length];
            index++;
        }
        return colors;
    }

    createSpecialCells(gameState) {
        // Drop every decoration object (they hold no GPU buffers of their
        // own — meshes are shared via the mesh cache).
        this.specialCellObjects = [];
        this.generatorMeshes.clear();
        this.generatorLineMeshes = [];
        this.crystalFrames = [];
        this.crystalMesh = null;
        this.crystalWorldPos = null;
        this.mysteryRings = [];

        if (!gameState.crystal) return;

        const centerX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;
        this.crystalWorldPos = { x: centerX, y: CRYSTAL_HUB_Y, z: centerZ };

        const hub = {
            kind: 'unlit',
            mesh: this._mesh('icoHub', () => buildIcoSphere(40, 2)),
            pos: { x: centerX, y: CRYSTAL_HUB_Y, z: centerZ },
            rot: { x: 0, y: 0, z: 0 },
            scale: { x: 1, y: 2.2, z: 1 },
            color: CRYSTAL_COLOR,
            brightness: 1.6,
            crystalHub: true,
        };
        this.specialCellObjects.push(hub);
        this.crystalMesh = { mesh: hub, position: gameState.crystal.position, tokenCounts: {} };

        this.specialCellObjects.push({
            kind: 'unlit',
            mesh: this._mesh('icoCore', () => buildIcoSphere(25, 1)),
            pos: { x: centerX, y: CRYSTAL_HUB_Y, z: centerZ },
            rot: { x: 0, y: 0, z: 0 },
            scale: { x: 1, y: 2.2, z: 1 },
            color: [0.5, 0.95, 1.0],
            brightness: 2.4,
        });

        const gold = [1.0, 0.766, 0.336];
        const frameMesh = this._lineMesh('frameLines', buildIcoSphere(60, 1).edges);
        for (const [idx, frameScale] of [[0, { x: 1.0, y: 1.0, z: 1.0 }], [1, { x: 0.6, y: 1.3, z: 0.6 }], [2, { x: 1.2, y: 0.8, z: 1.2 }]]) {
            const frame = {
                kind: 'line',
                mesh: frameMesh,
                pos: { x: centerX, y: CRYSTAL_HUB_Y, z: centerZ },
                rot: { x: 0, y: idx * 1.1, z: 0 },
                scale: { x: frameScale.x, y: frameScale.y * 2.2, z: frameScale.z },
                color: gold,
                alpha: 0.85,
                lineSpinDir: idx % 2 === 0 ? 1 : -1,
            };
            this.specialCellObjects.push(frame);
            this.crystalFrames.push(frame);
        }

        if (gameState.generators) {
            gameState.generators.forEach((gen, index) => {
                const worldX = gen.position[0] * CELL_SIZE + CELL_SIZE / 2;
                const worldZ = gen.position[1] * CELL_SIZE + CELL_SIZE / 2;

                const pillar = {
                    kind: 'lit',
                    mesh: this._mesh('pillar', () => buildCylinder(12, GENERATOR_HEIGHT, 24, false)),
                    pos: { x: worldX, y: GENERATOR_CENTER_Y, z: worldZ },
                    rot: { x: 0, y: 0, z: 0 },
                    scale: { x: 1, y: 1, z: 1 },
                    color: [0.9, 0.92, 0.98],
                    emissive: ORANGE_GLOW.slice(),
                    alpha: 0.85,
                    metallic: 0.85,
                    roughness: 0.3,
                    genKey: `${gen.position[0]},${gen.position[1]}`,
                };
                this.specialCellObjects.push(pillar);
                this.generatorMeshes.set(pillar.genKey, {
                    object: pillar,
                    position: gen.position,
                    isDisabled: gen.is_disabled,
                    lastOwner: null,
                });
            });
        }

        this.createGeneratorLines(gameState);

        if (gameState.board && gameState.board.grid) {
            for (let y = 0; y < gameState.board.grid.length; y++) {
                for (let x = 0; x < gameState.board.grid[y].length; x++) {
                    if (gameState.board.grid[y][x].cell_type === 3) {
                        this.createMysteryRing(x, y);
                    }
                }
            }
        }
    }

    createMysteryRing(x, y) {
        const centerX = x * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = y * CELL_SIZE + CELL_SIZE / 2;

        const ring = {
            kind: 'unlit',
            mesh: this._mesh('mysteryTorus', () => buildTorus(CELL_SIZE * 0.35, 1.5, 24, 10)),
            pos: { x: centerX, y: WALL_HEIGHT * 0.5, z: centerZ },
            rot: { x: Math.PI / 2, y: 0, z: 0 },
            scale: { x: 1, y: 1, z: 1 },
            color: CYAN_GLOW,
            alpha: 0.6,
            brightness: 1.8,
            mysteryCell: { x, y },
        };
        this.specialCellObjects.push(ring);
        this.mysteryRings.push(ring);
    }

    createGeneratorLines(gameState) {
        if (!gameState.generators || !gameState.crystal || !this.crystalMesh) return;

        const centerX = gameState.crystal.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = gameState.crystal.position[1] * CELL_SIZE + CELL_SIZE / 2;
        const hubPos = new Vec3(centerX, CRYSTAL_BEAM_HUB_Y, centerZ);

        gameState.generators.forEach((gen, index) => {
            if (gen.is_disabled) return;

            const genData = this.generatorMeshes.get(`${gen.position[0]},${gen.position[1]}`);
            if (!genData) return;

            const pillarPos = new Vec3(genData.object.pos.x, genData.object.pos.y, genData.object.pos.z);
            const dir = hubPos.subtract(pillarPos);
            const fullLen = dir.length();
            const axis = dir.normalize();

            // Basis with Y aligned to the beam axis.
            const helper = Math.abs(axis.y) > 0.9 ? new Vec3(1, 0, 0) : new Vec3(0, 1, 0);
            const xAxis = helper.cross(axis).normalize();
            const zAxis = axis.cross(xAxis).normalize();

            const beamColors = [
                [0.1, 0.4, 1.0],
                [0.1, 0.8, 0.2],
                [0.8, 0.1, 0.1],
            ];
            const mid = pillarPos.add(hubPos).scale(0.5);
            const beams = [];

            beamColors.forEach((color, mIdx) => {
                const offset = (mIdx - 1) * 0.8;
                // Beam center: midpoint shifted sideways per strand.
                const strandMid = new Vec3(mid.x + offset, mid.y, mid.z + offset);

                const beam = {
                    kind: 'beam',
                    mesh: this._mesh('beam', () => buildCylinder(0.5, 1, 8, false)),
                    pos: { x: strandMid.x, y: strandMid.y, z: strandMid.z },
                    basis: {
                        x: xAxis,
                        y: axis.scale(fullLen), // Y axis carries the length
                        z: zAxis,
                    },
                    color,
                    alpha: 0.8,
                    brightness: 2.0,
                    phase: index * 2.1 + mIdx * 0.7,
                    additive: true,
                };
                this.specialCellObjects.push(beam);
                beams.push(beam);
            });

            this.generatorLineMeshes.push({ genPosition: gen.position, beams });
        });
    }

    updateSpecialCellColors(gameState) {
        if (!gameState.tokens || !gameState.generators) return;

        const playerColors = this.getPlayerColors(gameState);

        gameState.generators.forEach((gen) => {
            const genKey = `${gen.position[0]},${gen.position[1]}`;
            const genData = this.generatorMeshes.get(genKey);
            if (!genData) return;

            const tokensHere = [];
            for (const token of Object.values(gameState.tokens)) {
                if (!token.is_deployed || !token.is_alive) continue;
                // A token hidden by fog of war has no position.
                if (!token.position) continue;
                if (token.position[0] === gen.position[0] && token.position[1] === gen.position[1]) {
                    tokensHere.push(token);
                }
            }

            let dominantPlayer = null;
            let maxCount = 0;
            const playerCounts = {};
            for (const token of tokensHere) {
                for (const [playerId, player] of Object.entries(gameState.players || {})) {
                    if (player.token_ids && player.token_ids.includes(token.id)) {
                        playerCounts[playerId] = (playerCounts[playerId] || 0) + 1;
                        if (playerCounts[playerId] > maxCount) {
                            maxCount = playerCounts[playerId];
                            dominantPlayer = playerId;
                        }
                        break;
                    }
                }
            }

            if (gen.is_disabled && !genData.isDisabled) {
                this.triggerExplosion(gen.position, ORANGE_GLOW);
                this.playSound('capture');
            }

            const pillar = genData.object;
            if (dominantPlayer && playerCounts[dominantPlayer] >= 2 && !gen.is_disabled) {
                const color = playerColors[dominantPlayer] || ORANGE_GLOW;
                pillar.emissive = color.slice();
                pillar.alpha = 1.0;
                genData.lastOwner = dominantPlayer;
            } else if (gen.is_disabled) {
                pillar.emissive = [0.3, 0.3, 0.3];
                pillar.alpha = 0.3;
                genData.lastOwner = null;
            } else {
                pillar.emissive = ORANGE_GLOW.slice();
                pillar.alpha = 0.85;
                genData.lastOwner = null;
            }

            genData.isDisabled = gen.is_disabled;
        });

        if (this.crystalMesh && gameState.crystal) {
            const tokensAtCrystal = [];
            for (const token of Object.values(gameState.tokens)) {
                if (!token.is_deployed || !token.is_alive) continue;
                // A token hidden by fog of war has no position.
                if (!token.position) continue;
                if (token.position[0] === gameState.crystal.position[0] &&
                    token.position[1] === gameState.crystal.position[1]) {
                    tokensAtCrystal.push(token);
                }
            }

            const crystalCounts = {};
            let dominantPlayer = null;
            let maxCount = 0;
            for (const token of tokensAtCrystal) {
                for (const [playerId, player] of Object.entries(gameState.players || {})) {
                    if (player.token_ids && player.token_ids.includes(token.id)) {
                        crystalCounts[playerId] = (crystalCounts[playerId] || 0) + 1;
                        if (crystalCounts[playerId] > maxCount) {
                            maxCount = crystalCounts[playerId];
                            dominantPlayer = playerId;
                        }
                        break;
                    }
                }
            }

            if (dominantPlayer && crystalCounts[dominantPlayer] >= 2) {
                const color = playerColors[dominantPlayer] || CRYSTAL_COLOR;
                this.crystalMesh.mesh.color = color;
                this.crystalMesh.mesh.brightness = 2.2;
            } else {
                this.crystalMesh.mesh.color = CRYSTAL_COLOR.slice();
                this.crystalMesh.mesh.brightness = 1.6;
            }

            this.crystalMesh.tokenCounts = crystalCounts;
        }
    }

    // --- Tokens -----------------------------------------------------------------

    updateTokens(gameState) {
        const allTokens = [];
        for (const player of Object.values(gameState.players)) {
            for (const tokenId of player.token_ids) {
                const token = gameState.tokens[tokenId];
                if (token && token.is_alive && token.is_deployed) {
                    allTokens.push(token);
                }
            }
        }

        const visibleTokens = this.filterVisibleTokens(gameState, allTokens);
        const visibleTokenIds = new Set(visibleTokens.map((t) => t.id));

        for (const [tokenId, record] of this.tokens3D) {
            if (!visibleTokenIds.has(tokenId)) {
                this.tokens3D.delete(tokenId);
            }
        }

        for (const token of visibleTokens) {
            const player = Object.values(gameState.players).find((p) =>
                p.token_ids.includes(token.id)
            );
            const colorIndex = player ? (player.color_index ?? player.color ?? 0) : 0;
            const playerColor = PLAYER_COLORS[colorIndex % PLAYER_COLORS.length];

            if (this.tokens3D.has(token.id)) {
                this.updateTokenPosition(token.id, token);
            } else {
                this.createToken3D(token, playerColor);
            }
        }

        this.updatePhantomTokens(gameState);
    }

    filterVisibleTokens(gameState, allTokens) {
        // Fog of war: the server masks the tokens a player cannot see.
        const seen = allTokens.filter(
            (token) => token.is_visible !== false && token.position,
        );

        if (!gameState.crystal?.active_effect) {
            return seen;
        }

        const effect = gameState.crystal.active_effect;
        const localPlayerId = this.localPlayerId;

        if (effect.type === CRYSTAL_EFFECT.FOG_OF_WAR) {
            return seen.filter((token) => token.player_id === localPlayerId);
        }

        return seen;
    }

    getPhantomTokens(gameState) {
        if (!gameState.crystal?.active_effect || gameState.crystal.active_effect.type !== CRYSTAL_EFFECT.PHANTOM_ENEMIES) {
            return [];
        }

        const phantoms = [];
        const affectedPlayerId = gameState.crystal.active_effect.affected_player_id;
        const localPlayerId = this.localPlayerId;

        if (affectedPlayerId === localPlayerId) {
            const player = gameState.players[affectedPlayerId];
            if (!player) return [];

            for (const tokenId of player.token_ids) {
                const token = gameState.tokens[tokenId];
                if (token && token.is_alive && token.is_deployed) {
                    phantoms.push({
                        phantom_id: `phantom_${tokenId}`,
                        apparent_player_id: affectedPlayerId,
                        apparent_health: token.health,
                        position: token.position,
                    });
                }
            }
        }

        return phantoms;
    }

    updatePhantomTokens(gameState) {
        const phantoms = this.getPhantomTokens(gameState);
        const phantomIds = new Set(phantoms.map((p) => p.phantom_id));

        if (!this.phantomTokens3D) this.phantomTokens3D = new Map();

        for (const [phantomId, record] of this.phantomTokens3D) {
            if (!phantomIds.has(phantomId)) {
                this.phantomTokens3D.delete(phantomId);
            }
        }

        for (const phantom of phantoms) {
            if (this.phantomTokens3D.has(phantom.phantom_id)) {
                const record = this.phantomTokens3D.get(phantom.phantom_id);
                record.targetX = phantom.position[0] * CELL_SIZE + CELL_SIZE / 2;
                record.targetZ = phantom.position[1] * CELL_SIZE + CELL_SIZE / 2;
            } else {
                const player = gameState.players[phantom.apparent_player_id];
                const colorIndex = player ? (player.color_index ?? player.color ?? 0) : 0;
                const playerColor = PLAYER_COLORS[colorIndex % PLAYER_COLORS.length];
                this.createPhantomToken3D(phantom, playerColor);
            }
        }
    }

    createToken3D(token, playerColor) {
        const worldX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;

        const record = {
            id: token.id,
            kind: 'lit',
            mesh: this._mesh('hexToken', () => buildCylinder(CELL_SIZE * 0.35, TOKEN_HEIGHT, 6, true)),
            pos: { x: worldX, y: TOKEN_CENTER_Y, z: worldZ },
            rot: { x: 0, y: 0, z: 0 },
            scale: { x: 1, y: 1, z: 1 },
            color: [0.0, 0.0, 0.0],
            emissive: playerColor.slice(),
            alpha: 0.95,
            metallic: 0.55,
            roughness: 0.38,
            colorKey: playerColor.join(','),
            token,
            hidden: false,
            baseEmissive: playerColor.slice(),
            label: {
                width: CELL_SIZE * 0.6,
                height: CELL_SIZE * 0.3,
                texture: createHealthLabelTexture(this.gl, `${token.health}hp`, false),
                isPhantom: false,
            },
        };
        record.targetX = worldX;
        record.targetZ = worldZ;
        this.tokens3D.set(token.id, record);
        return record;
    }

    createPhantomToken3D(phantom, playerColor) {
        const worldX = phantom.position[0] * CELL_SIZE + CELL_SIZE / 2;
        const worldZ = phantom.position[1] * CELL_SIZE + CELL_SIZE / 2;

        const record = {
            id: phantom.phantom_id,
            kind: 'lit',
            mesh: this._mesh('hexToken', () => buildCylinder(CELL_SIZE * 0.35, TOKEN_HEIGHT, 6, true)),
            pos: { x: worldX, y: TOKEN_CENTER_Y, z: worldZ },
            rot: { x: 0, y: 0, z: 0 },
            scale: { x: 1, y: 1, z: 1 },
            color: [0.0, 0.0, 0.0],
            emissive: playerColor.slice(),
            alpha: 0.4,
            metallic: 0.3,
            roughness: 0.5,
            phantom: true,
            flickerPhase: Math.random() * Math.PI * 2,
            label: {
                width: CELL_SIZE * 0.6,
                height: CELL_SIZE * 0.3,
                texture: createHealthLabelTexture(this.gl, `${phantom.apparent_health}hp`, true),
                isPhantom: true,
            },
        };
        record.targetX = worldX;
        record.targetZ = worldZ;
        this.phantomTokens3D.set(phantom.phantom_id, record);
        return record;
    }

    updateTokenPosition(tokenId, token) {
        const record = this.tokens3D.get(tokenId);
        if (!record) return;
        record.targetX = token.position[0] * CELL_SIZE + CELL_SIZE / 2;
        record.targetZ = token.position[1] * CELL_SIZE + CELL_SIZE / 2;
        record.token = token;
        const healthTexture = createHealthLabelTexture(this.gl, `${token.health}hp`, false);
        if (record.label.texture !== healthTexture) {
            record.label.texture = healthTexture;
        }
    }

    /**
     * Hide the controlled token (mesh + health label) so it does not block
     * the first-person view; pass null to show all tokens again.
     */
    updateControlledTokenVisibility(controlledTokenId) {
        this.tokens3D.forEach((record, tokenId) => {
            record.hidden = tokenId === controlledTokenId;
        });
    }

    updateTokenSelectionGlow(selectedTokenId) {
        this.tokens3D.forEach((record, tokenId) => {
            if (selectedTokenId !== null && selectedTokenId !== undefined && tokenId === selectedTokenId) {
                record.emissive = WHITE.slice();
                record.scale = { x: 1.25, y: 1.25, z: 1.25 };
            } else {
                record.emissive = (record.baseEmissive || WHITE).slice();
                record.scale = { x: 1, y: 1, z: 1 };
            }
        });
    }

    getTokenMesh(tokenId) {
        const record = this.tokens3D.get(tokenId);
        if (!record) return null;
        return {
            position: { x: record.pos.x, y: record.pos.y, z: record.pos.z },
        };
    }

    // --- Indicators ---------------------------------------------------------------

    _makeFlatCell(size, color, alpha, y) {
        return {
            kind: 'unlit',
            mesh: this._mesh('pipQuad', () => buildQuad(1, 1)),
            pos: { x: 0, y, z: 0 },
            rot: { x: -Math.PI / 2, y: 0, z: 0 },
            scale: { x: size, y: size, z: 1 },
            color,
            alpha,
            brightness: 1.4,
            additive: false,
        };
    }

    updateHoverIndicator(gridX, gridY) {
        // Drop any existing hover marker (single hover cell at a time).
        this.hoverMesh = null;

        this.hoveredCell = gridX === null || gridY === null ? null : { gridX, gridY };
        // The threat overlay is anchored to the cell under the pointer.
        this.updateThreatIndicators();

        if (gridX === null || gridY === null) return;

        const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;
        this.hoverMesh = {
            kind: 'line',
            mesh: this._lineMesh('hoverLine', buildSquareLine(CELL_SIZE * 0.7).positions),
            pos: { x: centerX, y: 2.0, z: centerZ },
            rot: { x: 0, y: 0, z: 0 },
            scale: { x: 1, y: 1, z: 1 },
            color: WHITE,
            alpha: 0.95,
            lineLoop: true,
            additive: true,
        };
    }

    // Valid-move sets may contain "x,y" strings or [x, y] arrays.
    _toGridCoords(entry) {
        if (Array.isArray(entry)) return entry;
        return String(entry).split(',').map(Number);
    }

    _updateCellIndicators(list, entries, color, alphaFill, alphaLine) {
        // Drop previous markers.
        list.length = 0;
        if (!entries || entries.size === 0) return;

        entries.forEach((entry) => {
            const [gridX, gridY] = this._toGridCoords(entry);
            const centerX = gridX * CELL_SIZE + CELL_SIZE / 2;
            const centerZ = gridY * CELL_SIZE + CELL_SIZE / 2;

            // Additive fill: additive blending makes the marker read as a
            // glow rather than a paint swatch, so a modest alpha works.
            const fill = this._makeFlatCell(CELL_SIZE * 0.8, color, alphaFill, 1.0);
            fill.pos = { x: centerX, y: 1.0, z: centerZ };
            fill.additive = true;
            fill.brightness = 1.8;
            list.push(fill);

            const outline = {
                kind: 'line',
                mesh: this._lineMesh('squareLine', buildSquareLine(CELL_SIZE * 0.8).positions),
                pos: { x: centerX, y: 1.0, z: centerZ },
                rot: { x: 0, y: 0, z: 0 },
                scale: { x: 1, y: 1, z: 1 },
                color,
                alpha: alphaLine,
                lineLoop: true,
                additive: true,
            };
            list.push(outline);
        });
    }

    updateValidMoveIndicators(moves) {
        this._updateCellIndicators(this.validMoveMeshes, moves, GREEN_GLOW, 0.35, 0.8);
    }

    updateValidAttackIndicators(attacks) {
        this._updateCellIndicators(this.validAttackMeshes, attacks, RED_GLOW, 0.35, 0.8);
    }

    updateThreatIndicators() {
        this.threatMeshes = [];

        const state = this.lastGameState;
        if (!state || !state.threat_map) return;
        if (!this.hoveredCell) return;

        const key = `${this.hoveredCell.gridX},${this.hoveredCell.gridY}`;
        const tokenIds = state.threat_map[key];
        if (!tokenIds || tokenIds.length === 0) return;

        // The cell under the pointer is dangerous.
        const square = this._makeFlatCell(CELL_SIZE * 0.8, RED_GLOW, 0.3, 2.5);
        square.additive = true;
        square.brightness = 1.8;
        square.pos = {
            x: this.hoveredCell.gridX * CELL_SIZE + CELL_SIZE / 2,
            y: 2.5,
            z: this.hoveredCell.gridY * CELL_SIZE + CELL_SIZE / 2,
        };
        this.threatMeshes.push(square);
        this.threatMeshes.push({
            kind: 'line',
            mesh: this._lineMesh('squareLine', buildSquareLine(CELL_SIZE * 0.8).positions),
            pos: { x: square.pos.x, y: 2.5, z: square.pos.z },
            rot: { x: 0, y: 0, z: 0 },
            scale: { x: 1, y: 1, z: 1 },
            color: RED_GLOW,
            alpha: 0.95,
            lineLoop: true,
            additive: true,
        });

        // Every enemy token that can hit the hovered cell gets a red ring.
        tokenIds.forEach((tokenId) => {
            const record = this.tokens3D.get(tokenId);
            if (!record) return;
            this.threatMeshes.push({
                kind: 'line',
                mesh: this._lineMesh('threatCircle', buildCircleLine(CELL_SIZE * 0.4, 40).positions),
                pos: { x: record.pos.x, y: 2.0, z: record.pos.z },
                rot: { x: 0, y: 0, z: 0 },
                scale: { x: 1, y: 1, z: 1 },
                color: RED_GLOW,
                alpha: 0.9,
                lineLoop: true,
                additive: true,
            });
        });
    }

    updateObjectiveIndicators(gameState) {
        this.objectiveMeshes = [];

        if (!gameState) return;
        const colors = this.getPlayerColors(gameState);

        (gameState.generators || []).forEach((gen) => {
            this.addObjectiveIndicator(
                `gen${gen.id}`,
                gen.position,
                gen.tokens_present || 0,
                gen.tokens_required || 0,
                gen.turns_held || 0,
                gen.turns_required || 0,
                gen.capturing_player_id ? colors[gen.capturing_player_id] : null,
                gen.is_disabled,
                // The generator's pillar is 24 wide, so pips clear a 12 radius.
                12,
            );
        });

        const crystal = gameState.crystal;
        if (crystal) {
            this.addObjectiveIndicator(
                'crystal',
                crystal.position,
                crystal.tokens_present || 0,
                crystal.tokens_required || 0,
                crystal.turns_held || 0,
                crystal.turns_required || 0,
                crystal.holding_player_id ? colors[crystal.holding_player_id] : null,
                false,
                // The crystal's hub stands over the cell.
                30,
            );
        }
    }

    addObjectiveIndicator(key, position, tokensPresent, tokensRequired, turnsHeld, turnsRequired, color, isDisabled, footprint) {
        // A fallen generator needs no progress; a disabled one is greyed out.
        if (isDisabled) return;
        if (!tokensRequired) return;
        if (!position) return;

        const centerX = position[0] * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = position[1] * CELL_SIZE + CELL_SIZE / 2;
        const tint = color || ORANGE_GLOW;

        const addPip = (x, z, size, tintColor, alpha) => {
            const pip = this._makeFlatCell(size, tintColor, alpha, 1.2);
            pip.pos = { x, y: 1.2, z };
            this.objectiveMeshes.push(pip);
        };

        // The turns of the capture, on a tight ring just clear of the objective.
        if (turnsRequired > 0) {
            const ringRadius = footprint + 3;
            const spacing = (2 * Math.PI * ringRadius) / turnsRequired;
            const pipSize = Math.max(2.5, Math.min(5, spacing * 0.5));
            for (let i = 0; i < turnsRequired; i++) {
                const angle = (i / turnsRequired) * Math.PI * 2 - Math.PI / 2;
                const lit = i < turnsHeld;
                addPip(
                    centerX + Math.cos(angle) * ringRadius,
                    centerZ + Math.sin(angle) * ringRadius,
                    pipSize,
                    lit ? tint : OBJECTIVE_PIP_EMPTY,
                    lit ? 0.95 : 0.55,
                );
            }
        }

        // The tokens the capture needs, on a wider ring, lit as they arrive.
        const ringRadius = footprint + 9;
        const spacing = (2 * Math.PI * ringRadius) / tokensRequired;
        const pipSize = Math.max(2.5, Math.min(7, spacing * 0.5));
        for (let i = 0; i < tokensRequired; i++) {
            const angle = (i / tokensRequired) * Math.PI * 2 - Math.PI / 2;
            const lit = i < tokensPresent;
            addPip(
                centerX + Math.cos(angle) * ringRadius,
                centerZ + Math.sin(angle) * ringRadius,
                pipSize,
                lit ? tint : OBJECTIVE_PIP_EMPTY,
                lit ? 0.95 : 0.55,
            );
        }
    }

    // --- Mystery squares ---------------------------------------------------------

    checkMysteryLandings(gameState) {
        if (!gameState.tokens || !gameState.board) return;

        if (gameState.last_triggered_mystery_event) {
            const eventKey = JSON.stringify(gameState.last_triggered_mystery_event);

            if (eventKey !== this.lastProcessedMysteryEvent) {
                const [tokenId, position, effect] = gameState.last_triggered_mystery_event;
                const posKey = `${position[0]},${position[1]}`;

                this.mysteryAnimations.set(posKey, 0.0);
                console.log(`Token ${tokenId} triggered mystery square at ${posKey} - Effect: ${effect}`);
                this.playSound('mystery');

                this.lastProcessedMysteryEvent = eventKey;
            }
        }

        for (const [posKey, progress] of this.mysteryAnimations) {
            if (progress >= 1.0) {
                this.mysteryAnimations.delete(posKey);
            }
        }
    }

    checkCrystalEffectTrigger(gameState) {
        if (!gameState.last_triggered_crystal_effect || !this.crystalEffectAnimator) return;
        if (!gameState.crystal) return;

        const [affectedPlayerId, effectType] = gameState.last_triggered_crystal_effect;
        // The server's last_triggered_crystal_effect persists until the next
        // effect fires, so it replays on every state echo without a guard —
        // which spams the sound and log. Only replay on change.
        const effectKey = `${affectedPlayerId}:${effectType}`;
        if (this.lastProcessedCrystalEffect === effectKey) return;
        this.lastProcessedCrystalEffect = effectKey;

        let affectedTokens = [];
        if (effectType === CRYSTAL_EFFECT.DAMAGE_BOOST) {
            affectedTokens = Object.values(gameState.tokens || {}).filter(
                t => t.player_id === affectedPlayerId && t.is_deployed && t.is_alive
            );
        }

        this.crystalEffectAnimator.startEffect(
            effectType,
            gameState.crystal.position,
            affectedTokens
        );

        switch (effectType) {
            case CRYSTAL_EFFECT.FOG_OF_WAR:
                this.playSound('fog_horn');
                break;
            case CRYSTAL_EFFECT.PHANTOM_ENEMIES:
                this.playSound('ghost');
                break;
            case CRYSTAL_EFFECT.DAMAGE_BOOST:
                this.playSound('lightning');
                break;
            case CRYSTAL_EFFECT.SPEED_BOOST:
                this.playSound('whoosh');
                break;
        }

        console.log(`Crystal effect triggered: ${effectType} for player ${affectedPlayerId}`);
    }

    // --- Particles ---------------------------------------------------------------

    _spawnParticle(p) {
        if (this.particles.length >= this.particleCapacity) {
            this.particles.shift();
        }
        this.particles.push(p);
    }

    triggerExplosion(position, color) {
        const centerX = position[0] * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = position[1] * CELL_SIZE + CELL_SIZE / 2;
        const baseColor = color || [1, 1, 1];

        for (let i = 0; i < 30; i++) {
            this._spawnParticle({
                x: centerX + (Math.random() - 0.5) * CELL_SIZE * 0.5,
                y: WALL_HEIGHT * 0.3 + Math.random() * CELL_SIZE * 0.3,
                z: centerZ + (Math.random() - 0.5) * CELL_SIZE * 0.5,
                vx: (Math.random() - 0.5) * 120,
                vy: 60 + Math.random() * 120,
                vz: (Math.random() - 0.5) * 120,
                life: 0.7 + Math.random() * 0.5,
                maxLife: 1.2,
                size: 2 + Math.random() * 4,
                color: [baseColor[0], baseColor[1], baseColor[2]],
                gravity: 180,
            });
        }
    }

    _spawnConfetti() {
        const colors = [
            [1, 0, 0], [0, 1, 0], [0.2, 0.5, 1], [1, 1, 0], [1, 0, 1], [0, 1, 1],
        ];
        for (let i = 0; i < 100; i++) {
            this._spawnParticle({
                x: Math.random() * BOARD_WIDTH * CELL_SIZE,
                y: 100 + Math.random() * 120,
                z: Math.random() * BOARD_HEIGHT * CELL_SIZE,
                vx: (Math.random() - 0.5) * 25,
                vy: -40 - Math.random() * 40,
                vz: (Math.random() - 0.5) * 25,
                life: 6.0,
                maxLife: 6.0,
                size: 2 + Math.random() * 3,
                color: colors[i % colors.length],
                gravity: 40,
                recycle: true,
            });
        }
    }

    _spawnDust(count) {
        for (let i = 0; i < count; i++) {
            this._spawnParticle({
                x: Math.random() * BOARD_WIDTH * CELL_SIZE,
                y: Math.random() * 200,
                z: Math.random() * BOARD_HEIGHT * CELL_SIZE,
                vx: (Math.random() - 0.5) * 2,
                vy: 0.5 + Math.random() * 1.5,
                vz: (Math.random() - 0.5) * 2,
                life: 8 + Math.random() * 6,
                maxLife: 14,
                size: 0.6 + Math.random() * 1.4,
                color: [0.4, 0.8, 1.0],
                gravity: 0,
                dust: true,
            });
        }
    }

    _updateParticles(dt) {
        // Keep a gentle amount of ambient dust drifting over the board.
        const dustAlive = this.particles.filter(p => p.dust).length;
        if (dustAlive < 120) {
            this._spawnDust(Math.min(4, 120 - dustAlive));
        }

        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.life -= dt;
            p.vy -= (p.gravity || 0) * dt;
            p.x += p.vx * dt;
            p.y += p.vy * dt;
            p.z += p.vz * dt;

            if (p.recycle && p.y < 0) {
                p.y = 220;
                p.x = Math.random() * BOARD_WIDTH * CELL_SIZE;
                p.z = Math.random() * BOARD_HEIGHT * CELL_SIZE;
                p.vy = -50 - Math.random() * 50;
            }

            if (p.life <= 0) {
                if (p.dust || p.recycle) {
                    p.life = p.maxLife;
                    p.x = Math.random() * BOARD_WIDTH * CELL_SIZE;
                    p.y = p.dust ? Math.random() * 200 : 220;
                    p.z = Math.random() * BOARD_HEIGHT * CELL_SIZE;
                    continue;
                }
                this.particles.splice(i, 1);
            }
        }
    }

    _drawStars(proj, view) {
        if (!this.starMesh || !this.starCount) return;
        const gl = this.gl;
        const cam = this.cameraController ? this.cameraController.camera : null;
        const fov = cam ? cam.fov : 0.7;
        const rect = this.canvas.getBoundingClientRect();
        const uPointScale = Math.max(rect.height, 1) / (2 * Math.tan(fov / 2));

        const program = this.programs.points;
        gl.useProgram(program.program);
        gl.uniformMatrix4fv(program.uniforms.uView, false, view);
        gl.uniformMatrix4fv(program.uniforms.uProj, false, proj);
        gl.uniform1f(program.uniforms.uPointScale, uPointScale);

        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE, gl.ONE);
        gl.depthMask(false);
        gl.bindVertexArray(this.starMesh.vao);
        gl.drawArrays(gl.POINTS, 0, this.starCount);
        gl.bindVertexArray(null);
        gl.depthMask(true);
        gl.disable(gl.BLEND);
    }

    _drawParticles(gl, view, proj) {
        const n = Math.min(this.particles.length, this.particleCapacity);
        if (n === 0) return;

        for (let i = 0; i < n; i++) {
            const p = this.particles[i];
            this._pointPositions[i * 3] = p.x;
            this._pointPositions[i * 3 + 1] = p.y;
            this._pointPositions[i * 3 + 2] = p.z;
            this._pointStyles[i * 2] = p.size;
            this._pointStyles[i * 2 + 1] = Math.max(0, Math.min(1, (p.life / p.maxLife) * (p.dust ? 0.5 : 1)));
            this._pointColors[i * 3] = p.color[0];
            this._pointColors[i * 3 + 1] = p.color[1];
            this._pointColors[i * 3 + 2] = p.color[2];
        }

        // Point size scale: viewportHeight / (2 * tan(fov / 2))
        const rect = this.canvas.getBoundingClientRect();
        const cam = this.cameraController ? this.cameraController.camera : null;
        const fov = cam ? cam.fov : 0.7;
        const uPointScale = Math.max(rect.height, 1) / (2 * Math.tan(fov / 2));

        const program = this.programs.points;
        gl.useProgram(program.program);
        gl.uniformMatrix4fv(program.uniforms.uView, false, view);
        gl.uniformMatrix4fv(program.uniforms.uProj, false, proj);
        gl.uniform1f(program.uniforms.uPointScale, uPointScale);

        gl.bindVertexArray(this.pointMesh.vao);
        gl.bindBuffer(gl.ARRAY_BUFFER, this.pointMesh.positionBuffer);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, this._pointPositions.subarray(0, n * 3));
        gl.bindBuffer(gl.ARRAY_BUFFER, this.pointMesh.styleBuffer);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, this._pointStyles.subarray(0, n * 2));
        gl.bindBuffer(gl.ARRAY_BUFFER, this.pointMesh.colorBuffer);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, this._pointColors.subarray(0, n * 3));

        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE, gl.ONE); // additive
        gl.depthMask(false);
        gl.drawArrays(gl.POINTS, 0, n);
        gl.depthMask(true);
        gl.disable(gl.BLEND);
        gl.bindVertexArray(null);
    }

    // --- Floating combat text & pulse rings ---------------------------------------

    showFloatingText(worldPos, text, colorHex) {
        if (!worldPos || worldPos.length < 2) return;

        const centerX = worldPos[0] * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = worldPos[1] * CELL_SIZE + CELL_SIZE / 2;
        const centerY = WALL_HEIGHT * 0.6 + 6;

        const { makeCanvas, uploadCanvasTexture } = this._textures();
        const { canvas, ctx } = makeCanvas(256, 128);
        ctx.clearRect(0, 0, 256, 128);
        ctx.font = 'bold 88px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.lineWidth = 9;
        ctx.strokeStyle = 'rgba(0,0,0,0.85)';
        ctx.fillStyle = colorHex || '#ff4444';
        ctx.strokeText(String(text), 128, 64);
        ctx.fillText(String(text), 128, 64);
        const texture = uploadCanvasTexture(this.gl, canvas);
        this.textures.push(texture);

        this.floatingTexts.push({
            pos: { x: centerX, y: centerY, z: centerZ },
            width: 13,
            height: 6.5,
            texture,
            alpha: 1,
            life: 1.2,
            vy: 22,
        });
    }

    showPulseRing(position, color) {
        if (!position || position.length < 2) return;
        const centerX = position[0] * CELL_SIZE + CELL_SIZE / 2;
        const centerZ = position[1] * CELL_SIZE + CELL_SIZE / 2;
        this.pulseRings = this.pulseRings || [];
        this.pulseRings.push({
            kind: 'unlit',
            mesh: this._mesh('pipQuad', () => buildQuad(1, 1)),
            pos: { x: centerX, y: 1.5, z: centerZ },
            rot: { x: -Math.PI / 2, y: 0, z: 0 },
            scale: { x: CELL_SIZE, y: CELL_SIZE, z: 1 },
            color: color || WHITE,
            alpha: 0.9,
            life: 0.6,
            additive: true,
        });
    }

    _textures() {
        // Lazy import shim so showFloatingText doesn't need the module at
        // class-definition time.
        return {
            makeCanvas: (w, h) => {
                const canvas = document.createElement('canvas');
                canvas.width = w;
                canvas.height = h;
                return { canvas, ctx: canvas.getContext('2d') };
            },
            uploadCanvasTexture: (gl, canvas) => {
                const texture = gl.createTexture();
                gl.bindTexture(gl.TEXTURE_2D, texture);
                gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
                // Restore the default — this global leaks into later texture
                // uploads and flips them upside down.
                gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
                gl.bindTexture(gl.TEXTURE_2D, null);
                return texture;
            },
        };
    }

    // --- Animation ----------------------------------------------------------------

    updateAnimations() {
        const dt = 1 / 60;
        const t = this.animationTime;

        // Crystal: slow spin + breathing scale.
        if (this.crystalMesh) {
            this.crystalMesh.mesh.rot.y = t * 0.3;
            const pulse = 1 + 0.06 * Math.sin(t * 2);
            this.crystalMesh.mesh.scale = { x: pulse, y: 2.2, z: pulse };
        }
        this.crystalFrames.forEach((frame) => {
            frame.rot.y = t * 0.18 * frame.lineSpinDir;
            frame.rot.z = t * 0.06 * frame.lineSpinDir;
        });

        // Laser beams: pulse + occasionally spark at a random beam end.
        for (const line of this.generatorLineMeshes) {
            for (const beam of line.beams) {
                beam.alpha = 0.45 + 0.3 * (0.5 + 0.5 * Math.sin(t * 3 + beam.phase));
            }
            if (Math.random() > 0.92 && line.beams.length) {
                const beam = line.beams[Math.floor(Math.random() * line.beams.length)];
                this._spawnParticle({
                    x: beam.pos.x, y: beam.pos.y + (Math.random() - 0.5) * 4, z: beam.pos.z,
                    vx: (Math.random() - 0.5) * 30, vy: 20 + Math.random() * 40, vz: (Math.random() - 0.5) * 30,
                    life: 0.4, maxLife: 0.4, size: 0.8 + Math.random(),
                    color: [1, 0.9, 0.4], gravity: 60,
                });
            }
        }

        // Mystery rings: tumble + landing animation on trigger.
        for (const ring of this.mysteryRings) {
            const cell = ring.mysteryCell;
            const key = cell ? `${cell.x},${cell.y}` : null;
            const progress = key !== null ? this.mysteryAnimations.get(key) : undefined;

            if (progress !== undefined) {
                const angle = progress * 3 * 2 * Math.PI;
                ring.rot.y = angle;
                ring.scale.x = Math.abs(Math.cos(angle));
                this.mysteryAnimations.set(key, progress + dt);
                continue;
            }
            ring.rot.x = Math.PI / 2 + t * 0.9;
            ring.rot.y = t * 0.36;
            ring.scale.x = 1 + 0.1 * Math.sin(t * 3);
            ring.scale.z = 1 + 0.1 * Math.sin(t * 3);
        }

        // Token / phantom position easing.
        const lerp = (record) => {
            if (record.targetX === undefined) return;
            const s = 1 - Math.exp(-dt * 8);
            record.pos.x += (record.targetX - record.pos.x) * s;
            record.pos.z += (record.targetZ - record.pos.z) * s;
        };
        this.tokens3D.forEach(lerp);
        if (this.phantomTokens3D) this.phantomTokens3D.forEach((record) => {
            lerp(record);
            // Phantom flicker.
            record.alpha = 0.25 + 0.2 * (0.5 + 0.5 * Math.sin(t * 6 + record.flickerPhase));
        });

        this._updateParticles(dt);

        // Floating combat text.
        for (let i = this.floatingTexts.length - 1; i >= 0; i--) {
            const f = this.floatingTexts[i];
            f.life -= dt;
            f.pos.y += f.vy * dt;
            f.vy *= 0.95;
            f.alpha = Math.max(0, f.life / 1.2);
            if (f.life <= 0) {
                this.floatingTexts.splice(i, 1);
            }
        }

        // Pulse rings.
        if (this.pulseRings) {
            for (let i = this.pulseRings.length - 1; i >= 0; i--) {
                const r = this.pulseRings[i];
                r.life -= dt;
                const growth = 1 + (0.6 - r.life) * 6;
                r.scale = { x: CELL_SIZE * growth, y: CELL_SIZE * growth, z: 1 };
                r.alpha = Math.max(0, r.life / 0.6) * 0.9;
                if (r.life <= 0) {
                    this.pulseRings.splice(i, 1);
                }
            }
        }

        if (this.crystalEffectAnimator) {
            this.crystalEffectAnimator.update(0.016);
        }
    }

    addTrauma(amount) {
        this.trauma = Math.min(1, this.trauma + (amount || 0));
    }

    applyCameraShake() {
        // Applied inside _viewMatrix via this.trauma.
    }

    // --- Event-based animations ----------------------------------------------------

    animateTokenMove(tokenId, oldPos, newPos) {
        const record = this.tokens3D.get(tokenId);
        if (record && newPos) {
            record.targetX = newPos[0] * CELL_SIZE + CELL_SIZE / 2;
            record.targetZ = newPos[1] * CELL_SIZE + CELL_SIZE / 2;
        }
        this.playSound('whoosh');
    }

    animateCombat(data) {
        const position = data.defender_position;
        if (!position || position.length < 2) return;

        const killed = data.defender_killed === true;
        this.addTrauma(killed ? 0.6 : 0.25);
        this.triggerExplosion(position, killed ? [1, 0.2, 0.2] : [1, 0.8, 0.2]);
        if (data.damage !== undefined) {
            this.showFloatingText(position, `-${data.damage}`, killed ? '#ff3333' : '#ffcc33');
        }
        this.playSound('attack');
    }

    animateTokenDeploy(data) {
        this.playSound('deploy');
        if (data && data.position) {
            this.showPulseRing(data.position, [0.3, 0.8, 1.0]);
        }
    }

    animateGeneratorUpdate(data) {
        if (data.is_disabled) {
            this.addTrauma(0.8);
            this.triggerExplosion(data.position, [1.0, 0.5, 0.1]);
            this.playSound('generator_explosion');
        }
    }

    animateCrystalUpdate() {
        // Reserved for capture-progress pulses (parity with Babylon version).
    }

    animateMysteryEvent(data) {
        const position = data.position;
        if (!position || position.length < 2) return;
        const posKey = `${position[0]},${position[1]}`;
        this.mysteryAnimations.set(posKey, 0.0);
        this.addTrauma(0.2);
        this.triggerExplosion(position, [0.6, 1.0, 0.6]);
        this.playSound('mystery');
    }

    triggerTokenBurst(position, color) {
        if (!position || position.length < 2) return;
        this.triggerExplosion(position, color || WHITE);
    }

    triggerCrystalBurst(position) {
        if (!position || position.length < 2) return;
        this.triggerExplosion(position, [0.2, 0.9, 1.0]);
        this.triggerExplosion(position, [1.0, 0.9, 0.3]);
    }

    triggerVictoryEffect() {
        this.addTrauma(0.9);
        this._spawnConfetti();
        if (this.crystalMesh) {
            this.triggerCrystalBurst(this.crystalMesh.position);
        }
        this.playSound('crystal');
    }

    // --- Full state update ---------------------------------------------------------

    updateGameState(gameState) {
        // Overlays read the state, so keep the last one.
        this.lastGameState = gameState;
        this.createSpecialCells(gameState);
        this.updateTokens(gameState);
        this.checkMysteryLandings(gameState);
        this.updateSpecialCellColors(gameState);
        this.checkCrystalEffectTrigger(gameState);
        // The ambient hum follows the generators: one per standing generator.
        this.updateGeneratorHums(gameState.generators || []);
        // Capture progress on the objectives, and the threat overlay on
        // the cell under the pointer.
        this.updateObjectiveIndicators(gameState);
        this.updateThreatIndicators();
    }

    // --- Frame ---------------------------------------------------------------------

    _resizeCanvas() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const width = Math.max(1, Math.floor(this.canvas.clientWidth * dpr * this.renderScale));
        const height = Math.max(1, Math.floor(this.canvas.clientHeight * dpr * this.renderScale));
        if (this.canvas.width !== width || this.canvas.height !== height) {
            this.canvas.width = width;
            this.canvas.height = height;
        }
    }

    _renderFrame() {
        const gl = this.gl;
        if (!gl) return;
        this._resizeCanvas();
        gl.viewport(0, 0, this.canvas.width, this.canvas.height);

        const cam = this.cameraController ? this.cameraController.camera : null;
        if (!cam) {
            gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
            return;
        }

        const proj = this._projectionMatrix(cam);
        const view = this._viewMatrix(cam);
        const eyePos = cam.position;
        const t = this.animationTime;

        // Render into the bloom scene FBO when post-processing is active.
        const bloomActive = this.bloomPass
            ? this.bloomPass.beginScene(this.canvas.width, this.canvas.height)
            : false;
        if (!bloomActive) {
            gl.bindFramebuffer(gl.FRAMEBUFFER, null);
            gl.viewport(0, 0, this.canvas.width, this.canvas.height);
        }

        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

        // --- Star field (static points, additive, no depth writes) ---
        this._drawStars(proj, view);

        // --- Collect draw lists ---
        const opaque = [];
        const transparent = [];

        // Board ground (unlit, textured, gently pulsing grid).
        opaque.push({
            kind: 'unlit',
            mesh: this._mesh('ground', () => buildGround(BOARD_WIDTH * CELL_SIZE, BOARD_HEIGHT * CELL_SIZE)),
            pos: { x: 0, y: 0, z: 0 },
            rot: { x: 0, y: 0, z: 0 },
            scale: { x: 1, y: 1, z: 1 },
            color: [1, 1, 1],
            useMap: true,
            texture: this.gridTexture,
            brightness: 1 + 0.08 * Math.sin(t * 2),
            alpha: 1,
        });

        // Grid + cage lines.
        transparent.push({
            kind: 'line',
            mesh: this.meshCache.get('gridVertical'),
            pos: { x: 0, y: 0, z: 0 }, rot: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 },
            color: CYAN_GLOW, alpha: 0.55, additive: true,
        });
        transparent.push({
            kind: 'line',
            mesh: this.meshCache.get('gridCage'),
            pos: { x: 0, y: 0, z: 0 }, rot: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 },
            color: CYAN_GLOW, alpha: 0.85, additive: true,
        });

        // Special cells (crystal, pillars, rings, beams).
        for (const obj of this.specialCellObjects) {
            const alpha = obj.alpha !== undefined ? obj.alpha : 1;
            if (obj.additive || alpha < 1 || obj.kind === 'line') {
                transparent.push(obj);
            } else {
                opaque.push(obj);
            }
        }

        // Tokens + health labels.
        this.tokens3D.forEach((record) => {
            if (record.hidden) return;
            const alpha = record.alpha !== undefined ? record.alpha : 1;
            const entry = {
                kind: 'lit',
                mesh: record.mesh,
                pos: record.pos,
                rot: record.rot,
                scale: record.scale,
                color: record.color,
                emissive: record.emissive,
                alpha,
                metallic: record.metallic,
                roughness: record.roughness,
            };
            if (alpha < 1) transparent.push(entry); else opaque.push(entry);
            // Health label floats above the token, faces the camera.
            transparent.push({
                billboard: true,
                pos: { x: record.pos.x, y: TOKEN_CENTER_Y + TOKEN_HEIGHT / 2 + 8, z: record.pos.z },
                width: record.label.width,
                height: record.label.height,
                texture: record.label.texture,
                useMap: true,
                color: [1, 1, 1],
                alpha: alpha < 1 ? 0.7 : 1,
            });
        });
        if (this.phantomTokens3D) {
            this.phantomTokens3D.forEach((record) => {
                transparent.push({
                    kind: 'lit',
                    mesh: record.mesh,
                    pos: record.pos,
                    rot: record.rot,
                    scale: record.scale,
                    color: record.color,
                    emissive: record.emissive,
                    alpha: record.alpha,
                    metallic: record.metallic,
                    roughness: record.roughness,
                });
                transparent.push({
                    billboard: true,
                    pos: { x: record.pos.x, y: TOKEN_CENTER_Y + TOKEN_HEIGHT / 2 + 8, z: record.pos.z },
                    width: record.label.width,
                    height: record.label.height,
                    texture: record.label.texture,
                    useMap: true,
                    color: [1, 1, 1],
                    alpha: 0.7,
                });
            });
        }

        // Indicators.
        for (const m of this.validMoveMeshes) transparent.push(m);
        for (const m of this.validAttackMeshes) transparent.push(m);
        for (const m of this.threatMeshes) transparent.push(m);
        for (const m of this.objectiveMeshes) transparent.push(m);
        if (this.hoverMesh) transparent.push(this.hoverMesh);
        if (this.pulseRings) for (const m of this.pulseRings) transparent.push(m);
        for (const f of this.floatingTexts) {
            transparent.push({
                billboard: true,
                pos: f.pos,
                width: f.width,
                height: f.height,
                texture: f.texture,
                useMap: true,
                color: [1, 1, 1],
                alpha: f.alpha,
            });
        }
        // Crystal effect objects (fog puffs, ghosts, lightning bolts/flashes).
        if (this.crystalEffectAnimator && this.crystalEffectAnimator.renderObjects) {
            for (const obj of this.crystalEffectAnimator.renderObjects()) {
                transparent.push(obj);
            }
        }

        // Sort transparent back-to-front.
        transparent.sort((a, b) => {
            const da = (a.pos.x - eyePos.x) ** 2 + (a.pos.z - eyePos.z) ** 2;
            const db = (b.pos.x - eyePos.x) ** 2 + (b.pos.z - eyePos.z) ** 2;
            return db - da;
        });

        // --- Draw opaque ---
        for (const obj of opaque) {
            if (obj.kind === 'unlit') {
                this._drawUnlit(gl, obj, view, proj);
            } else {
                this._drawLit(gl, obj, view, proj, eyePos);
            }
        }

        // --- Draw transparent ---
        gl.depthMask(false);
        for (const obj of transparent) {
            if (obj.billboard) {
                gl.enable(gl.BLEND);
                gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
                this._drawBillboard(gl, obj, view, proj, eyePos);
                gl.disable(gl.BLEND);
                continue;
            }
            if (obj.additive) {
                gl.enable(gl.BLEND);
                gl.blendFunc(gl.ONE, gl.ONE);
            } else {
                gl.enable(gl.BLEND);
                gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
            }
            if (obj.kind === 'line') {
                this._drawLine(gl, obj, view, proj);
            } else if (obj.kind === 'beam') {
                this._drawBeam(gl, obj, view, proj);
            } else if (obj.kind === 'unlit') {
                this._drawUnlit(gl, obj, view, proj);
            } else {
                this._drawLit(gl, obj, view, proj, eyePos);
            }
            gl.disable(gl.BLEND);
        }
        gl.depthMask(true);

        // --- Particles (additive points) ---
        this._drawParticles(gl, view, proj);

        // --- Resolve to canvas: bloom + god rays + vignette + grain (or direct) ---
        if (bloomActive) {
            this.bloomPass.endScene(this.animationTime, this._rayLightPos(proj, view));
        }
    }

    /**
     * Screen-space position (UV, bottom-left origin) of the crystal — the
     * god-ray light the composite pass radially blurs toward. Returns null
     * when the crystal is behind the camera, rays are disabled, or there is
     * no crystal in the state.
     */
    _rayLightPos(proj, view) {
        const cp = this.crystalWorldPos;
        if (!this.raysEnabled || !cp) return null;
        const clip = mat4TransformPoint(mat4Multiply(proj, view), cp);
        if (clip.w <= 0.001) return null; // behind the camera
        const ndcX = clip.x / clip.w;
        const ndcY = clip.y / clip.w;
        // Light slightly off-screen still throws rays; far outside just smears.
        if (Math.abs(ndcX) > 2.5 || Math.abs(ndcY) > 2.5) return null;
        return { x: ndcX * 0.5 + 0.5, y: ndcY * 0.5 + 0.5 };
    }

    _drawBeam(gl, obj, view, proj) {
        // Beam mesh is a unit cylinder along Y; the basis carries the length.
        const model = new Float32Array([
            obj.basis.x.x, obj.basis.x.y, obj.basis.x.z, 0,
            obj.basis.y.x, obj.basis.y.y, obj.basis.y.z, 0,
            obj.basis.z.x, obj.basis.z.y, obj.basis.z.z, 0,
            obj.pos.x, obj.pos.y, obj.pos.z, 1,
        ]);
        const program = this.programs.unlit;
        gl.useProgram(program.program);
        gl.uniformMatrix4fv(program.uniforms.uModel, false, model);
        gl.uniformMatrix4fv(program.uniforms.uView, false, view);
        gl.uniformMatrix4fv(program.uniforms.uProj, false, proj);
        gl.uniform3fv(program.uniforms.uColor, obj.color);
        gl.uniform1f(program.uniforms.uAlpha, obj.alpha !== undefined ? obj.alpha : 0.85);
        gl.uniform1f(program.uniforms.uBrightness, obj.brightness || 2.0);
        gl.uniform1i(program.uniforms.uUseMap, 0);
        obj.mesh.draw();
    }

    dispose() {        if (this._rafId) cancelAnimationFrame(this._rafId);
        this._rafId = null;
        if (this._resizeHandler) window.removeEventListener('resize', this._resizeHandler);
        if (this.crystalEffectAnimator) this.crystalEffectAnimator.cleanup();

        if (this.audioManager) {
            this.audioManager.cleanup();
        }
        const gl = this.gl;
        if (this.bloomPass) {
            this.bloomPass.dispose();
            this.bloomPass = null;
        }
        if (gl) {
            for (const mesh of this.meshCache.values()) {
                if (mesh.dispose) mesh.dispose();
            }
            for (const tex of this.textures) {
                gl.deleteTexture(tex);
            }
            if (this.pointMesh) {
                gl.deleteVertexArray(this.pointMesh.vao);
                gl.deleteBuffer(this.pointMesh.positionBuffer);
                gl.deleteBuffer(this.pointMesh.styleBuffer);
                gl.deleteBuffer(this.pointMesh.colorBuffer);
            }
            if (this.starMesh) {
                gl.deleteVertexArray(this.starMesh.vao);
                gl.deleteBuffer(this.starMesh.positionBuffer);
                gl.deleteBuffer(this.starMesh.styleBuffer);
                gl.deleteBuffer(this.starMesh.colorBuffer);
            }
            for (const key of Object.keys(this.programs)) {
                gl.deleteProgram(this.programs[key].program);
            }
        }
        this.meshCache.clear();
        this.tokens3D.clear();
        this.gl = null;
    }
}

export { VanillaRenderer3D };
