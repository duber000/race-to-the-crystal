/**
 * Replay scrubber (Phase 2.4).
 *
 * Does not require server-side battle logging: any JSON file matching the
 * `.rttc-battle.json` shape (or a plain array of full-state snapshots) can be
 * loaded from disk and walked turn by turn. Incoming live updates are detached
 * while replaying.
 */
export class ReplayController {
    constructor(gameClient) {
        this.gameClient = gameClient;
        this.snapshots = [];
        this.cursor = 0;
        this.playing = false;
        this.timer = null;
        this.speed = 1;
        this.panel = null;
        this.ensurePanel();
    }

    ensurePanel() {
        let panel = document.getElementById('replay-controls');
        if (!panel) {
            panel = document.createElement('details');
            panel.id = 'replay-controls';
            panel.className = 'hidden replay-panel';
            panel.innerHTML = `
                <summary><h3>Replay</h3></summary>
                <div class="panel-content" id="replay-content">
                    <input type="file" id="replay-file" accept="application/json,.json" />
                    <div class="replay-scrubber">
                        <input type="range" id="replay-scrubber" min="0" max="0" value="0" />
                        <span id="replay-pos">0 / 0</span>
                    </div>
                    <div class="replay-buttons">
                        <button id="replay-prev">&laquo;</button>
                        <button id="replay-play">Play</button>
                        <button id="replay-next">&raquo;</button>
                        <button id="replay-exit">Exit</button>
                        <button id="replay-export">Export&nbsp;&darr;</button>
                    </div>
                    <div class="replay-speeds" id="replay-speeds">
                        <button class="replay-speed active" data-speed="1">1&times;</button>
                        <button class="replay-speed" data-speed="2">2&times;</button>
                        <button class="replay-speed" data-speed="5">5&times;</button>
                    </div>
                </div>`;
            document.body.appendChild(panel);
        }
        this.panel = panel;
        this.wire();
    }

    wire() {
        const file = this.panel.querySelector('#replay-file');
        file.addEventListener('change', (e) => {
            const f = e.target.files && e.target.files[0];
            if (!f) return;
            const reader = new FileReader();
            reader.onload = () => {
                try {
                    const json = JSON.parse(reader.result);
                    this.loadBattleLog(json);
                } catch (err) {
                    console.error('[Replay] Bad file:', err);
                }
            };
            reader.readAsText(f);
        });

        const scrub = this.panel.querySelector('#replay-scrubber');
        scrub.addEventListener('input', () => {
            this.seek(parseInt(scrub.value, 10));
        });

        this.panel.querySelector('#replay-prev').addEventListener('click', () => this.seek(this.cursor - 1));
        this.panel.querySelector('#replay-next').addEventListener('click', () => this.seek(this.cursor + 1));
        this.panel.querySelector('#replay-play').addEventListener('click', () => this.togglePlay());
        this.panel.querySelector('#replay-exit').addEventListener('click', () => this.exit());
        const exportBtn = this.panel.querySelector('#replay-export');
        if (exportBtn) exportBtn.addEventListener('click', () => this.exportBattleLog());
        for (const btn of this.panel.querySelectorAll('.replay-speed')) {
            btn.addEventListener('click', () => this.setSpeed(parseInt(btn.dataset.speed, 10)));
        }
    }

    setSpeed(n) {
        if (![1, 2, 5].includes(n)) return;
        this.speed = n;
        for (const btn of this.panel.querySelectorAll('.replay-speed')) {
            btn.classList.toggle('active', parseInt(btn.dataset.speed, 10) === n);
        }
        // Restart the timer so the new rate takes effect immediately.
        if (this.playing) {
            this.stop();
            this.togglePlay();
        }
    }

    async exportBattleLog() {
        const gameId = this.gameClient.networkManager && this.gameClient.networkManager.currentGameId;
        try {
            if (gameId) {
                const res = await fetch(`/api/game/${encodeURIComponent(gameId)}/battle`);
                const json = await res.json();
                if (!json.success) {
                    console.warn('[Replay] Battle log unavailable:', json.message);
                    return;
                }
                this.download(json.data, `${gameId}.rttc-battle.json`);
            } else if (this.snapshots.length) {
                // No live game (e.g. viewing an imported file): export what
                // is currently loaded.
                this.download({ snapshots: this.snapshots }, 'battle.rttc-battle.json');
            }
        } catch (e) {
            console.error('[Replay] Export failed:', e);
        }
    }

    download(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    loadBattleLog(json) {
        if (Array.isArray(json)) {
            this.snapshots = json;
        } else if (json && Array.isArray(json.snapshots)) {
            this.snapshots = json.snapshots;
        } else if (json && Array.isArray(json.states)) {
            this.snapshots = json.states;
        } else {
            console.warn('[Replay] No snapshots found');
            this.snapshots = [];
        }
        this.cursor = 0;
        this.enterReplayMode();
        this.updateScrubber();
        this.seek(0);
    }

    enterReplayMode() {
        this.gameClient.replayMode = true;
        this.gameClient.stateManager.replayMode = true;
        if (this.panel) this.panel.classList.remove('hidden');
    }

    exit() {
        this.stop();
        this.gameClient.replayMode = false;
        this.gameClient.stateManager.replayMode = false;
        if (this.panel) this.panel.classList.add('hidden');
    }

    seek(index) {
        if (!this.snapshots.length) return;
        this.cursor = Math.max(0, Math.min(this.snapshots.length - 1, index));
        const snap = this.snapshots[this.cursor];
        const state = (snap && snap.game_state) ? snap.game_state : snap;
        // Preserve board/terrain if the snapshot only carries the mutable layer.
        if (!state.board && this.gameClient.stateManager.gameState && this.gameClient.stateManager.gameState.board) {
            state.board = this.gameClient.stateManager.gameState.board;
        }
        try {
            this.gameClient.stateManager.setFullState({ game_state: state });
        } catch (e) {
            console.error('[Replay] apply failed:', e);
        }
        // Re-emit the recorded events for this turn into the FX pipeline.
        if (Array.isArray(this.snapshots[this.cursor]?.events)) {
            for (const ev of this.snapshots[this.cursor].events) {
                this.dispatchFx(ev);
            }
        }
        this.updateScrubber();
    }

    dispatchFx(ev) {
        if (!ev || !ev.type) return;
        const type = String(ev.type).toLowerCase();
        const r = this.gameClient.renderer;
        if (!r) return;
        if (type === 'combat_resolved' && typeof r.animateCombat === 'function') r.animateCombat(ev);
        else if (type === 'token_moved' && typeof r.animateTokenMove === 'function') r.animateTokenMove(ev.token_id, ev.old_position, ev.new_position);
        else if (type === 'token_deployed' && typeof r.animateTokenDeploy === 'function') r.animateTokenDeploy(ev);
        else if (type === 'generator_changed' && typeof r.animateGeneratorUpdate === 'function') r.animateGeneratorUpdate(ev);
        else if (type === 'mystery_triggered' && typeof r.animateMysteryEvent === 'function') r.animateMysteryEvent(ev);
    }

    updateScrubber() {
        const scrub = this.panel && this.panel.querySelector('#replay-scrubber');
        const pos = this.panel && this.panel.querySelector('#replay-pos');
        if (scrub) {
            scrub.max = Math.max(0, this.snapshots.length - 1);
            scrub.value = this.cursor;
        }
        if (pos) {
            pos.textContent = `${this.cursor + 1} / ${this.snapshots.length}`;
        }
    }

    togglePlay() {
        this.playing = !this.playing;
        const btn = this.panel && this.panel.querySelector('#replay-play');
        if (btn) btn.textContent = this.playing ? 'Pause' : 'Play';
        if (this.playing) {
            this.timer = setInterval(() => {
                if (this.cursor >= this.snapshots.length - 1) { this.togglePlay(); return; }
                this.seek(this.cursor + 1);
            }, 1000 / this.speed);
        } else {
            if (this.timer) clearInterval(this.timer);
            this.timer = null;
        }
    }

    stop() {
        if (this.timer) clearInterval(this.timer);
        this.timer = null;
        this.playing = false;
    }
}
