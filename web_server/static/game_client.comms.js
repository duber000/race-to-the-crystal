/**
 * Tactical Comms sidebar — Phase 2.3.
 *
 * Fed by `RadioChatter` events (server event stream). Renders an avatar
 * badge, a name and the message text in a collapsible <details> panel,
 * reusing the HUD conventions.
 */
export class TacticalComms {
    constructor(gameClient) {
        this.gameClient = gameClient;
        this.panel = null;
        this.list = null;
        this.ensurePanel();
    }

    ensurePanel() {
        let panel = document.getElementById('tactical-comms');
        if (!panel) {
            panel = document.createElement('details');
            panel.id = 'tactical-comms';
            panel.className = 'hidden comms-panel';
            panel.setAttribute('open', '');
            panel.innerHTML = `
                <summary><h3>Tactical Comms</h3></summary>
                <div class="panel-content" id="comms-content">
                    <div id="comms-list"></div>
                </div>`;
            const hud = document.getElementById('hud');
            if (hud && hud.parentNode) {
                hud.parentNode.insertBefore(panel, hud.nextSibling);
            } else {
                document.body.appendChild(panel);
            }
        }
        this.panel = panel;
        this.list = panel.querySelector('#comms-list');
    }

    show() {
        if (this.panel) this.panel.classList.remove('hidden');
    }

    hide() {
        if (this.panel) this.panel.classList.add('hidden');
    }

    clear() {
        if (this.list) this.list.innerHTML = '';
    }

    add(data) {
        if (!this.list || !data) return;
        this.show();
        const entry = document.createElement('div');
        entry.className = 'comms-entry';
        entry.dataset.tone = data.tone || 'neutral';

        const name = document.createElement('div');
        name.className = 'comms-name';
        name.textContent = data.player_name || data.player_id || 'Agent';

        const text = document.createElement('div');
        text.className = 'comms-text';
        text.textContent = data.text || '';

        entry.appendChild(name);
        entry.appendChild(text);
        this.list.appendChild(entry);
        // Keep the newest visible.
        this.list.scrollTop = this.list.scrollHeight;
    }
}
