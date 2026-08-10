# Chapter 6: Lists and Maps

**Example: `learn/examples/08-collections/`**

Your token army is a list; your reserve is a map. Collections are the
heart of any real strategy.

## Lists

`api.MyTokens()` returns `list of int` — your deployed token ids:

```kukicha
mine := api.MyTokens()
api.Say("deployed tokens: {len(mine)} -> {mine}")
```

- `len(xs)` counts.
- Index with `xs[i]`, negative indexes work from the end (`xs[-1]`).
- The inferred type is `list of int`; you only write it when declaring
  an empty one: `empty list of int`.

## Maps

`api.Reserve()` returns `map of int to int`:

```kukicha
func StrongestReserve(reserve: map of int to int) int
    strongest := 0
    for hv, count in reserve
        if count > 0 and hv > strongest
            strongest = hv
    return strongest
```

- Iterating a map yields **keys** with `for k in m`, or key+value with
  `for k, v in m`.
- `map[key]` returns the zero value for missing keys — so
  `reserve[10]` is 0 when the 10hp reserve is empty, and the check
  `count > 0` does double duty.

## Combining them

```kukicha
if strongest > 0 and len(mine) < 5
    _ = api.Place(strongest, 2, 2)

for tid in mine
    pos := api.TokenPosition(tid)
    if pos.X < 12
        _ = api.Move(tid, pos.X + 1, pos.Y)
```

The strategy: keep the army at five tokens (deploying the strongest
reserve), and keep everyone advancing on the crystal's column.

## Your turn

1. The march only advances tokens whose X is left of the crystal.
   Add the Y axis so tokens converge from both directions.
2. Count your army's total health: `sum := 0` then add each token's
   health. (You only have positions — total the *reserve* values
   instead: `10 * reserve[10] + 8 * reserve[8] + ...`.)
3. Stop deploying once the army is 6 tokens: change the `< 5` check
   and observe the reserve staying untouched in the narration.
