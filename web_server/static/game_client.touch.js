/**
 * Touch gesture arbiter (Phase 4.1).
 *
 * Pointer-event based; adds single-finger camera orbit (which the stripped
 * Babylon pointer input cannot do) while leaving tap selection to the
 * existing InputHandler path.
 *
 * Gestures:
 * - 1 finger, tap            -> handled by InputHandler (tap detection)
 * - 1 finger, drag            -> camera orbit (alpha/beta)
 * - 1 finger, hold >500 ms    -> long-press: inspect the cell's threat
 *                                indicators (emits `hover`, which is what
 *                                the mouse gets for free and touch never
 *                                had)
 * - 2 fingers, pinch + drag   -> zoom (proportional to pinch distance)
 *                                and pan (follows the pinch midpoint)
 */
export class TouchArbiter {
    constructor(gameClient) {
        this.gameClient = gameClient;
        this.canvas = gameClient.canvas;
        this.pointers = new Map();
        this.dragging = false;
        // Two-pointer gesture state: previous pinch midpoint/distance.
        this.prevMid = null;
        this.prevDist = 0;
        // Long-press state for the single-pointer case.
        this.longPressTimer = null;
        this.longPressFired = false;
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
        if (this.pointers.size === 1) {
            this.longPressFired = false;
            this.armLongPress(e.clientX, e.clientY);
        } else {
            // A second finger cancels any pending long-press and resets
            // the pinch baseline.
            this.cancelLongPress();
            this.prevMid = null;
            this.prevDist = 0;
        }
    }

    onMove(e) {
        const p = this.pointers.get(e.pointerId);
        if (!p) return;
        if (this.pointers.size === 1) {
            const dx = e.clientX - p.x;
            const dy = e.clientY - p.y;
            if (!this.dragging && Math.hypot(dx, dy) > 12) {
                this.dragging = true;
                this.cancelLongPress();
            }
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
            this.onTwoPointerMove();
        }
        try { e.preventDefault(); } catch (_) {}
    }

    onTwoPointerMove() {
        const pts = Array.from(this.pointers.values());
        const mid = {
            x: (pts[0].x + pts[1].x) / 2,
            y: (pts[0].y + pts[1].y) / 2,
        };
        const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
        const cc = this.gameClient.cameraController;
        if (cc && cc.cameraMode === 'overview' && cc.camera && !cc._transition) {
            if (this.prevMid && this.prevDist > 0 && dist > 0) {
                // Zoom: proportional to the pinch distance ratio, so a
                // steady pinch gives a steady zoom (rather than a fixed
                // step per move event). adjustZoom's factor is
                // 0.88^steps, so invert it for a target factor of
                // prevDist/dist.
                const ratio = dist / this.prevDist;
                cc.adjustZoom(Math.log(ratio) / Math.log(1 / 0.88));
                // Pan: grab-the-world, following the midpoint.
                const mdx = mid.x - this.prevMid.x;
                const mdy = mid.y - this.prevMid.y;
                if (cc._groundRight && cc._groundForward && cc._panTarget && this.canvas.clientHeight > 0) {
                    const right = cc._groundRight();
                    const forward = cc._groundForward();
                    const scale = (cc.camera.radius * 1.6) / this.canvas.clientHeight;
                    cc._panTarget(
                        right.x * (-mdx * scale) + forward.x * (mdy * scale),
                        right.z * (-mdx * scale) + forward.z * (mdy * scale),
                    );
                }
            }
            this.prevMid = mid;
            this.prevDist = dist;
        }
    }

    armLongPress(clientX, clientY) {
        this.cancelLongPress();
        const downX = clientX;
        const downY = clientY;
        this.longPressTimer = setTimeout(() => {
            this.longPressTimer = null;
            if (this.pointers.size !== 1 || this.dragging) return;
            this.longPressFired = true;
            const input = this.gameClient.inputHandler;
            if (!input || !this.canvas) return;
            const rect = this.canvas.getBoundingClientRect();
            const x = downX - rect.left;
            const y = downY - rect.top;
            const cell = (typeof input.pickGridCellWithFallback === 'function')
                ? input.pickGridCellWithFallback(x, y)
                : input.pickGridCell(x, y);
            if (cell) {
                // Same signal the mouse's hover produces, so threat
                // indicators render for the held cell.
                input.emit('hover', { gridX: cell.gridX, gridY: cell.gridY });
            }
        }, 500);
    }

    cancelLongPress() {
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
    }

    onUp(e) {
        const p = this.pointers.get(e.pointerId);
        const wasTap = p && !this.dragging && (Date.now() - p.t < 300);
        this.pointers.delete(e.pointerId);
        this.cancelLongPress();
        if (this.pointers.size === 0) {
            this.dragging = false;
            this.prevMid = null;
            this.prevDist = 0;
        }
        // Taps are left to the existing InputHandler touchdown handlers.
        // A long-press already lasts >300 ms, so it never reads as a tap.
        void wasTap;
    }
}
