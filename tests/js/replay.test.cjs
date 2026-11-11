'use strict';

/**
 * game_client.replay.js — battle-log replay scrubber.
 *
 * The replay feature loads exported battle JSON (from the server or from a
 * file) and walks it turn by turn. The value being pinned here is the
 * parse-shape tolerance ({ snapshots } vs { states } vs bare array), the
 * cursor clamping in seek(), the board-preservation rule for delta-only
 * snapshots, and the event re-dispatch into the FX pipeline.
 *
 * The module touches `document` at construction (it builds its control
 * panel), so it is evaluated in a node:vm context with a minimal DOM stub.
 * Only the panel-creation path is exercised; querySelector results are
 * cached per selector so updateScrubber() can write into them.
 *
 * Run with: npm run test:js   (or: node --test tests/js/)
 */

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const assert = require('node:assert/strict');

/** Strip ES module syntax vm can't run; fail loudly on anything new. */
function stripModule(source, label) {
    const stripped = source.replace(/^export /gm, '');
    if (/^\s*(import|export)\s/m.test(stripped)) {
        throw new Error(
            `${label}: unhandled ES module syntax — update stripModule() in this test`
        );
    }
    return stripped;
}

function makeElement(tag) {
    const el = {
        tagName: tag,
        id: '',
        className: '',
        innerHTML: '',
        textContent: '',
        value: '0',
        max: 0,
        dataset: {},
        style: {},
        classAdds: [],
        classRemoves: [],
        __attrs: {},
        classList: {
            add(...names) { el.classAdds.push(...names); },
            remove(...names) { el.classRemoves.push(...names); },
            toggle() {},
        },
        setAttribute(name, value) { el.__attrs[name] = String(value); },
        getAttribute(name) { return el.__attrs[name] ?? null; },
        addEventListener() {},
        appendChild() {},
        querySelector(sel) {
            if (!el.__qs) el.__qs = {};
            if (!el.__qs[sel]) el.__qs[sel] = makeElement('div');
            return el.__qs[sel];
        },
        querySelectorAll(sel) {
            if (sel === '.replay-speed') return el.__speedButtons ?? [];
            return [];
        },
    };
    return el;
}

function createHarness() {
    const warnings = [];
    const rendererCalls = [];
    const stateFullStates = [];
    const document = {
        getElementById: () => null,
        createElement: (tag) => makeElement(tag),
        body: { appendChild() {} },
    };
    const gameClient = {
        replayMode: false,
        networkManager: { currentGameId: null },
        stateManager: {
            replayMode: false,
            gameState: null,
            setFullState({ game_state }) {
                this.gameState = game_state;
                stateFullStates.push(game_state);
            },
        },
        renderer: {
            animateTokenMove(tokenId, oldPos, newPos) {
                rendererCalls.push(['token_moved', tokenId, oldPos, newPos]);
            },
            animateCombat(ev) {
                rendererCalls.push(['combat_resolved', ev]);
            },
        },
    };
    const sandbox = {
        console: { log() {}, warn(msg) { warnings.push(msg); }, error() {} },
        document,
        setInterval,
        clearInterval,
        setTimeout,
        clearTimeout,
    };
    vm.createContext(sandbox);
    const source = fs.readFileSync(
        path.join(__dirname, '..', '..', 'web_server', 'static', 'game_client.replay.js'),
        'utf8'
    );
    vm.runInContext(`${stripModule(source, 'game_client.replay.js')}\n;globalThis.__mod = { ReplayController };`, sandbox, {
        filename: 'game_client.replay.js',
    });
    return {
        controller: new sandbox.__mod.ReplayController(gameClient),
        gameClient,
        warnings,
        rendererCalls,
        stateFullStates,
    };
}

const snap = (id) => ({ game_state: { turn: id, tokens: {} } });

test('loadBattleLog accepts a bare array of snapshots', () => {
    const { controller, gameClient } = createHarness();
    controller.loadBattleLog([snap(1), snap(2), snap(3)]);
    assert.equal(controller.snapshots.length, 3);
    assert.equal(controller.cursor, 0);
    assert.equal(gameClient.replayMode, true);
    assert.equal(gameClient.stateManager.replayMode, true);
});

test('loadBattleLog accepts the { snapshots } and { states } envelopes', () => {
    const a = createHarness();
    a.controller.loadBattleLog({ snapshots: [snap(1), snap(2)] });
    assert.equal(a.controller.snapshots.length, 2);

    const b = createHarness();
    b.controller.loadBattleLog({ states: [snap(1), snap(2), snap(3), snap(4)] });
    assert.equal(b.controller.snapshots.length, 4);
});

test('loadBattleLog with unrecognized JSON warns and loads nothing', () => {
    const { controller, warnings } = createHarness();
    controller.loadBattleLog({ hello: 'world' });
    assert.equal(controller.snapshots.length, 0);
    assert.equal(warnings.length, 1);
});

test('seek clamps the cursor into [0, snapshots.length - 1]', () => {
    const { controller } = createHarness();
    controller.loadBattleLog([snap(1), snap(2), snap(3)]);
    controller.seek(99);
    assert.equal(controller.cursor, 2);
    controller.seek(-5);
    assert.equal(controller.cursor, 0);
});

test('seek applies the snapshot through stateManager.setFullState', () => {
    const { controller, stateFullStates } = createHarness();
    controller.loadBattleLog([snap(7), snap(8)]);
    assert.equal(stateFullStates.length >= 1, true);
    assert.equal(stateFullStates.at(-1).turn, 7);
    controller.seek(1);
    assert.equal(stateFullStates.at(-1).turn, 8);
});

test('seek preserves the board when the snapshot only carries the mutable layer', () => {
    const { controller, gameClient, stateFullStates } = createHarness();
    const board = { grid: [['keep']], width: 1 };
    gameClient.stateManager.gameState = { board, tokens: {} };
    controller.loadBattleLog([{ game_state: { turn: 1, tokens: { 9: {} } } }]);
    assert.deepEqual(stateFullStates.at(-1).board, board, 'board carried over from current state');
});

test('seek re-dispatches recorded events into the renderer FX pipeline', () => {
    const { controller, rendererCalls } = createHarness();
    const events = [
        { type: 'TOKEN_MOVED', token_id: 5, old_position: [1, 1], new_position: [2, 2] },
        { type: 'COMBAT_RESOLVED', attacker_id: 5 },
        { type: 'UNKNOWN_THING' },
    ];
    controller.loadBattleLog([{ game_state: { turn: 1 }, events }]);
    assert.deepEqual(rendererCalls[0], ['token_moved', 5, [1, 1], [2, 2]]);
    assert.equal(rendererCalls[1][0], 'combat_resolved');
    assert.equal(rendererCalls.length, 2, 'unknown event types are ignored');
});

test('setSpeed stamps aria-pressed on the pressed speed only', () => {
    const { controller } = createHarness();
    const speeds = [1, 2, 5].map((n) => {
        const btn = makeElement('button');
        btn.className = 'replay-speed';
        btn.dataset.speed = String(n);
        return btn;
    });
    controller.panel.__speedButtons = speeds;

    controller.setSpeed(5);
    assert.deepEqual(speeds.map((b) => b.getAttribute('aria-pressed')), ['false', 'false', 'true']);
    controller.setSpeed(1);
    assert.deepEqual(speeds.map((b) => b.getAttribute('aria-pressed')), ['true', 'false', 'false']);
});

test('togglePlay flips Play/Pause and stamps aria-pressed', () => {
    const { controller } = createHarness();
    controller.loadBattleLog([snap(1), snap(2), snap(3)]);
    const playBtn = controller.panel.querySelector('#replay-play');

    controller.togglePlay();
    assert.equal(playBtn.textContent, 'Pause');
    assert.equal(playBtn.getAttribute('aria-pressed'), 'true');

    controller.togglePlay();
    assert.equal(playBtn.textContent, 'Play');
    assert.equal(playBtn.getAttribute('aria-pressed'), 'false');
    assert.equal(controller.playing, false);
});

test('exit() detaches replay and hides the panel', () => {
    const { controller, gameClient } = createHarness();
    controller.loadBattleLog([snap(1)]);
    assert.equal(gameClient.replayMode, true);
    controller.exit();
    assert.equal(gameClient.replayMode, false);
    assert.equal(gameClient.stateManager.replayMode, false);
    assert.ok(controller.panel.classAdds.includes('hidden'), 'panel re-hidden');
});
