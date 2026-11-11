'use strict';

/**
 * state_manager.js — delta-merge and selection semantics.
 *
 * The server pushes fog-filtered state updates over WebSocket; applyDelta()
 * is the only thing reconciling them with what the client renders. These
 * tests pin the merge contract (null deletes, arrays replace, objects merge
 * recursively) and the selection notification behavior so a future refactor
 * can't silently re-enter the state-change callback on a no-op clear.
 *
 * state_manager.js has one import (game_client.constants.js) and no browser
 * globals at import or construction time, so it is imported directly — no
 * DOM stubs needed.
 *
 * Run with: npm run test:js   (or: node --test tests/js/)
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const url = require('node:url');

const STATIC_DIR = path.join(__dirname, '..', '..', 'web_server', 'static');
const mod = (name) => import(url.pathToFileURL(path.join(STATIC_DIR, name)));

let modPromise = null;
function load() {
    if (!modPromise) {
        modPromise = Promise.all([mod('state_manager.js'), mod('game_client.constants.js')])
            .then(([sm, constants]) => ({
                StateManager: sm.StateManager,
                mergeDelta: sm.mergeDelta,
                TurnPhase: constants.TurnPhase,
            }));
    }
    return modPromise;
}

test('mergeDelta deep-merges objects, replaces arrays, deletes on null', async () => {
    const { mergeDelta } = await load();
    const target = {
        turn_phase: 'MOVEMENT',
        board: { grid: [[{ cell: 1 }, { cell: 2 }]], width: 32 },
        tokens: { 7: { hp: 3, name: 'old' } },
        scores: [1, 2, 3],
        crystal: { neutral: true },
    };
    const result = mergeDelta(target, {
        turn_phase: 'ACTION',
        board: { grid: [[{ cell: 9 }]] },
        tokens: { 7: { hp: 2, name: null }, 8: { hp: 4 } },
        scores: [4, 5],
        crystal: null,
        added: 'yes',
    });

    assert.equal(result.turn_phase, 'ACTION');
    // Nested objects merge; the untouched key survives.
    assert.equal(result.board.width, 32);
    assert.deepEqual(result.board.grid, [[{ cell: 9 }]]);
    // Token fields merge per token; null deletes the key.
    assert.equal(result.tokens[7].hp, 2);
    assert.equal('name' in result.tokens[7], false);
    assert.deepEqual(result.tokens[8], { hp: 4 });
    // Arrays are replaced wholesale, never merged.
    assert.deepEqual(result.scores, [4, 5]);
    // null at the top level deletes the subtree wholesale.
    assert.equal('crystal' in result, false);
    assert.equal(result.added, 'yes');
});

test('mergeDelta replaces a non-object target with the delta', async () => {
    const { mergeDelta } = await load();
    assert.deepEqual(mergeDelta(null, { a: 1 }), { a: 1 });
    assert.equal(mergeDelta(5, { a: 1 }).a, 1);
});

test('setFullState records the perspective player and full state', async () => {
    const { StateManager, TurnPhase } = await load();
    const sm = new StateManager();
    sm.setFullState({
        game_state: {
            perspective_player_id: 'p1',
            current_turn_player_id: 'p2',
            // turn_phase deliberately absent
            tokens: { 1: { hp: 5 } },
        },
    });
    assert.equal(sm.localPlayerId, 'p1');
    assert.equal(sm.gameState.tokens[1].hp, 5);
    assert.equal(sm.turnPhase, TurnPhase.MOVEMENT, 'absent turn_phase defaults to MOVEMENT');
    assert.equal(sm.isLocalPlayerTurn(), false);
});

test('applyDelta merges into the stored state and deletes with null', async () => {
    const { StateManager } = await load();
    const sm = new StateManager();
    // Delta before the first full state must not throw or create state.
    sm.applyDelta({ tokens: { 1: { hp: 1 } } });
    assert.equal(sm.gameState, null);

    sm.setFullState({ game_state: { perspective_player_id: 'me', current_turn_player_id: 'me', turn_phase: 'MOVEMENT', tokens: { 1: { hp: 5 }, 2: { hp: 6 } } } });
    sm.applyDelta({ tokens: { 1: { hp: 4 }, 2: null }, turn_phase: 'ACTION' });
    assert.equal(sm.gameState.tokens[1].hp, 4);
    assert.equal('2' in sm.gameState.tokens, false, 'null removes the token from the map');
    assert.equal(sm.turnPhase, 'ACTION');
});

test('clearSelection only notifies when something was selected', async () => {
    const { StateManager } = await load();
    const sm = new StateManager();
    let calls = 0;
    sm.setChangeCallback(() => { calls += 1; });

    sm.clearSelection(); // nothing selected — must not notify
    assert.equal(calls, 0);

    sm.setSelectedToken(42, new Set(['3', '4']));
    assert.equal(calls, 1);
    sm.clearSelection();
    assert.equal(calls, 2);
    sm.clearSelection(); // already empty — must not notify again
    assert.equal(calls, 2);
});

test('isLocalPlayerTurn reflects the stored state', async () => {
    const { StateManager } = await load();
    const sm = new StateManager();
    assert.equal(sm.isLocalPlayerTurn(), false, 'no state yet');
    sm.setFullState({ game_state: { perspective_player_id: 'me', current_turn_player_id: 'me' } });
    assert.equal(sm.isLocalPlayerTurn(), true);
    sm.applyDelta({ current_turn_player_id: 'opponent' });
    assert.equal(sm.isLocalPlayerTurn(), false);
});

test('getToken looks tokens up by id from the stored map', async () => {
    const { StateManager } = await load();
    const sm = new StateManager();
    assert.equal(sm.getToken(1), undefined, 'no state yet');
    sm.setFullState({ game_state: { tokens: { 3: { owner: 'me' } } } });
    assert.equal(sm.getToken(3).owner, 'me');
    assert.equal(sm.getToken(9), undefined);
});
