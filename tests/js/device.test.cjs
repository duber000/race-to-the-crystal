'use strict';

/**
 * game_client.device.js — device detection and profile heuristics.
 *
 * DeviceCapabilities decides quality settings and camera sensitivity from
 * the user agent, touch support, core count and screen size. UA parsing is
 * the kind of table that silently rots (someone adds an iPadOS desktop-class
 * UA and the game downgrades itself to low quality), so the detection table
 * is pinned here.
 *
 * device.js touches `window`/`navigator` at import time (it assigns itself
 * onto window), so it is evaluated in a node:vm context with explicit stubs
 * rather than imported. Only the two browser globals the module actually
 * reads are stubbed.
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

/** vm-realm objects have a different Object prototype; compare by value. */
const assertJsonEqual = (actual, expected) =>
    assert.equal(JSON.stringify(actual), JSON.stringify(expected));

const UA = {
    iPhone: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    iPad: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    androidPhone: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    androidTablet: 'Mozilla/5.0 (Linux; Android 14; SM-X710) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    desktop: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
};

function createHarness({ userAgent = UA.desktop, hardwareConcurrency = 8, maxTouchPoints = 0, width = 1280, height = 800 } = {}) {
    const sandbox = {
        console: { log() {}, warn() {}, error() {} },
        navigator: {
            userAgent,
            hardwareConcurrency,
            maxTouchPoints,
        },
        window: {
            innerWidth: width,
            innerHeight: height,
        },
    };
    vm.createContext(sandbox);
    const source = fs.readFileSync(
        path.join(__dirname, '..', '..', 'web_server', 'static', 'game_client.device.js'),
        'utf8'
    );
    vm.runInContext(`${stripModule(source, 'game_client.device.js')}\n;globalThis.__mod = { DeviceCapabilities };`, sandbox, {
        filename: 'game_client.device.js',
    });
    return new sandbox.__mod.DeviceCapabilities();
}

test('detectDeviceType classifies phones, tablets and desktops', () => {
    const iPhone = createHarness({ userAgent: UA.iPhone });
    assert.equal(iPhone.deviceType, 'mobile');
    assert.equal(iPhone.isMobile(), true);
    assert.equal(iPhone.isDesktop(), false);

    const iPad = createHarness({ userAgent: UA.iPad });
    assert.equal(iPad.deviceType, 'tablet');
    assert.equal(iPad.isMobile(), true, 'tablets count as mobile for quality scaling');

    const phone = createHarness({ userAgent: UA.androidPhone });
    assert.equal(phone.deviceType, 'mobile');

    const tablet = createHarness({ userAgent: UA.androidTablet });
    assert.equal(tablet.deviceType, 'tablet', 'Android without "Mobile" in the UA is a tablet');

    const desktop = createHarness({ userAgent: UA.desktop });
    assert.equal(desktop.deviceType, 'desktop');
    assert.equal(desktop.isMobile(), false);
    assert.equal(desktop.isDesktop(), true);
});

test('detectPerformanceProfile uses device class and core count', () => {
    assert.equal(createHarness({ userAgent: UA.iPhone, hardwareConcurrency: 6 }).performanceProfile, 'low');
    assert.equal(createHarness({ userAgent: UA.desktop, hardwareConcurrency: 4 }).performanceProfile, 'low');
    assert.equal(createHarness({ userAgent: UA.desktop, hardwareConcurrency: 8 }).performanceProfile, 'medium');
    assert.equal(createHarness({ userAgent: UA.desktop, hardwareConcurrency: 16 }).performanceProfile, 'high');
});

test('getRenderingConfig maps each profile to its quality tier', () => {
    const low = createHarness({ userAgent: UA.iPhone, hardwareConcurrency: 4 });
    assertJsonEqual(low.getRenderingConfig(), {
        hardwareScaling: 1.5,
        shadowsEnabled: false,
        particleMaxCount: 500,
        meshTessellation: 12,
        antialiasing: false,
    });

    const medium = createHarness({ userAgent: UA.desktop, hardwareConcurrency: 8 });
    assertJsonEqual(medium.getRenderingConfig(), {
        hardwareScaling: 1.0,
        shadowsEnabled: false,
        particleMaxCount: 1000,
        meshTessellation: 24,
        antialiasing: true,
    });

    const high = createHarness({ userAgent: UA.desktop, hardwareConcurrency: 16 });
    assert.equal(high.getRenderingConfig().particleMaxCount, 2000);
    assert.equal(high.getRenderingConfig().antialiasing, true);
});

test('getRenderingConfig falls back to medium for an unknown profile (no stack overflow)', () => {
    const dc = createHarness({ userAgent: UA.desktop, hardwareConcurrency: 16 });
    dc.performanceProfile = 'ultra'; // corrupt profile — default arm must not recurse forever
    assertJsonEqual(dc.getRenderingConfig(), {
        hardwareScaling: 1.0,
        shadowsEnabled: false,
        particleMaxCount: 1000,
        meshTessellation: 24,
        antialiasing: true,
    });
});

test('getCameraConfig uses touch-first settings on mobile, fine-grained on desktop', () => {
    const mobile = createHarness({ userAgent: UA.iPhone });
    const mobileConfig = mobile.getCameraConfig();
    assert.equal(mobileConfig.touchAngularSensibility, 5000);
    assert.equal(mobileConfig.angularSensibility, 3000);

    const desktop = createHarness({ userAgent: UA.desktop });
    const desktopConfig = desktop.getCameraConfig();
    assert.equal(desktopConfig.pinchPrecision, 0, 'pinch zoom disabled on desktop');
    assert.equal(desktopConfig.angularSensibility, 2000);
});

test('getUIScale only scales up on small mobile screens', () => {
    assert.equal(createHarness({ userAgent: UA.iPhone, width: 390 }).getUIScale(), 1.2);
    assert.equal(createHarness({ userAgent: UA.iPad, width: 900 }).getUIScale(), 1.0);
    assert.equal(createHarness({ userAgent: UA.desktop, width: 390 }).getUIScale(), 1.0);
});

test('detectTouchSupport keys off window/navigator touch surfaces', () => {
    assert.equal(createHarness({ maxTouchPoints: 5 }).touchSupport, true);
    assert.equal(createHarness({ maxTouchPoints: 0 }).touchSupport, false);
});
