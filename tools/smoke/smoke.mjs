// Headless smoke test for the vanilla WebGL2 renderer.
//
// Drives a full lobby flow with two browser contexts (two human seats)
// against side instances of the game server (HTTP_PORT=8081) and the web
// proxy (WEB_PORT=8001), then asserts the vanilla renderer came up and
// the scene renders without console errors. The side instances are
// spawned and torn down by this script; the live 8080/8000 servers are
// never touched.
//
// Prerequisites:
//   1. Built binaries: `make build` (or at least `race-server` and
//      `web_server/web_server` at the repo root / in web_server/).
//   2. Node deps: `npm install` (playwright) and
//      `npx playwright install chromium`.
//
// Usage:
//   node tools/smoke/smoke.mjs        # spawn side servers, run, tear down
//   make smoke                        # same, from the Makefile
//
// Env overrides:
//   SMOKE_BASE_URL     Use an already-running web instance instead of
//                      spawning one (e.g. http://127.0.0.1:8001).
//   SMOKE_GAME_PORT    Port for the spawned game server (default 8081).
//   SMOKE_WEB_PORT     Port for the spawned web proxy      (default 8001).

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const outDir = join(repoRoot, 'tools', 'smoke', 'out');
const spawnSideServers = !process.env.SMOKE_BASE_URL;
const gamePort = Number(process.env.SMOKE_GAME_PORT ?? 8081);
const webPort = Number(process.env.SMOKE_WEB_PORT ?? 8001);
const base = process.env.SMOKE_BASE_URL ?? `http://127.0.0.1:${webPort}`;

const failures = [];
const check = (label, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? ` — ${detail}` : ''}`);
  if (!ok) failures.push(label);
};

// --- side servers: spawn, wait for health, tear down on exit ---------------
const children = [];
function stopSideServers() {
  for (const child of children) {
    try {
      // SIGKILL: Go's default SIGTERM handling is fine, but this makes
      // teardown deterministic even if a server grows signal handling.
      child.kill('SIGKILL');
    } catch {
      // already gone
    }
  }
}
process.on('exit', stopSideServers);
process.on('SIGINT', () => process.exit(130));
process.on('SIGTERM', () => process.exit(143));

async function waitForHttp(url, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`timed out waiting for ${url}`);
}

try {
  if (spawnSideServers) {
    const serverBin = join(repoRoot, 'race-server');
    const webBin = join(repoRoot, 'web_server', 'web_server');
    for (const bin of [serverBin, webBin]) {
      if (!existsSync(bin)) {
        throw new Error(`${bin} not found — run \`make build\` first (or set SMOKE_BASE_URL)`);
      }
    }
    const server = spawn(serverBin, [], {
      cwd: repoRoot,
      env: { ...process.env, HTTP_PORT: String(gamePort), TURN_TIMEOUT_SECONDS: '300' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    const web = spawn(webBin, [], {
      cwd: repoRoot,
      env: {
        ...process.env,
        WEB_PORT: String(webPort),
        GAME_SERVER_URL: `http://localhost:${gamePort}`,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    children.push(server, web);
    server.stdout.on('data', (d) => process.stdout.write(`[server] ${d}`));
    server.stderr.on('data', (d) => process.stderr.write(`[server] ${d}`));
    web.stdout.on('data', (d) => process.stdout.write(`[web] ${d}`));
    web.stderr.on('data', (d) => process.stderr.write(`[web] ${d}`));
    await waitForHttp(`http://127.0.0.1:${gamePort}/api/games`);
    await waitForHttp(`http://127.0.0.1:${webPort}/`);
  }

  mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({
    args: [
      // SwiftShader fallback so WebGL2 works headless without a GPU.
      '--use-angle=swiftshader',
      '--enable-unsafe-swiftshader',
    ],
  });

  async function newClient(name) {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    const consoleErrors = [];
    const consoleWarnings = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
      if (msg.type() === 'warning') consoleWarnings.push(msg.text());
    });
    page.on('pageerror', (err) => consoleErrors.push(String(err)));
    await page.goto(`${base}/?renderer=webgl2`, { waitUntil: 'load' });
    await page.fill('#player-name-input', name);
    await page.click('#connect-btn');
    await page.waitForSelector('#lobby-browser-screen:not(.hidden)', { timeout: 10000 });
    return { context, page, consoleErrors, consoleWarnings };
  }

  const a = await newClient('SmokeA');
  const b = await newClient('SmokeB');

  // --- A: create a 2-player game
  await a.page.click('#create-game-btn');
  await a.page.click('#players-decrement-btn'); // 4 -> 3
  await a.page.click('#players-decrement-btn'); // 3 -> 2
  await a.page.fill('#create-game-name-input', 'SmokeTest');
  await a.page.click('#create-game-confirm-btn');
  await a.page.waitForSelector('#waiting-room-screen:not(.hidden)', { timeout: 10000 });

  const gameIdText = await a.page.textContent('#lobby-game-id');
  const gameId = gameIdText.replace(/Game ID:\s*/i, '').trim();
  check('game created, id present', gameId.length > 0, gameId);

  // --- B: join it
  await b.page.fill('#join-game-id-input', gameId);
  await b.page.click('#join-by-id-btn');
  await b.page.waitForSelector('#waiting-room-screen:not(.hidden)', { timeout: 10000 });

  // --- both ready up; A starts
  await b.page.click('#ready-btn');
  await a.page.click('#ready-btn');
  await a.page.waitForSelector('#start-game-btn:not(.hidden)', { timeout: 15000 });
  await a.page.click('#start-game-btn');

  // --- both enter the game
  await a.page.waitForSelector('#renderCanvas:not(.hidden)', { timeout: 15000 });
  await b.page.waitForSelector('#renderCanvas:not(.hidden)', { timeout: 15000 });

  // Let the render loop run a while so any per-frame errors surface.
  await a.page.waitForTimeout(4000);

  for (const [label, client] of [['A (host)', a], ['B (guest)', b]]) {
    const state = await client.page.evaluate(() => ({
      vanillaRenderer: window.gameClient?.vanillaRenderer === true,
      hasRenderer: !!window.gameClient?.renderer,
      hasCamera: !!window.gameClient?.cameraController,
      canvasVisible: !document.getElementById('renderCanvas').classList.contains('hidden'),
      turnPhase: document.getElementById('turnPhase')?.textContent ?? '',
    }));
    check(`${label}: vanilla renderer flag set`, state.vanillaRenderer);
    check(`${label}: renderer + camera constructed`, state.hasRenderer && state.hasCamera);
    check(`${label}: canvas visible`, state.canvasVisible);
    check(`${label}: turn phase populated`, state.turnPhase.trim().length > 0, `"${state.turnPhase}"`);
    check(
      `${label}: no console errors`,
      client.consoleErrors.length === 0,
      client.consoleErrors.slice(0, 3).join(' | ')
    );
    check(
      `${label}: no WebGL2 fallback warning`,
      !client.consoleWarnings.some((w) => w.includes('falling back to Babylon')),
      client.consoleWarnings.slice(0, 3).join(' | ')
    );
    const shot = await client.page.screenshot({ type: 'jpeg', quality: 60 });
    const shotPath = join(outDir, `shot-${label.startsWith('A') ? 'a' : 'b'}.jpg`);
    writeFileSync(shotPath, shot);
    check(`${label}: scene has non-trivial content`, shot.length > 30_000, `${Math.round(shot.length / 1024)} KB screenshot -> ${shotPath}`);
  }

  // HUD should show a running game phase for a fresh match
  const phase = await a.page.textContent('#gamePhase');
  console.log(`INFO  game phase shown in HUD: "${phase?.trim()}"`);

  await a.context.close();
  await b.context.close();
  await browser.close();
  stopSideServers();
} catch (err) {
  failures.push(String(err));
  console.error('ERROR during smoke run:', err);
  stopSideServers();
  process.exitCode = 1;
}

stopSideServers();

if (failures.length) {
  console.error(`\nSMOKE FAIL — ${failures.length} failure(s)`);
  process.exit(1);
} else {
  console.log('\nSMOKE PASS — vanilla WebGL2 path boots and renders cleanly');
  process.exit(0);
}
