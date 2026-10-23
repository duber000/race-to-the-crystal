/**
 * Touch gesture arbiter (Phase 4.1).
 *
 * Pointer-event based; adds single-finger camera orbit (which the stripped
 * Babylon pointer input cannot do) while leaving tap selection to the
 * existing InputHandler path.
 */
export class TouchArbiter {
    constructor(gameClient) {
        this.gameClient = gameClient;
        this.canvas = gameClient.canvas;
        this.pointers = new Map();
        this.dragging = false;
        this.attach();
    }

    attach() {
        if (!this.canvas) return;
        this.canvas.addEventListener('pointerdown', (e) => this.onDown(e), { passive: false });
        this.canvas.addEventListener('pointermove', (e) => this.onMove(e), { passive: false });
        this.canvas.addEventListener('pointerup', (e) => this.onUp(e));
        this.canvas.addEventListener('pointercancel', (e) => this.onUp(e));
    }

    onDown(e) {
        this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY, t: Date.now() });
        try { this.canvas.setPointerCapture(e.pointerId); } catch (_) {}
    }

    onMove(e) {
        const p = this.pointers.get(e.pointerId);
        if (!p) return;
        if (this.pointers.size === 1) {
            const dx = e.clientX - p.x;
            const dy = e.clientY - p.y;
            if (!this.dragging && Math.hypot(dx, dy) > 12) this.dragging = true;
            if (this.dragging) {
                const cc = this.gameClient.cameraController;
                if (cc && cc.cameraMode === 'overview' && cc.camera) {
                    cc.camera.alpha -= dx * 0.005;
                    cc.camera.beta = Math.max(0.1, Math.min(Math.PI / 2 - 0.1, cc.camera.beta + dy * 0.005));
                }
                p.x = e.clientX;
                p.y = e.clientY;
            }
        } else if (this.pointers.size === 2) {
            // Pinch zoom: use distance between the two pointers.
            const pts = Array.from(this.pointers.values());
            // We do not track previous distance; use movement average as zoom.
            const dy = e.clientY - p.y;
            const cc = this.gameClient.cameraController;
            if (cc) cc.adjustZoom(dy > 0 ? 1 : -1);
        }
        try { e.preventDefault(); } catch (_) {}
    }

    onUp(e) {
        const p = this.pointers.get(e.pointerId);
        const wasTap = p && !this.dragging && (Date.now() - p.t < 300);
        this.pointers.delete(e.pointerId);
        if (this.pointers.size === 0) this.dragging = false;
        // Taps are left to the existing InputHandler touchdown handlers.
        void wasTap;
    }
}
