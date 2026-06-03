# Kukicha Style Guide for race-to-the-crystal

This project is written in Kukicha, a near-superset of Go. Most Go syntax
compiles unchanged, but Kukicha-idiomatic forms are **required** — reviewers
reject PRs that use raw Go operators, type syntax, or nil when a Kukicha form
exists.

## Anti-patterns observed in this codebase

These are the recurring mistakes found in the generated `.kuki` files here.
Fix them proactively; don't wait for a lint warning.

### 1. `==` and `!=` — the most common mistake

`equals` and `isnt` replace **every** `==` and `!=`, not just nil/empty checks.

```kukicha
# WRONG — Go operators leak into non-empty comparisons constantly in this codebase
if gs.phase == enums.PLAYING
if gs.turn_phase != enums.MOVEMENT
if dc.cell_type != enums.GENERATOR
if m == dest
if start == end
if len(parts) != 3

# CORRECT
if gs.phase equals enums.PLAYING
if gs.turn_phase isnt enums.MOVEMENT
if dc.cell_type isnt enums.GENERATOR
if m equals dest
if start equals end
if len(parts) isnt 3
```

`equals`/`isnt` with `empty` is the one context where this codebase gets it
right — apply the same keyword to all other comparisons too.

### 2. Explicit type in list literal elements

When element type is inferrable from the outer literal, omit it.

```kukicha
# WRONG
var DIRECTIONS = list of DirOffset{
    DirOffset{dx: -1, dy: -1},
    DirOffset{dx: 0,  dy: -1},
}

# CORRECT — inner type is inferred from the outer `list of DirOffset`
var DIRECTIONS = list of DirOffset{
    {dx: -1, dy: -1},
    {dx: 0,  dy: -1},
}
```

Same rule applies to `append` calls and function arguments where the type is
fixed by the parameter signature.

### 3. `panic` — use errors instead

```kukicha
# WRONG — triggers the Kukicha lint warning
panic "health must be >= 0"

# CORRECT — return an error or use onerr
func NewToken(...) (Token, error)
    if health < 0
        return Token{}, error "health must be >= 0"
```

### 4. Fallback return for `list of byte` (and similar slice types)

```kukicha
# WRONG — string-to-slice cast is a Go-ism
result := decode(s) onerr return "" as list of byte

# CORRECT
result := decode(s) onerr return empty list of byte
```

## Quick reference — Kukicha vs Go

| Kukicha (write this) | Go equivalent (never write in .kuki) |
|----------------------|--------------------------------------|
| `equals` | `==` |
| `isnt` | `!=` |
| `and`, `or`, `not` | `&&`, `\|\|`, `!` |
| `empty` | `nil` |
| `list of T` | `[]T` |
| `map of K to V` | `map[K]V` |
| `reference T` | `*T` (statically non-empty) |
| `nullable reference T` | `*T` (may be nil; guard before dereference) |
| `reference of x` | `&x` |
| `dereference x` | `*x` |
| `name: Type` in params | `name Type` (accepted but deprecated) |
| `for x in items` | `for _, x := range items` |
| `for i from 0 to N` | `for i := 0; i < N; i++` |
| `empty list of T` | `nil` / `[]T(nil)` |
| `{field: val}` (type inferrable) | `T{field: val}` |

## Enum patterns used in this project

### Variant enums (plain integer-backed, no string value)
```kukicha
enum GamePhase
    SETUP
    PLAYING
    ENDED
```
Reference variants with the bare name inside the same package (`PLAYING`) or
qualified from another package (`enums.PLAYING`). Switch with `when`:
```kukicha
switch gs.phase
    when enums.PLAYING
        ...
    when enums.ENDED
        ...
```

### String-backed enums
```kukicha
enum PlayerColor: string
    CYAN = "cyan"
    MAGENTA = "magenta"
```
The compiler auto-generates:
- `String()` — returns the raw string value (`PlayerColor.CYAN.String()` → `"cyan"`)
- `ParsePlayerColor(s string) (PlayerColor, bool)` — parse at boundaries

Prefer `switch` + `when` over a chain of `if color equals ...` for 3+ arms.

## onerr patterns

```kukicha
# Propagate — most common
data := fetch.Get(url) onerr return empty, error "{error}"

# Fallback value on expected absence
token := crypto.RandomToken(32) onerr return ""

# Discard (test code only)
doSomething() onerr discard

# Named error for wrapping
data := parse(raw) onerr as e
    return empty, error "parse failed: {e}"
```

`onerr` is for genuinely fallible operations (I/O, parse, network, required
env var). For lookups with a sensible default, use `*Or` functions instead:
`maps.GetOr`, `slice.GetOr`, `slice.FirstOr`, `env.GetOr`.

## nullable reference narrowing

```kukicha
# Always narrow before dereference
cell := brd.get_cell(nx, ny)
if cell equals empty
    continue
dc := dereference cell   # safe: narrowed above
```

The compiler rejects `dereference x` unless `x` is narrowed in the current
branch by `if x isnt empty` or `if x equals empty: return/continue/break`.

## Module layout

```
shared/enums/   — CellType, GamePhase, TurnPhase, PlayerColor, Direction, …
shared/types/   — TokenID, PlayerID, Position, Pos()
shared/constants/ — board dimensions and tunable constants
shared/errs/    — project error values
game/           — board, token, player, combat, movement, crystal, AI logic
server/         — HTTP/WebSocket handlers, auth, lobby, coordinator
```

Import cross-package types with an alias to avoid name collisions:
```kukicha
import "race-to-the-crystal/shared/enums" as enums
import "race-to-the-crystal/shared/types" as types
```
