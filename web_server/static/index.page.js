// Page-level glue for index.html: hostname autofill, player-count stepper,
// and mobile action-bar button wiring. Game logic lives in game_client.js.

(function () {
    'use strict';

    function autofillServerHost() {
        const hostInput = document.getElementById('server-host-input');
        if (hostInput && !hostInput.value) {
            hostInput.value = window.location.hostname;
        }

        const portInput = document.getElementById('server-port-input');
        if (portInput && !portInput.value) {
            // Prefer the explicit URL port; fall back to the protocol default.
            const defaultPort = window.location.protocol === 'https:' ? '443' : '80';
            portInput.value = window.location.port || defaultPort;
        }
    }

    function wirePlayerCountStepper() {
        const input = document.getElementById('create-game-players-input');
        const dec = document.getElementById('players-decrement-btn');
        const inc = document.getElementById('players-increment-btn');
        if (!input || !dec || !inc) return;

        const MIN = 2;
        const MAX = 4;

        dec.addEventListener('click', () => {
            const v = parseInt(input.value, 10) || MIN;
            input.value = Math.max(MIN, v - 1);
        });
        inc.addEventListener('click', () => {
            const v = parseInt(input.value, 10) || MIN;
            input.value = Math.min(MAX, v + 1);
        });
    }

    function handleMobileAction(action, btn) {
        if (btn) {
            btn.classList.add('active');
            setTimeout(() => btn.classList.remove('active'), 150);
        }

        if (navigator.vibrate) {
            try { navigator.vibrate(50); } catch (e) { /* ignore */ }
        }

        if (!window.gameClient) return;
        console.log('[MobileAction]', action);

        try {
            switch (action) {
                case 'deploy':
                    window.gameClient.toggleDeploymentMenu?.();
                    break;
                case 'camera':
                    window.gameClient.handleKeyDown?.({ key: 'camera_toggle' });
                    break;
                case 'end_turn':
                    window.gameClient.handleKeyDown?.({ key: 'end_turn' });
                    break;
                case 'reset':
                    window.gameClient.inputController?.resetToOverview();
                    break;
                case 'menu': {
                    const hud = document.getElementById('hud');
                    hud?.toggleAttribute('open');
                    break;
                }
            }
        } catch (e) {
            console.error('Error handling mobile action:', e);
        }
    }

    // First-person mode has no touch look/move controls yet — hide the View
    // button on touch-only devices so users can't enter a dead-end view.
    function updateCameraButtonVisibility() {
        const cameraBtn = document.getElementById('mobile-btn-camera');
        if (!cameraBtn) return;
        const touchOnly = window.matchMedia('(pointer: coarse)').matches &&
            !window.matchMedia('(pointer: fine)').matches;
        cameraBtn.classList.toggle('hidden', touchOnly);
    }

    function wireMobileActionBar() {
        const bar = document.getElementById('mobile-action-bar');
        if (!bar) return;

        updateCameraButtonVisibility();

        bar.querySelectorAll('.action-btn[data-action]').forEach((btn) => {
            const action = btn.dataset.action;
            // pointerdown covers mouse, touch, and pen uniformly.
            btn.addEventListener('pointerdown', (event) => {
                event.preventDefault();
                event.stopPropagation();
                handleMobileAction(action, btn);
            });
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        autofillServerHost();
        wirePlayerCountStepper();
        wireMobileActionBar();
    });
})();
