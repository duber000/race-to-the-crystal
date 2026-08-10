# Chapter 4: Loops

**Example: `learn/examples/06-loops/`**

Battles are won by tokens, and tokens come in crowds. Loops let one
strategy govern them all.

## Counting loops

```kukicha
for x from 0 to 3        # 0, 1, 2 — "to" is exclusive
    _ = api.Place(10, x, 2)
```

`for x from 0 to 3` runs with x = 0, 1, 2. Use `through` for inclusive
(`0 through 3` → 0,1,2,3). The example uses the loop to try each cell
of the row y=2 until one is free:

```kukicha
for x from 0 to 3
    result := api.Place(10, x, 2)
    if result.Success
        api.Say("deployed at ({x}, 2)")
        break
```

`break` stops the loop; `continue` skips to the next iteration.

## Collection loops

```kukicha
for tid in api.MyTokens()
    # do something with each token id
```

`for item in collection` iterates lists (and maps — keys only, like Go
and Python; use the two-variable form for key + value).

## Loops + state per iteration

The march pattern: read the token's position, compute a one-step delta,
move. One action per phase means one move per turn — so the loop over
your tokens moves *one* of them per turn unless you track which ones
already moved. The example just moves everything one step each turn
(moves that are invalid simply fail with a narrated message).

## Your turn

1. Rewrite the deploy loop to try `(x, 2)` for x = 2, 1, 0 — the
   reverse order. When does it behave differently?
2. The march moves every token toward the crystal every turn. Add a
   check: only move tokens that are *further* than 2 steps from the
   crystal (reuse the `Distance` helper from chapter 3).
3. Use `for i, tid in api.MyTokens()` and have the first token guard
   the crystal while the others march — a `if i equals 0` branch.
