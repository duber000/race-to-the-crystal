/**
 * Radial action palette (Phase 4.2).
 * Shows the legal actions for the currently selected token. DOM-based so it
 * inherits HUD conventions and stays accessible.
 */
export class RadialPalette {
    constructor(gameClient) {
        this.gameClient = gameClient;
        this.panel = null;
        this.ensure();
    }

    ensure() {
        let p = document.getElementById('radial-palette');
        if (!p) {
            p = document.createElement('div');
            p.id = 'radial-palette';
            p.className = 'hidden radial-palette';
            p.innerHTML = `<div id="radial-list"></div>`;
            document.body.appendChild(p);
        }
        this.panel = p;
        this.list = p.querySelector('#radial-list');
    }

    refresh(selectedTokenId) {
        if (!this.panel || !this.list) return;
        const state = this.gameClient.gameState;
        if (!selectedTokenId || !state) {
            this.panel.classList.add('hidden');
            return;
        }
        const token = state.tokens && state.tokens[selectedTokenId];
        if (!token) { this.panel.classList.add('hidden'); return; }
        const targets = (this.gameClient.inputController && typeof this.gameClient.inputController.calculateValidTargets === 'function')
            ? this.gameClient.inputController.calculateValidTargets(token) : new Set();
        const phase = this.gameClient.turnPhase;
        this.list.innerHTML = '';
        const label = document.createElement('div');
        label.className = 'radial-label';
        label.textContent = `${phase} • ${targets.size} targets`;
        this.list.appendChild(label);
        this.panel.classList.remove('hidden');
    }
}
