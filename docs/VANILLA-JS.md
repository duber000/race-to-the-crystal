# Vanilla JavaScript + WebGL2 for the Web Client

> **Status**: Phase 0 and Phase 1 are complete. Phase 2 is complete —
> bloom, the crystal-effect animator, the marker-readability bump, god rays,
> GGX PBR with an analytic IBL, and the composite-pass cosmetics are built and
> verified in-browser.
> **The default flip shipped 2026-11-10 (decision gate, option A)**, and
> **Babylon.js was deleted the same day** (per maintainer instruction, ahead
> of the planned "first clean release" wait — the rollback hatch is gone and
> was never exercised). The vanilla WebGL2 renderer is the only renderer.
> **Cache headers shipped the same day** (`Cache-Control: no-cache` + 304
> revalidation on `/` and `/static/*`).
> **2026-11-10 (legibility pass, sixth verification):** floating combat text
> was rendering at half size (a billboard nominal-size bug, see §2) and is
> now legible at playing distance; health labels draw at nominal size as
> rounded pill chips; markers re-judged at zoom.
> **2026-11-10 (seventh verification):** the overview camera is now
> seat-relative — it sits behind the local player's deployment corner
> (α per SEAT_ALPHAS) with radius 1.1x the board diagonal, so no seat's
> tokens render behind the crystal, a HUD panel, or off-frame. The
> `#controls` blurb is capped to 480px (the full-width panel covered the
> bottom strip). Nothing in this document has been merged into a release
> — everything below was validated locally, in the browser, against a
> live game server.

This document records the argument for dropping Babylon.js, what has been
built and verified so far, the traps hit along the way, and what remains.

---

## 1. The premise

In October 2026 Paul Ford published ["The Web Is More Than
Enough"](https://ftrain.com/aboard-the-web-is-more-than-enough) (2026-10-21),
arguing that the browser's built-in platforms — Web Crypto, WebAssembly,
WebGL, Web Audio, SSE, offline storage — are vast, stable, and now far
cheaper to reach for than when they were built for Google-sized teams.
TinyLittleOffice shipped in 21 languages on Cloudflare's free tier.

The thesis gained a concrete proof point in the same thread: on the
[Hacker News discussion](https://news.ycombinator.com/item?id=50416456)
(2026-11-09), Simon Willison noted he builds features on three.js and
offline storage "multiple times per week", then took up socalgal2's comment
that "your LLM will do fine without it" and built a second, **no-libraries**
version of a Three.js Fabergé egg with plain JS and WebGL2. Per the
[HN comment](https://news.ycombinator.com/item?id=50416456) and the
[Claude transcript](https://claude.ai/share/e56d163e-2793-4677-aa11-191d5058b414)
of that session:

- three.js version: 77 KB, loads `three@0.170.0` from a CDN import-map
- vanilla version: ~98 KB, one self-contained file, hand-written PBR
  shader, shadow mapping, orbit controls, WebGL2-or-show-a-message fallback
- Reported results: whilenot-dev measured **120ms INP (vanilla) vs 504ms
  (three.js)**; Bengalilol reported **2.6 MB vs 173 KB** total downloads and
  better M1 frame rates; merelysounds notes some features were traded away
  (no glow, no glass transparency — faked with sparkles/inner glow)

The transferable lesson is not "WebGL2 is magic." It is: **for a bounded,
small, mostly-emissive stylized scene, one developer (or agent) can replace
a scene-graph library with a few thousand lines of plain JS + WebGL2 and get
a much smaller payload and faster page, at the price of owning all the
graphics code and losing a little visual gloss.**

### What our client actually spends on Babylon

Before any changes, the web client (`web_server/static/`, served with no
build step) shipped:

| Asset | Size | Gzip |
|---|---|---|
| `babylon.js` (Babylon.js 8.45.3, full UMD build) | 7.7 MB | **1.66 MB** |
| `babylon.gui.min.js` | 624 KB | 126 KB |
| `babylonjs.loaders.min.js` | 348 KB | 75 KB |
| First-party JS (25 files, 9,311 lines) | 325 KB | ~75 KB |

Findings from the survey (November 2026):

- The GUI and loaders were **never used** — zero first-party references, no
  `SceneLoader`/`.glb`/`.gltf`/`.obj`/`.stl` anywhere, no `BABYLON.GUI`.
  ~200 KB of gzip shipped for nothing.
- Two assets were fetched from `playground.babylonjs.com` at runtime: the
  `environment.env` IBL map and the `flare.png` particle sprite. A
  production dependency on a third-party CDN — a supply-chain and
  availability problem regardless of the migration.
- The first-party Babylon surface is ~223 `BABYLON.*` references across 11
  files (Vector3/Color3/MeshBuilder, StandardMaterial/PBRMaterial,
  GlowLayer, DefaultRenderingPipeline, VolumetricLightScatteringPostProcess,
  ParticleSystem, DynamicTexture, ArcRotateCamera, one ray-pick).
  Not used: GUI, loaders, shadow maps, physics, skeletons, WebGPU.
- First-party Babylon-coupled code was ~4,000 lines (~43% of client JS);
  the other 57% (DOM HUD, CSS, Web Audio, WebSocket, device detection) was
  already framework-free.

### The decision

Yes, we can convert — this codebase is an unusually good candidate (tiny
scene, no asset pipeline, DOM HUD, audio already raw Web Audio). Strategy:
stage it, keep Babylon as fallback, gate on a decision point.

---

## 2. What has been done

### Phase 0 — dead weight and third-party dependencies (done)

- Deleted `babylon.js` GUI/loaders scripts and vendored files (~200 KB gzip).
- Replaced the two `playground.babylonjs.com` assets:
  - `environment.env` → dropped IBL; gold frame and shard pillars got small
    emissive terms to stand in for it
  - `flare.png` → 64×64 radial-gradient `DynamicTexture` (local, no fetch)
- Fixed the board size: client `BOARD_CONFIG` said 24×24; server
  `shared/constants` says 18×18. The 3D view was framed for a board 6 cells
  wider than the one the server sends. Constants now 18×18.
- Fixed the server's `LOBBY_UPDATE` broadcast being unhandled — the client
  logged `Unknown message type: LOBBY_UPDATE` and dropped every lobby roster
  update. Added the case; verified the roster refreshes live.
- Silenced the crystal-effect replay: the fog/lightning/ghost effect and
  its sound re-fired on **every FULL_STATE echo** (10k+ duplicate log lines
  and blaring audio in one match). Both paths now replay only when the
  effect changes (`lastProcessedCrystalEffect`, like the mystery-event
  path).

### Phase 1 — vanilla WebGL2 spike, opt-in (done; default flip and deletion followed)

New `web_server/static/webgl2/` (~4,577 lines after the Phase 2 god-ray/PBR
pass, ~40 KB gzip), originally wired in behind `?renderer=webgl2`.
(2026-11-10: vanilla became the default and Babylon.js was deleted the
same day, see the decision gate in §4.)

| File | Lines | Role |
|---|---|---|
| `glmath.js` | 237 | vec3 + column-major mat4 (perspective/lookAt/multiply/invert/TRS + mat4TransformPoint) |
| `webgl2_core.js` | 170 | context, program/attrib management, VAO mesh builders (triangles/lines/points) |
| `webgl2_geometry.js` | 368 | ground/box/cylinder/UV/ico sphere/torus/quad/circle/square builders |
| `webgl2_camera.js` | 644 | spherical orbit overview + first person, wheel zoom, two-finger pinch/pan, focus/transition/FP smoothing |
| `webgl2_renderer.js` | 2,301 | `VanillaRenderer3D` — drop-in for `Renderer3D` (duck-typed), same public interface |
| `webgl2_textures.js` | 85 | canvas-generated textures (grid, health labels, soft-circle billboards) |
| `webgl2_bloom.js` | 402 | half-res bloom + god rays + composite (vignette, grain) — Phase 2 |
| `webgl2_crystal_effects.js` | 370 | fog/ghosts/lightning/whirlwind animator — Phase 2 |

Total ~4,577 lines (Phase 2 total ~882 lines over the Phase 1 spike).

Reached via `game_client.modules.js` → always the vanilla path. Since
2026-11-10 there is no flag and no fallback: if the WebGL2 renderer throws
during init the client shows a fatal alert (WebGL2 required) instead of
silently degrading — the Babylon fallback was deleted with Babylon.js.

**Verified in-browser (Chrome), page by page:**

- Scene renders: board grid/cage, hex tokens, health labels, generators,
  crystal + gold wireframe cage, mystery torus rings, laser beams,
  objective pips, hover/valid-move/attack/threat indicators, selection
  glow (white emissive + 1.25 scale), star field, ambient/explosion/
  confetti particles, camera shake.
- Interaction works through the real event path: pick ray → cell, select,
  valid moves populate, click to move, server accepts, token eases to the
  cell, HUD updates, deploy flow (menu → canvas click → `TOKEN_DEPLOYED`).
- Sounds (AudioManager unchanged), timer, fog-of-war filtering, spectate
  mode (seat-cam), `?renderer=webgl2` + Babylon fallback both exercised.
- Multi-turn AI-vs-AI play: combat, deployments, turn timer, crystal effect
  triggers, all flowing correctly.

**Observed (2026-11-09): a win over the wire end-to-end.** A scripted
HTTP_AI seat won a side-instance match by disabling a generator and banking
crystal charge to 80/80 at turn 23 of `SpectateScripted2` (verified two
ways: the HTTP action response itself returned
`GAME OVER - ScriptedAI2 won the race to the crystal!`, and the spectator
client logged `Game won by ScriptedAI2`), the `GAME_ENDED` event fired and
the vanilla renderer played the victory effect (confetti burst + crystal
pulse — screenshotted), and the browser-native `alert()` fired and was
accepted. Prerequisite find: the HTTP action path broadcast a `GAME_OVER`
frame the client does not handle, so the winner announcement silently
dropped for HTTP-driven seats — see §3. Crystal effects observed firing
over the wire twice (see Phase 2).

**Two silent white-box renderer bugs found and fixed:**

1. A soft white curved streak across the sky — UV-sphere star dome's pole
   pinch stretched texture to a smear. Replaced the sphere with a static
   point-sprite dome (250 tiny points, no texture, no poles).
2. `gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true)` was leaked to all
   subsequent texture uploads; would have rendered health-label text upside
   down. Each upload now flips then restores.

### Game-side bugs found while proving it played

The renderer worked before the game did. Three pre-existing defects had to
be fixed for the AI to function at all (see §3 for the shared cause):

- `game/ai_strategy.kuki` `resolveAction` panicked (`random.Choice` of an
  empty list) when a DeployAction had no valid positions — every AI died on
  turn 0. Now returns `ChosenEndTurn{}`.
- `ChooseAction` never reached `ChosenEndTurn{}` correctly — the AI chose
  END_TURN forever because the action parser dropped every field (see §3,
  "JSON / wire decoding"). With the parser fixed, two aggressive AIs play
  a full, combative match.
- `server/http_handler.kuki` and `server/ws_endpoint.kuki` read
  `max_players` as `is int` — JSON numbers decode as `float64`, so the
  lobby stepper was ignored and **every game was a 4-player one**. Now
  accepts `int`/`int64`/`float64` (matches `action_validation.kuki`).

`kukicha check ./game ./server ./client/ai` passes; `make test` passes;
`kukicha fmt --check .` clean. (Note: `game/main.go` et al. are
gitignored; `make test` regenerated everything it needed.)

### Phase 2 — visual parity (built and verified in-browser)

Built since the Phase 1 spike, including the verification pass in Chrome
(November 2026):

- **Bloom** (`webgl2_bloom.js`) — half-res separable gaussian (9 taps,
  two ping-pong iterations) composited additively over the scene, plus a
  soft vignette and a whisper of film grain in the same pass. The scene
  renders into a full-res FBO (RGBA16F where `EXT_color_buffer_float` is
  available — it is, in Chrome — RGBA8 otherwise) with a depth
  renderbuffer. `?bloom=0` opts out entirely and draws straight to the
  canvas, identical to the Phase 1 path. Verified live: toggling
  `renderer.bloomPass` off at runtime flattens the beams and generators
  visibly; the FBO comes up complete, no shader or link errors are
  logged.
- **Crystal-effect animator** (`webgl2_crystal_effects.js`) — the Babylon
  `CrystalEffectAnimator` ported against the vanilla renderer's
  primitives. Exercised in-browser, all four effects: fog (16 radial
  smoke billboards — seen hazing the whole board), whirlwind (8 spiral
  point emitters — cyan spiral streams seen spreading), damage boost
  (jagged sky→token bolt + additive flash sphere + spark burst — a forced
  strike renders, the flash sphere catches the bloom knee), phantom
  enemies (5 ghost billboards — object emission verified: correct
  alpha/color/texture; hard to make out at overview distance). The
  trigger path itself (`checkCrystalEffectTrigger`) is unchanged and
  replay-guarded; not yet observed firing end-to-end from the wire — the
  "whoosh" heard during verification was the selection sound, not an
  effect. Sounds flow through the unchanged `AudioManager`.
- **Marker readability** — valid-move/attack fill quads raised from 0.16
  to 0.35 alpha, drawn additively with brightness 1.8; threat-hover
  squares bumped to match. Judged at zoom 2026-11-10 (sixth pass):
  legible on open canvas; the `0.35` alpha is inert under `ONE/ONE`
  additive blending (brightness 1.8 drives the fill) — see §2 (sixth
  pass). HUD-panel occlusion of the deploy corner is a §5 question.
- **God rays** (`webgl2_bloom.js` → `FRAG_GODRAYS`) — the stand-in for
  Babylon's `VolumetricLightScatteringPostProcess`. When the crystal is
  visible, the bright pass (no extra render) is radially blurred toward
  the crystal's screen-space position (48 taps, decay 0.955, quadratic
  falloff comes from the decay) into a half-res texture, then softened
  with the same separable 9-tap blur bloom uses, and added additively in
  the composite. The crystal's UV-space position comes from projecting
  the hub world position through `mat4TransformPoint(proj*view, …)`;
  skipped (strength 0, dummy texture bound) when the crystal is behind
  the camera, off-screen by a wide margin, absent, or `?rays=0`. Both
  toggle and strength are live-tweakable from the console
  (`renderer.bloomPass.raysStrength`, default 0.9). Verified in-browser:
  shafts fan out from the crystal across the board and sky; raw radial
  accumulation read as harsh angular wedges before the extra blur, and
  0.6 read as too subtle — 0.9 is the settled default. NOTE: the rays
  are uniform along a shaft (occlusion is not modelled — no depth
  texture exists on the scene FBO), which is acceptable at this scene
  scale; foreground geometry does not cast ray shadows.
- **GGX PBR + analytic IBL** (`webgl2_renderer.js` → `FRAG_LIT`) —
  Lambert/Blinn-Phong replaced with GGX/Smith/Schlick direct lighting
  and an environment computed per-fragment from an analytic sky (warm
  dusty horizon, deep-blue zenith, near-black nadir, sun disk + forward
  scatter lobe, warm horizon band on the sun's azimuth). No environment
  texture, no cube map, nothing fetched. Diffuse IBL samples a
  sun-softened gradient (`skyAmbient`); specular IBL uses
  `skyColor(reflect(-v, n), roughness)` with roughness-blurred sun
  (`focus = mix(600, 5, roughness)`) and a Schlick-roughness Fresnel.
  Materials are now `metallic`/`roughness`: generators 0.85/0.3, tokens
  0.55/0.38, phantoms 0.3/0.5. The old emissive-heavy look survives —
  the generators' orange emissive is kept on top of the metal (it reads
  as "hot coil", and the bloom knee loves it). **Decision on the gold:
  kept the emissive fake.** The cage is additive line geometry, not a
  lit metal, so PBR would not have touched it anyway; the warm horizon
  band does wonders on the generators and tokens, but the cage lines
  with their emissive gold stay exactly as they were. Verified
  in-browser: generator pillars pick up a proper warm/cool gradient and
  sun streak instead of flat orange; tokens read as shaded hex solids;
  zero shader compile/link errors in Chrome or SwiftShader, and
  `make smoke` passes (the boot gate now exercises both new shaders).
- **Two more silent white-box bugs found by reading, then fixed:**
  3. `VERT_UNLIT` declared `aUV` at location 1 — the *normal* attribute's
     location (fixed VAO layout is 0=position, 1=normal, 2=UV), so every
     unlit draw read the normal vector as its UVs. `aUV` is now location 2.
  4. The floating-text texture upload leaked `UNPACK_FLIP_Y_WEBGL`
     (same global-state trap as the Phase 1 health-label bug). Each
     upload now flips then restores.
- **Fifth silent white-box bug found, then fixed (2026-11-10, legibility
  pass).** `_drawBillboard` scaled the unit quad (±0.5) by `width/2`, so
  every billboard — health labels, floating combat text, fog puffs,
  ghosts — drew at **half its nominal size**. The floating damage popup
  ("-7") read as a ~2-unit speck on the token face at playing distance,
  invisible past ~150 units out. Fixed by drawing billboards at nominal
  size; floating text re-canvased (256×128, `bold 88px sans-serif`,
  9px stroke, quad 13×6.5); health labels became rounded pill chips with a
  thin cool-white stroke; fog puffs were retuned from 42–80 to 21–40 units
  (the size they were actually rendering at — the verified fog look is
  unchanged); ghosts, which were never tuned ("hard to make out at
  overview distance"), now render at their intended 15 units.
- **Cosmetics (chromatic aberration + unsharp mask)** — both live in the
  composite pass of `webgl2_bloom.js`: radial CA (R/B shift against G,
  quadratic toward the corners, `?chroma=0` to disable, default 0.006) and a
  4-tap unsharp mask (`?sharpen=0` to disable, default **0.25** — lowered
  from 0.4 on 2026-11-09; 0.4 accentuated the 1–2px neon grid lines).
  Film grain (0.045) and the vignette (0.55) have been in the same pass
  since the bloom landed. Decision recorded in the fourth verification
  pass, below.

Re-verified after the changes: page loads clean, full match plays, pick →
select works through the real event path (valid moves populate, the
"MOVEMENT • 3 targets" hint appears, selection glow shows), turn timer,
fog-of-war opponent filtering, and the AI seat all behave.

**Verification notes (second pass, as a spectator):**

- **Seat-cam spectating works end-to-end.** `SPECTATE` with `follow=player_0`
  binds the connection, the vanilla renderer comes up, and the fog-filtered
  stream flows. Nice trick for watching a match conclude without a seat.
- **A crystal effect observed firing over the wire**: on connect, the fresh
  client logged `Crystal effect triggered: 3 for player player_0` (damage
  boost replayed once from the persisted `last_triggered_crystal_effect`,
  replay-guard intact) and played the matching sound. The forced-trigger
  path was already proven; this closes the loop.
- **Zoom is glued to the board center.** Wheel dollies the radius but the
  target never leaves the crystal — past ~radius 110 the crystal fills the
  frame. Pan/drag moves it (map-style grab pan), and direct spherical edits
  (`camera.target/alpha/beta/radius`) work for a precise camera. Noted:
  the target stays centered on the crystal (by design); the azimuth is
  now seat-relative instead of the fixed Babylon-matching pose — see the
  seventh verification pass.
- **First-person mode toggles (V) and survives WASD**: with no controlled
  token, `W` prints the "No token controlled! Press TAB to cycle tokens"
  banner. WASD movement with a controlled token and TAB cycling remain
  untested.
- **Health labels are crisp quads** — glyph legibility at zoom verified
  2026-11-10 (sixth pass): upright, crisp at radius ≥ 150; unreadable at
  full-board radius (by design). Superseded same day by the nominal-size
  billboard fix; labels now render 2× larger (see §2, fifth/sixth pass).
- **In-browser spectating is wired end-to-end (fixed and verified).** Two
  defects stood between the lobby browser and the seat-cam view, both
  fixed: (1) WS `LIST_GAMES` returned only joinable lobbies, so the
  `IN_PROGRESS` Spectate button never rendered — it now mirrors the HTTP
  `/api/games` list (available + in-progress); (2) the seat-chooser overlay
  sat at a lower z-index than the always-on-top HUD (100) and then the
  fixed lobby panel (2000), so clicks hit those layers instead of the
  seat buttons — now 2100, below the victory modal (3000) and toast
  (9999). Verified with a side instance (`HTTP_PORT=8081` game server +
  `WEB_PORT=8001 GAME_SERVER_URL=http://localhost:8081` web proxy):
  lobby browser lists the IN_PROGRESS match → SPECTATE → seat chooser →
  click "VerifyAI HTTP_AI" → spectator view streams for that seat. Note:
  the page's CSP (`default-src 'self'`) blocks a :8000 page from opening
  `ws://localhost:8081` directly, so side-instance verification must go
  through a side web proxy, not a direct port.

**Verification notes (third pass — god rays + PBR/IBL, November 2026):**

- Side-instance flow again (8081 game server + 8001 web proxy). Fresh
  2-player game against a detached `aggressive` AI on the side server;
  the human started PLAYING with auto-deployed tokens. Console clean:
  no shader compile/link errors, no fallback warning — the new `FRAG_LIT`
  and `FRAG_GODRAYS` come up on the first paint in Chrome and under
  SwiftShader (`make smoke` re-run for the fallback path).
- **God rays A/B.** `?rays=0` vs default vs live-tuned
  `renderer.bloomPass.raysStrength` (0.6 / 0.9 / 1.1). Raw accumulation
  (no softening blur) produced hard angular wedges — rejected; 0.6 with
  the extra 9-tap H/V soften read as "mystery haze", not rays — too
  subtle; **0.9 ships** as the default. The rays are most legible over
  the sky above the crystal, fanning up-out from it; they do not
  re-light the board.
- **PBR look.** Generator pillars read as polished warm-orange metal
  (sun streak + horizon gradient reflect); tokens read as shaded hex
  solids rather than flat player-color slabs; the crystal and cage are
  unchanged (unlit/line geometry, deliberately). The emissive terms stay.
- **No perf red flags observed** at 1354×728 (high-performance profile),
  but the rays add two half-res passes (radial accumulate + H/V soften)
  and the composite reads a third texture — worth a frame-time check on
  a low-end device before the default flip, together with the existing
  bloom question. *(Done — see fifth pass below: vsync-locked at 6x CPU
  throttle, bloom+rays below timing noise.)*

**Verification notes (fourth pass — cosmetics tuning, November 2026):**

- Side-instance flow again (8081 game server + 8001 web proxy) against the
  `CosmeticVerify2` game, `?renderer=webgl2&nocache=5`; `bloomPass.sharpen`
  / `bloomPass.chroma` flipped live from the console between screenshots.
  Full-page JPEGs (q60, ~270–290 KB at this 2257×1214 viewport) and small
  crops (10–46 KB) stayed far under the inline-media budget; no full-size
  PNGs were read. (The session that preceded this one ended on
  `airlock_error: inlined media exceeds the 33554432 byte total limit`
  after inline PNGs + three full reads — see §3.)
- **Sharpen A/B** (chroma held at 0.006): 0 / 0.25 / 0.4 screenshotted and
  compared on a thin-grid crop. Grid-line Laplacian p99: **0 → 159,
  0.25 → 180, 0.4 → 191**; 0.4 visibly accentuates the thin neon lines
  ("slightly too crisp for thin lines"), 0 flattens the micro-contrast.
  **Decision: ship 0.25** (`webgl2_renderer.js` + `webgl2_bloom.js`;
  `?sharpen=0` remains the opt-out).
- **Chroma A/B** (sharpen held at 0.25, 0 vs 0.006): the corner regions are
  behind the DOM HUD (unaffected, as expected — HUD text never touches the
  composite); the only visible split is a faint ~1–2px R/B fringe on
  sub-pixel stars at the frame periphery. Beam/generator crops are
  indistinguishable by eye, and bright mid-edge pixels skew ≤2.5% in
  R−B (|R−B| 140.8 → 144.4) — nothing the cyan board can show.
  **Decision: keep 0.006** — it matches the Babylon DefaultRenderingPipeline
  look and the grain/vignette photo-vibe, and costs two scene fetches in a
  pass that already runs. `?chroma=0` remains the opt-out.
- The new persisted defaults (chroma 0.006, sharpen 0.25) were confirmed on
  the wire from both :8000 and the :8001 side instance — a fresh page load
  gets the new constants (the renderer only constructs after joining a
  game, so the check was done against the served files, not a live
  `bloomPass`).

**Verification notes (fifth pass — low-end frame time, 2026-11-10):**

- Steady-state rAF frame times measured on the host seat of a headless
  2-player game (side instances on 8081/8001, Playwright-driven, 10 s
  samples), hardware GL via ANGLE→Vulkan on Mesa ANV (Intel MTL iGPU).
  **Headless Chromium defaults to SwiftShader — it had to be forced off**
  (`--use-gl=angle --use-angle=vulkan`); left alone, every run reports a
  ~350 ms frame and looks like a low-end disaster (see below), which is
  the software rasterizer, not the device. CPU throttled 6x via CDP
  `Emulation.setCPUThrottlingRate` (the Lighthouse-style low-end stand-in;
  CDP cannot throttle the GPU).
- **60 fps vsync-locked in all three configs** (bloom+rays default,
  `rays=0`, `bloom=0`) at both 1x and 6x CPU, zero frames > 33.3 ms, zero
  reported long tasks — and still locked at **2000×1125 (2.25 MP)**, so the
  passes are not fill-bound at this scene's complexity either. Bloom/rays
  overhead is below vsync quantization noise: p99 differs by ≤ 0.5 ms
  between configs (19.2 / 19.6 / 19.1 ms at 6x). JS thread is not the
  bottleneck even at 6x.
- **Software-GL floor** (SwiftShader, first probe): default 353 ms,
  `rays=0` 232 ms, `bloom=0` 40 ms. Bloom is the expensive pass; god rays
  are the second. Both are imperceptible on hardware GL at this
  resolution, but if a genuinely weak GPU ever needs it, `?bloom=0` exists.
- Caveats: idle steady-state scene (ambient particles / crystal pulse
  animate; no camera input or token easing during sampling); vsync hides
  sub-frame headroom; Intel MTL is a modest iGPU, not a low-end phone SoC
  — but nothing here suggests bloom needs to come off the default.
  `make smoke` remains on SwiftShader and is unaffected (it asserts boot,
  not frame rate).

**Verification notes (sixth pass — legibility at zoom, 2026-11-10):**

- Side instance again (`HTTP_PORT=8081` + `WEB_PORT=8001` proxy), fresh
  2-player game vs. a detached `aggressive` AI, viewport 1354×728 (canvas
  2257×1214 at DPR 1.667). Camera posed by direct spherical edit
  (`cameraController.camera.target/alpha/beta/radius`) — no camera math in
  the test; grid cells resolved by the page's own `pickGridCell` (the
  smoke-test pattern). Screenshots taken as q60 JPEGs with `filePath`;
  crops via `magick` for pixel-level checks.
- **Health labels**: upright (flip_y fix re-confirmed — glyphs read
  "10hp" right-side up), crisp at every radius ≥ 150, and now full size
  (38 % larger than the half-sized billboards of the Phase 2 state). The
  black square behind the glyphs became a rounded pill with a thin
  cool-white stroke (`createHealthLabelTexture`) so the selected white
  token no longer wears a harsh black bar. Unreadable nan-text at
  full-board radius — by design (labels are a close-up readout).
- **Floating combat text** (forced via `renderer.showFloatingText(...)`
  with life pinned — the built-in 1.2 s TTL expires before a DevTools
  round-trip can screenshot; "-7"/"-12" spawned over cells 0 and 1):
  **was a ~2-unit speck** before the fifth white-box fix, now a
  stroke + fill glyph ~4.5 units tall — clearly readable against the
  cyan token faces and against the crystal backdrop.
- **Marker readability at zoom (the §4 item 1 follow-up)**: the
  valid-move green fill + square outline render legibly on open canvas —
  saturated neon, as tuned. Two findings that are *not* canvas defects:
  (a) additive draws blend `ONE/ONE`, so the fill's `alpha: 0.35` is a
  **no-op** — brightness 1.8 is what sets intensity (it clips to saturated
  green over anything bright); (b) the HUD panels are DOM layers above the
  canvas — the info panel (`#hud`, `rgba(0,0,0,0.7)`) and `#controls`
  (`rgba(0,0,0,0.7)`) dim everything beneath them. At 1354×728 the deploy
  corner (own tokens + their valid-move markers) renders behind the left
  panel, and one marker (cell `1,1`) sits fully under `#controls` at this
  camera pose. Marker tuning is sound; the occlusion is a HUD/framing
  question (see §5). **Resolved same day**: both panels thinned to
  `rgba(0,0,0,0.45)` (maintainer's choice, option "thin the panels").
- The fog/ghost billboards were part of the half-size bug; fog was
  retuned to its previously-rendered effective size (no look change);
  ghosts now render at nominal 15 units. The lightning bolt (line
  geometry) was never billboard-sized.
- **HUD panel thinning (2026-11-10, option chosen by the maintainer):**
  `#hud` and `#controls` backgrounds lowered from `rgba(0,0,0,0.7)` to
  `rgba(0,0,0,0.45)` so the board — and the deploy corner with its
  markers — reads through the panels. Verify HUD text remains legible on
  your display; the panels are otherwise unchanged (borders, layout,
  z-index).
- `make smoke` re-run clean after the fix (own side servers torn down;
  the gate spawns its own): boot, render, and the two-seat move/end-turn
  interaction gate all pass with zero console errors.

**Verification notes (seventh pass — seat-relative overview camera, 2026-11-10):**

- **The diagnosis had to be measured, not assumed.** The default pose
  (α = π/4, beta 60°, radius 0.8 × diagonal ≈ 650, fov 40°, target board
  center) projects the four deployment corners asymmetrically: the P0/P1
  corners land inside the crystal/cage silhouette (P0 renders *on top of
  the crystal* — all three host tokens nested in the cage wireframe,
  confirmed visually), P2 lands behind the info panel (x ≈ 87 px), and
  P3 lands off the bottom edge (y ≈ 970 px, 240 px past a 728 px canvas)
  behind `#controls` — a full-width (~1140 px) panel whose unbroken
  blurb sentence set its width. Only P1 got a clear view. §5 had called
  the symptom "corners crop at ~1:1 aspect"; at 1354×728 the same
  asymmetry applies with the corners merely projected, not cropped.
- **Fix: the overview azimuth is per seat.** The camera sits behind the
  local player's deployment corner (`SEAT_ALPHAS` in `webgl2_camera.js`:
  0=NW 225°, 1=NE 135°, 2=SW 315°, 3=SE 45° — matching the corners in
  `game/board.kuki`). `focusOn` uses the same azimuth. Spectators get
  the followed seat's azimuth for free (`perspective_player_id` = the
  followed seat); a missing/unparsable id falls back to the SE pose.
- **Radius 0.8 → 1.1 × diagonal (≈ 650 → ≈ 896).** The near corner at
  the 60° tilt needs radius ≈ 900 to enter the frame (it was projected
  off the bottom for every seat at 0.8 — P3 was unplayable today). At
  1.1, every seat projects symmetrically: own corner at y ≈ 703, side
  corners at y ≈ 364, far corner at y ≈ 209, crystal at y ≈ 364 at
  1354×728. Cost: ~28 % smaller board scale (acceptable; labels and
  markers were re-verified legible).
- **`#controls` blurb capped at 480 px** (bottom strip usable below the
  wrapped text; near corner at x ≈ 677 clears the 480 px panel).
- **First FULL_STATE ordering**: `handleFullState` now applies the state
  before dispatching `IN_GAME` (the seat arrives as
  `perspective_player_id`), with an explicit `updateGameState` push after
  module init so the freshly built renderer sees the already-applied
  state. The first rendered frame already uses the seat-relative pose —
  no camera snap.
- Verified in-browser on a fresh side instance (2-player game vs. an
  aggressive `aggressive` AI): player_0 seats at α = 225°, radius 896;
  own tokens framed bottom-center, fully visible above the capped panel,
  labels intact; valid-move markers legible (their green outlines alias
  at glancing near-edge angles — inherent to 1 px line rendering, the
  same accepted trade-off as the neon grid). Console clean;
  `make smoke` passes end-to-end (move + end-turn gates, zero errors).

---

## 3. Gotchas

### JSON / wire decoding (the big one)

This stack — Go's `jsonv2` used under the hood everywhere including the
stdlib fetch decoder — has two properties that break naive assertions:

1. **Numbers decode as `float64`.** `if x is int as v` never matches a JSON
   number. Silently. Three unrelated bugs turned out to be exactly this:
   the AI's action parser dropped all numerics, the lobby's `max_players`
   silently stayed at 4, and any hand-rolled `is int` on a wire is a landmine.
2. **Arrays decode as one-level `[]any`.** `[][]int` from the wire simply
   does not match `is list of list of int as v` — you must walk one level at
   a time (`[]any` → each element `[]any` → each element a float). The old
   parser's nested assertion never matched and silently dropped
   `valid_destinations`/`positions`.

Rules for this codebase:

- Decode one level at a time; convert with `stdlib/cast` (`cast.ToIntOr`).
- Accept `int`/`int64`/`float64` anywhere a JSON number lands (see
  `action_validation.kuki` for the pattern; replicate it).
- Never trust a bare `is` assertion on a wire value. Ask the probe
  program (`/tmp/opencode/probe/main.go` pattern) if the types confuse you.

### The game package

- `//` is **not a comment** in Kukicha — it's two division operators and a
  syntax error. Use `#`. (Cost me a silently-broken `game/` once;
  `kukicha check ./client/ai` then blamed the importer for a missing type.)
- `kukicha check` errors surface at the **importer**, not the culprit.
  "undefined type X in package gamepkg" against `client/ai/` or `learn/`
  usually means a syntax error inside `game/` — fix `game/` first.
- A variant enum cannot have methods. Use free functions.
- Empty `when` arms are not allowed (`syntax/empty-arm`).
- `map` iteration order is random. Anything order-dependent (seat order,
  colors, turn order) must go through the explicit ordered helpers
  (`orderedPlayerIds`, `orderedPlayers`, `PlayerColorIndexes`). This has
  caused real defects; keep the discipline.
- Tests are `*_test.kuki` and are only transpiled by `kukicha brew`
  (`make test`). `go test ./...` alone runs stale generated code.

### End-of-game wire messages

- **The end of a match is announced twice — a `GAME_ENDED` event on the
  event stream, and a `GAME_WON` message with the winner's name.** Both are
  required: the client's victory effect keys off the event
  (`handleGameEnded → triggerVictoryOnce`), and the announcement/`alert()`
  keys off the message (`handleGameWon`). This was nearly missed: the
  **HTTP action path** used to broadcast a different message entirely —
  `{"type":"GAME_OVER","winner":…}` with no name — which every client
  (vanilla and Babylon alike) dropped with `Unknown message type:
  GAME_OVER`, so HTTP-driven seats (all AI clients, and any scripted HTTP
  player) got the confetti but never the winner announcement. Fixed
  2026-11-09: both end-of-game paths now broadcast one shared frame via
  `session.winnerBroadcastFrame()` (`server/game_coordinator.kuki`). WS
  and HTTP seat behaviour is now identical; the alert() path is verified
  live. If you touch end-of-game broadcasting, keep both paths identical.
- **Unattended AI-vs-AI matches never conclude.** All three bundled AI
  strategies converge on the crystal and annihilate both armies; no
  generator is ever captured (zero captures across three consecutive
  aggressive/defensive matches, incl. one to turn 76 with 0 tokens alive
  on both sides), nothing banks charge, and the server has no turn cap —
  the match idles forever in PLAYING. Expect this whenever you wait for a
  GAME_WON: it will not come from AI-vs-AI alone. The verification pass
  used a scripted HTTP_AI seat (a Python driver parked two tokens on a
  generator and held it until charge hit 80/80) to force a real,
  over-the-wire win.

### The web client

- **No build step, no bundler, no cache headers or hash busting.** Every
  page load heuristically re-fetches modules, but Chrome's heuristic caching
  can serve stale JS with no error. If the page behaves like the old code,
  hard-reload (`ignoreCache: true` in DevTools terms, or Ctrl+Shift+R).
  Verify with a fresh `?param` if in doubt.
- The game board is **18×18** (server `shared/constants`). Any client that
  assumes otherwise produces an oversized cage and an off-center camera.
- Fog of war is real: invisible enemy tokens are absent/masked and have
  `position: null`. Every `token.position[0/1]` read needs a null check.
  This is why spectators see "Tokens: 0/20" for the opponent — expected,
  not a bug.
- The server's `last_triggered_crystal_effect` **persists** until the next
  effect fires. Any code that reacts to it on every update (the Babylon
  client does the same thing) will replay the effect + sound hundreds of
  times per match. Guard on change, like the mystery-event path.
- Spectator is seat-cam: one seat per connection, union-of-vision across
  seats can reconstruct the board. Fine for casual play; not an integrity
  boundary.
- **Full-res screenshots blow the upstream media budget.** The canvas is
  devicePixelRatio-scaled (e.g. 728×629 CSS at DPR 1.667 → 1213×1048
  device pixels), and Chrome DevTools screenshots of it saved as inline
  PNG run ~3.5 MB each. Ten of those in one session exceed the
  `airlock_error: inlined media exceeds the 33554432 byte total limit`
  budget, and every subsequent upstream call then fails. Take them with
  `format: "jpeg"`, `quality: 60` and an explicit `filePath`, or
  quality 25 for a quick check; prefer text snapshots over images
  otherwise. This error ended two Phase 2 sessions. Note the budget is
  cumulative across the whole session, not per image: the second one
  tripped right after reading two ~280 KB JPEGs on top of an already-large
  transcript — so even q60 JPEGs are only safe while the running total is
  well under 32 MB, and small crops (10–46 KB) are the robust pattern
  for A/B comparisons. Cropping out a HUD or grid region and upscaling it
  (`magick in.jpeg -crop ... +repage -resize ... out.jpeg`) is enough
  fidelity for tuning calls and costs kilobytes.
- **A full lobby is invisible to the list endpoints, and join 400s with no
  explanation.** `/api/games` and WS `GAME_LIST` only show lobbies with a
  free seat (WAITING) or already in progress. A full WAITING lobby (2/2)
  simply disappears, and `JOIN_GAME` → the HTTP join endpoint both return
  a bare `failed to join game`. The trap: a timed-out foreground
  `./race-ai-client poll --join …` usually survives its shell, keeps its
  seat, and readies itself — the lobby then looks 1/2 from anywhere but
  is actually 2/2, and your second join attempt 400s. Check the lobby
  roster (WS `LOBBY_UPDATE` / the host screen), not the HTTP status.

### WebGL2 specifics worth remembering

- `gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, ...)` is global state and leaks
  into every subsequent texture upload. Flip per-texture, then restore.
- **Billboards drew at half nominal size until 2026-11-10** —
  `_drawBillboard` scaled the ±0.5-spanning unit quad by `width/2`. Fixed
  by scaling by `width` instead; if you add a billboard, size it at what
  you want on screen.
- **Additive draws blend `ONE/ONE`, so `uAlpha` is ignored.** Marker and
  grid "alpha" values are documentary only — intensity comes from
  `uBrightness` alone. To make alpha matter for an additive draw you'd
  need `SRC_ALPHA, ONE`, but that dims every existing additive user
  (grid, cage, beams); don't change the blend in place.- UNRESOLVED for later: lines are always 1px wide (WebGL ignores
  `lineWidth` on most platforms), which is fine for the neon look here.
- `antialias: true` on the context + no culling in the spike — tiny scene,
  overdraw irrelevant; revisit if profiling says otherwise.
- Eye-height first-person camera rides the same spherical representation
  (target 200 units ahead), so one camera implementation serves both modes.
- The board ground is an 18×18 **texture** grid; wall cage is `GL_LINES`;
  the ground and sky are deliberately untextured elsewhere.

---

## 4. The next phase

### Phase 2 — visual parity (complete)

1. ~~Bump the marker readability~~ — **done**: fills 0.16 → 0.35 alpha,
   additive, brightness 1.8. Judged at playing distance and re-judged at
   zoom 2026-11-10 (sixth pass): legible on open canvas. Canvas-side
   tuning is sound — the two remaining caveats are DOM/HUD occlusion
   (the panels dim the board beneath them) and the `ONE/ONE` additive
   blend (the 0.35 alpha is a no-op; brightness 1.8 is what renders).
   See §2 (sixth pass) and §5.
2. ~~Bloom / glow~~ — **done** (`webgl2_bloom.js`; threshold 0.55, strength
   0.9, half-res, `?bloom=0` escape hatch). See §2.
3. ~~**God rays**~~ — **done** (`FRAG_GODRAYS`, half-res radial blur from
   the crystal's screen position, 48 taps, softened with a 9-tap H+V blur,
   additive in the composite; `?rays=0` opt-out; verified in-browser).
   See §2.
4. ~~Crystal effects~~ — **done** (`webgl2_crystal_effects.js`, all four);
   see §2. First-choice follow-up is a wire-path (not forced) trigger
   observed in-browser.
5. ~~**PBR/IBL**~~ — **done** (`FRAG_LIT` rewritten: GGX/Smith/Schlick
   direct light + per-fragment analytic sky for both diffuse irradiance
   and roughness-blurred specular reflections; no environment texture.
   Generator pillars read as polished metal with a warm/cool gradient;
   tokens are shaded hex solids). Gold decision: keep the emissive fake —
   the cage is additive line geometry PBR would never touch, and the
   glow look is on-brand; see §2.
6. ~~**Floating text / health labels**~~ — **done 2026-11-10**: verified at
   zoom; flip_y fix re-confirmed. Found and fixed a real defect in the
   pass — `_drawBillboard` drew every billboard at half nominal size
   (fifth white-box bug, see §2), so floating damage text was a speck;
   re-canvased and verified legible. Health labels are now full-size
   pill chips. Mobile/small-viewport labels remain unverified
   (testing backlog).
7. ~~**Chroma aberration / film grain / sharpen**~~ — **done and tuned**:
   the composite pass carries a static-hash grain (0.045), a soft vignette
   (0.55), radial chromatic aberration (0.006, quadratic toward the
   corners, `?chroma=0`) and a 4-tap unsharp mask (**0.25**, `?sharpen=0`;
   lowered from 0.4 after the A/B — 0.4 accentuated the 1–2px neon grid
   lines). Verified in-browser; see §2, fourth pass.

### Decision gate — **decided 2026-11-10: option A**

- **A — Default vanilla. ← chosen 2026-11-10, deletion completed the
  same day.** Vanilla is the default and is now the **only** renderer:
  `babylon.js` (1.66 MB gzip — note: it was gitignored, never tracked; the
  saving is in the served payload, not the repo), the Babylon script tags,
  `game_client.renderer.js`, `renderer.*.js`, `renderer.tokens.js`,
  `renderer.indicators.js`, `renderer.special.js`, `renderer.animations.js`,
  `renderer.colors.js`, `renderer.base.js`, `renderer.fx.js`,
  `camera_controller.js`, `game_client.crystal_effects.js` (not in the
  original plan — imported only by `renderer.base.js`), and the
  `initGameModules` fallback were all deleted. The BABYLON-based color
  lists in `game_client.constants.js` are gone too (the vanilla path
  carries its own palettes), as is the Babylon-only `setupTouchGestures`.
  A renderer-init failure now shows a fatal alert instead of silently
  degrading. The smoke gate (loads the bare URL) passes end-to-end after
  the deletion: boot + pick→move + end turn both seats + the two new
  `Cache-Control: no-cache` assertions.
- **B — Keep Babylon default.** Not taken. Only if parity had stalled;
  tree-shaking `@babylonjs/core` (1.66 MB → maybe 300–600 KB) would
  accept a new build step for no parity gain.
- **C — Ship both, flag-selected.** Was the pre-flip state; defensible
  only as a transition. Superseded by A.

### Testing backlog (blocks calling it done)

- ~~Game-over screen seen live from an actual GAME_WON~~ — **done
  (2026-11-09).** A scripted HTTP_AI seat won a side-instance match by
  capturing a generator and banking charge to 80/80 at turn 23
  (`SpectateScripted2`); the spectator client rendered the victory effect
  (confetti + crystal pulse, screenshotted), the browser-native `alert()`
  fired and was accepted, and the server-side winner frame now works over
  both transports (HTTP path used to broadcast an unhandled `GAME_OVER`
  message — see §3). Required a scripted seat: unattended AI-vs-AI matches
  never conclude (§3, second gotcha). `triggerVictoryOnce()` stays
  idempotent across the double announcement (event stream + GAME_WON).
- ~~Headless smoke test before the default flip~~ — **done and vendored
  as of 2026-11-10.** `tools/smoke/smoke.mjs` (Playwright + SwiftShader
  WebGL2; the repo's first Node tooling — `package.json` at the root,
  Playwright pinned as a dev dependency, driven via `make smoke`) spawns
  side instances itself (`HTTP_PORT=8081 ./race-server` +
  `WEB_PORT=8001 GAME_SERVER_URL=http://localhost:8081 ./web_server/web_server`),
  drives a full two-context lobby flow (connect → create 2-player game
  (host) → join by id (guest) → both ready → host starts), and asserts
  per context: `window.gameClient.vanillaRenderer === true`, renderer +
  camera constructed, `#renderCanvas` visible, turn phase populated, zero
  console errors/pageerrors, no "falling back to Babylon" warning, and a
  > 30 KB JPEG screenshot (both seats rendered the scene — verified by
  eye: crystal + cage, generators, mystery rings, grid, HUD). Runs clean
  headless via SwiftShader (`--use-angle=swiftshader
  --enable-unsafe-swiftshader`); screenshots land in `tools/smoke/out/`
  (gitignored). Set `SMOKE_BASE_URL` to target an already-running web
  instance instead of spawning side servers.
  Note: both players auto-deploy before turn 1 (game starts directly in
  PLAYING/MOVEMENT) — expected server behavior, not a renderer issue.
  Interaction is now automated too (2026-11-10): the smoke test samples
  each page's own ray-plane pick (`inputHandler.pickGridCell`, ~4 px
  grid) to turn canvas CSS pixels into grid cells — no camera math of
  its own — then, for whichever seat holds the turn: selects a token,
  asserts valid moves are surfaced, clicks a valid destination, waits
  for the server to accept the move (position flips in `gameState`),
  and ends the turn from both seats (Space/Enter) checking
  `current_turn_player_id` flips each time. It also pins the
  seat-relative overview azimuth per seat (`SEAT_ALPHAS`, camera alpha
  matches the deployment corner the local player sits behind).
  Renderer-agnostic — the same
  steps work over the Babylon fallback. Set `SMOKE_INTERACT=0` to skip.
  Still manual-only: the deployment phase (unreachable in an
  auto-deployed fresh game), attacks (no adjacent enemies on turn 1),
  first-person WASD/TAB, toggle-bloom-at-runtime, mobile/touch.
- ~~Frame-time check on a low-end stand-in~~ — **done (2026-11-10).**
  Headless probe (rAF sampling on the host seat during a PLAYING match,
  hardware GL via ANGLE→Vulkan/Mesa ANV, 6x CPU throttle via CDP):
  60 fps vsync-locked for bloom+rays at 1354×728 and 2000×1125, zero
  >33 ms frames, zero long tasks; bloom/rays overhead below vsync timing
  noise. SwiftShader (software floor) confirms bloom is the expensive
  pass if ever needed (`?bloom=0`). Caveat: idle scene, isolated GPU
  not phone-class. Details in §2, fifth verification pass.
- Mobile/touch: tap-to-select, tap-to-move, pinch zoom, two-finger pan,
  health labels at small viewport sizes.
- Mid-game first-person toggle (V) works; WASD with a controlled token,
  TAB token cycle, and pointer-lock look remain untested.
- First-person pointer lock look.
- Long-match stability (memory: the mesh/material caches grow per
  `updateGameState`; watch for leaks across many turns).
- The lobby's live member list with three players; AI reconnection flow.

### Scoreboard (what Babylon parity means)

| Capability | Babylon | Vanilla |
|---|---|---|
| Board, cage, ground | ✓ | ✓ |
| Tokens, health labels, selection glow | ✓ | ✓ |
| Generators + crystal + lasers | ✓ | ✓ (no refraction) |
| Mystery rings | ✓ | ✓ (spin/pulse only, no landing burst) |
| Indicators (hover/move/attack/threat/pips) | ✓ | ✓ |
| Particles (explosions, confetti, ambient dust) | ✓ | ✓ |
| Camera (overview + first-person; overview azimuth is seat-relative) | ✓ | ✓ |
| Picking | ✓ `scene.pick` | ✓ ray-plane (equivalent for grid cells) |
| Bloom / glow layer | ✓ | ✓ (half-res gaussian + composite bloom/vignette/grain) |
| Chromatic aberration / sharpen | ✓ | ✓ (CA 0.006 radial + unsharp mask 0.25; grain + vignette always on in the composite) |
| God rays | ✓ | ✓ (radial blur from the crystal's screen pos, softened; additive — no ray occlusion) |
| Crystal effects (fog/ghost/lightning/whirlwind) | ✓ | ✓ (stub replaced; verified in-browser) |
| PBR / IBL | ✓ | ✓ (GGX/Smith/Schlick + analytic sky IBL; no env texture) |
| Refraction (shard pillars) | ✓ | ✗ |

---

## 5. Open questions

- **Bloom or no bloom?** Decided for now: on by default, half-res,
  `?bloom=0` as the escape hatch. Frame-time check on a low-end stand-in
  now done (fifth pass in §2): 60 fps vsync-locked at 6x CPU throttle,
  bloom+rays below timing noise, not fill-bound at 2.25 MP. An INP check
  is all that remains of the perf question — no frame-time reason to hold
  bloom back.
- **Overview framing is tight on square-ish viewports.** The overview
  pose used to be global to all seats (alpha π/4, beta 60°, radius 0.8,
  fov 40°) and asymmetric: P0 tokens rendered inside the crystal
  silhouette, P2 behind the info panel, P3 off-frame. **Resolved
  2026-11-10 (per-seat azimuth, seventh pass in §2)**: the camera now
  sits behind the local player's deployment corner with radius 1.1x the
  board diagonal — every seat sees its own corner near-side and
  in-frame, symmetrically. `#controls`' blurb is capped to 480 px so the
  bottom strip (where your corner projects) is usable. Spectators get
  the followed seat's azimuth. Remaining: the pose is still fixed per
  seat (no aspect-aware zoom clamp for ~1:1 viewports) and the far
  corner can still overlap the crystal/cage for an opponent at some
  angles — accepted; pan handles it. The Babylon-matching default is
  deliberately gone (the seat-relative pose is strictly more readable);
  the `?renderer=` flag and Babylon are both gone with it.
- **Keep Babylon in-repo as fallback forever?** Closed 2026-11-10:
  deleted the same day (ahead of the planned one-release wait, at the
  maintainer's instruction; the rollback hatch was never exercised).
  The web client is vanilla-only.
- **Test suite?** Answered in part: `make smoke` now runs a headless
  smoke test of the vanilla path (Playwright + SwiftShader WebGL2,
  vendored at `tools/smoke/smoke.mjs` — the repo's first Node tooling,
  root `package.json`, Playwright pinned). As of 2026-11-10 it is a
  behavioral gate too: after boot it plays a real move over the wire
  (cells resolved by sampling the page's own ray-plane pick — no camera
  math in the test), ends the turn from both seats, and asserts the
  seat-relative overview azimuth per seat. Still missing
  before the default flip: deploy-phase coverage (auto-deploy hides it
  in fresh games), attacks, first-person interactions, mobile/touch, and
  rendering correctness beyond "frame is non-trivial". The Babylon path
  is likewise untested.
- **Babylon version bump?** If we keep Babylon during transition: 8.45.3 is
  pinned; 9.35.0 is current. Don't upgrade unless forced.
- **`main.kuki` cache headers** — done 2026-11-10. Every response from
  the web server is now `Cache-Control: no-cache` (revalidate every load);
  Go's ServeFile sets Last-Modified, so repeat loads get 304s and fresh
  deploys propagate immediately. No build step needed; the smoke gate
  asserts the header on `/` and `/static/game_client.js`. Content-hash +
  immutable paths remain a possible follow-up if 304 round-trips ever
  matter — they won't at ~85 KB gzip.

## 6. Reproducing

```bash
make server-run          # game server, http://localhost:8080
make web-server-run      # web client + reverse proxy, http://localhost:8000
```

Then open `http://localhost:8000/` — vanilla WebGL2 is the default as of
2026-11-10 (hard-reload once). Add `&bloom=0` to compare against the
pre-bloom direct path, `&rays=0` to compare against bloom-without-god-rays,
or `&chroma=0` / `&sharpen=0` to see the composite without the corner CA or
the unsharp mask. Create a
2-player game, add an AI with `./race-ai-client poll --join <game-id>
--name AI --strategy aggressive` next to your seat, ready both, start.

Launch the AI client **detached** (background), not in a foreground shell
with a timeout — see §3, "a full lobby is invisible … join 400s". Compare
Babylon.js was removed 2026-11-10; there is no renderer flag left.

Headless verification (no GPU, no human seats):

```bash
npm install              # once; installs Playwright
npx playwright install chromium   # once
make smoke               # spawns side servers on 8081/8001, runs, tears down
```

`make smoke` exercises page load (no renderer flag needed — vanilla is
the only renderer) → connect → create/join → ready → start → vanilla
renderer boot + render, asserting zero console errors, a non-trivial
scene per seat and `Cache-Control: no-cache` on the HTML shell and static
JS — and the behavioral gate plays a real move over the wire (select →
click destination → server accepts; end turn from both seats). Screenshots
land in `tools/smoke/out/`.
Requires the built binaries (`race-server`, `web_server/web_server`) —
run `make build` first on a fresh checkout. Set `SMOKE_BASE_URL` to aim
at an already-running instance instead of spawning side servers.

When verifying in Chrome DevTools, take screenshots with `filePath` +
`format: "jpeg"` (see §3) — inline full-page PNGs at DPR 1.667 each run
~3.5 MB and kill the session.
