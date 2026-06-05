# TODO

## Kukicha Compiler Bugs

Upstream issues filed against [kukichalang/kukicha](https://github.com/kukichalang/kukicha/issues).

### ~~[#310](https://github.com/kukichalang/kukicha/issues/310) — `val.(T) onerr` generates invalid nil-check on bool~~ **FIXED in 0.48.4**

Workaround removed — `server/websocket_handler.kuki` now uses `val.(T) onerr` directly.

---

### [#311](https://github.com/kukichalang/kukicha/issues/311) — Cross-package variant enum construction rejected by semantic checker

**Still broken in 0.48.4** (issue is closed but the fix didn't land). Workaround remains in place.

---

### [#312](https://github.com/kukichalang/kukicha/issues/312) — `kukicha build` silently skips explicit targets listed after a `...` glob

`kukicha build ./a/ ./b/... ./c/` never builds `./c/`. No error or warning is emitted.

**Workaround:** use separate `kukicha build` invocations per package (see `deployment/dockerfiles/Dockerfile`).

---

## Client Package — Incomplete Migration ~~RESOLVED~~

~~`client/ai_client.kuki` and `client/http_ai_client.kuki` were not fully migrated and do not compile.~~

**Fixed:** Both files were moved to `client/ai/` as a separate package (resolving the `func main()` conflict). The `Session` struct and its methods (`NewSession`, `FetchState`, `PickAction`, etc.) are defined in `client/ai/http_ai_client.kuki`, removing all unresolved references. `make ai-client` and `make ai-client-run` build and run the AI client.
