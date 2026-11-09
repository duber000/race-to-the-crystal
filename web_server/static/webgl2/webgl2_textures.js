/**
 * webgl2_textures.js - Canvas-generated textures (no network fetches).
 *
 * Everything the original client loaded from a third-party CDN (grid
 * pattern, particle flare) or drew into a Babylon DynamicTexture
 * (health labels) is generated here from a 2D canvas instead.
 */

export function makeCanvas(width, height) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    return { canvas, ctx: canvas.getContext('2d') };
}

export function uploadCanvasTexture(gl, canvas) {
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
    // Restore the default — this global leaks into later texture uploads
    // (e.g. health labels) and flips them upside down.
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.bindTexture(gl.TEXTURE_2D, null);
    return texture;
}

/** Faint cyan grid on black — the board's ground texture. */
export function createGridTexture(gl, boardWidth) {
    const { canvas, ctx } = makeCanvas(1024, 1024);
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, 1024, 1024);
    ctx.strokeStyle = 'rgba(0, 200, 255, 0.2)';
    ctx.lineWidth = 2;
    const spacing = 1024 / boardWidth;
    for (let i = 0; i <= boardWidth; i++) {
        ctx.beginPath();
        ctx.moveTo(i * spacing, 0);
        ctx.lineTo(i * spacing, 1024);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(0, i * spacing);
        ctx.lineTo(1024, i * spacing);
        ctx.stroke();
    }
    return uploadCanvasTexture(gl, canvas);
}

/** "9hp" text texture for the floating health labels. Cached per value. */
const healthLabelCache = new Map();

export function createHealthLabelTexture(gl, text, isPhantom) {
    const key = `${isPhantom ? 'phantom_' : ''}${text}`;
    if (healthLabelCache.has(key)) return healthLabelCache.get(key);

    const { canvas, ctx } = makeCanvas(256, 128);
    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, 256, 128);
    ctx.font = 'bold 80px monospace';
    ctx.fillStyle = isPhantom ? 'rgba(255, 255, 255, 0.7)' : 'white';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 128, 64);
    const texture = uploadCanvasTexture(gl, canvas);
    healthLabelCache.set(key, texture);
    return texture;
}
