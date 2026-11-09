# Vanilla JavaScript + WebGL2 for the Web Client

> **Status**: Phase 0 and Phase 1 are complete. The vanilla WebGL2 renderer
> ships behind an opt-in flag (`?renderer=webgl2`); Babylon.js remains the
> default. Phase 2 (visual parity) and the default-flip decision are open.
> Nothing in this document has been merged into a release — everything below
> was validated locally, in the browser, against a live game server.

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

### Phase 1 — vanilla WebGL2 spike, opt-in (done)

New `web_server/static/webgl2/` (~3,634 lines, ~31 KB gzip), wired in with
`?renderer=webgl2`:

| File | Lines | Role |
|---|---|---|
| `glmath.js` | 228 | vec3 + column-major mat4 (perspective/lookAt/multiply/invert/TRS) |
| `webgl2_core.js` | 170 | context, program/attrib management, VAO mesh builders (triangles/lines/points) |
| `webgl2_geometry.js` | 368 | ground/box/cylinder/UV/ico sphere/torus/quad/circle/square builders |
| `webgl2_camera.js` | 644 | spherical orbit overview + first person, wheel zoom, two-finger pinch/pan, focus/transition/FP smoothing |
| `webgl2_renderer.js` | 2,152 | `VanillaRenderer3D` — drop-in for `Renderer3D` (duck-typed), same public interface |
| `webgl2_textures.js` | 72 | canvas-generated textures (grid, health labels) |

Reached via `game_client.modules.js` → `VANILLA_RENDERER` const; falls back
to Babylon automatically if the vanilla renderer throws during init.

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

**Not yet verified:** the game-over overlay and victory effects firing live
(no match has reached GAME_WON yet; the code path is renderer-agnostic and
wired, but unproven visually).

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

### WebGL2 specifics worth remembering

- `gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, ...)` is global state and leaks
  into every subsequent texture upload. Flip per-texture, then restore.
- UNRESOLVED for later: lines are always 1px wide (WebGL ignores
  `lineWidth` on most platforms), which is fine for the neon look here.
- `antialias: true` on the context + no culling in the spike — tiny scene,
  overdraw irrelevant; revisit if profiling says otherwise.
- Eye-height first-person camera rides the same spherical representation
  (target 200 units ahead), so one camera implementation serves both modes.
- The board ground is an 18×18 **texture** grid; wall cage is `GL_LINES`;
  the ground and sky are deliberately untextured elsewhere.

---

## 4. The next phase

### Phase 2 — visual parity (not started)

Parity work, roughly in order of value:

1. **Bump the marker readability**: valid-move/attack fill quads are alpha
   0.16 — often invisible against the dark board. Raise fill alpha, or add
   a second additive pulse.
2. **Bloom / glow** — Babylon's `GlowLayer` (intensity 1.5) + bloom pipeline
   produced the "neon cage" look. Candidate: half-res bloom pass with a
   separable gaussian, additive over the opaque pass. Alternative: skip
   bloom and keep emissive-only; looks acceptable, arguably cleaner.
3. **God rays** — Babylon's `VolumetricLightScatteringPostProcess`. Emulate
   with a radial-blur pass from the crystal's screen position, or delete
   outright (crystal already breathes/pulses).
4. **Crystal effects** — the stub animator logs and plays sounds but spawns
   no fog/lightning/ghosts/whirlwind. The Babylon `CrystalEffectAnimator`
   is ~400 lines and has particle spawners for all four — portable as-is.
   Effects are the main juice this scene has, so this is high value.
5. **PBR/IBL** — currently Lambert + Blinn-Phong. True PBR (GGX) + a small
   procedural environment (or baked gradient cube) would restore the gold
   and gems to full richness. This is also the moment to decide on the
   gold: keep the current emissive fake (free, moody) or pay the shader
   rewrite.
6. **Floating text / health labels** — verify at zoom, check flip_y and
   readability.
7. **Chroma aberration / film grain / sharpen** — optional cosmetics from
   the Babylon pipeline; reimplement as cheap fullscreen passes or delete.

### Decision gate

Make the call once parity is close:

- **A — Default vanilla.** `?renderer=` becomes the normal path; Babylon
  dropped (delete the 1.66 MB, the two `<script>` tags, `game_client.renderer.js`,
  `renderer.*.js`, `camera_controller.js`, `renderer.special.js` env map).
  Payload: ~85 KB gzip total for the whole client.
- **B — Keep Babylon default.** Only if parity stalls. In that case still
  consider tree-shaking `@babylonjs/core` (drops the 1.66 MB to maybe
  300–600 KB), accepting the new build step.
- **C — Ship both, flag-selected.** Current state; defensible only as a
  transition.

### Testing backlog (blocks calling it done)

- Game-over screen + victory effect seen live (confetti, alert, sound).
- Mobile/touch: tap-to-select, tap-to-move, pinch zoom, two-finger pan,
  health labels at small viewport sizes.
- Mid-game first-person toggle (V), WASD movement, TAB cycle.
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
| Camera (overview + first-person) | ✓ | ✓ |
| Picking | ✓ `scene.pick` | ✓ ray-plane (equivalent for grid cells) |
| Bloom / glow layer | ✓ | ✗ (emissive-only) |
| Chromatic aberration / grain / sharpen | ✓ | ✗ |
| God rays | ✓ | ✗ |
| Crystal effects (fog/ghost/lightning/whirlwind) | ✓ | ✗ (stub; sounds play) |
| PBR / IBL | ✓ | ~Lambert/Blinn-Phong |
| Refraction (shard pillars) | ✓ | ✗ |

---

## 5. Open questions

- **Bloom or no bloom?** The honest answer depends on how the neon-cage look
  reads on a low-end device without it. Try both; measure INP, not just vibes.
- **Keep Babylon in-repo as fallback forever?** Cost of keeping is one file
  + scripts; keeping it means we can flip back cheaply. Recommendation:
  keep it until the default-flip ships, then delete.
- **Test suite?** There is currently **no automated test for the 3D layer
  at all.** A headless screenshot/smoke test (playwright-style) before the
  default-flip would be the first net under the renderer.
- **Babylon version bump?** If we keep Babylon during transition: 8.45.3 is
  pinned; 9.35.0 is current. Don't upgrade unless forced.
- **`main.kuki` cache headers** — the web server sets no cache headers and
  no content hashing, so every deploy is a hard reload for first-time
  visitors anyway. Consider content hashes + immutable static paths if we
  flip the vanilla default.

## 6. Reproducing

```bash
make server-run          # game server, http://localhost:8080
make web-server-run      # web client + reverse proxy, http://localhost:8000
```

Then `http://localhost:8000/?renderer=webgl2` (hard-reload once). Create a
2-player game, add an AI with `./race-ai-client poll --join <game-id>
--name AI --strategy aggressive` next to your seat, ready both, start.

Compare against the Babylon path by dropping the flag.
