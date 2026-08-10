# Chapter 3: Decisions and Math

**Example: `learn/examples/05-decisions/`**

A strategy is a decision function: look at the world, compute something,
act. This chapter is the "compute" part.

## Math helpers

`stdlib/math` covers the basics:

```kukicha
import "stdlib/math"

func Distance(a: int, b: int) int
    return math.AbsInt(a - b)
```

Manhattan distance (the board has no diagonals for distance purposes) is
`|x1 - x2| + |y1 - y2|` — the same formula the game uses internally.

## Positions

`api.TokenPosition(id)` tells you where a token stands. It returns a
`Position` with fields `.X` and `.Y`:

```kukicha
mine := api.MyTokens()
tid := mine[0]
pos := api.TokenPosition(tid)
dist := Distance(pos.X, 12) + Distance(pos.Y, 12)
api.Say("token {tid} is {dist} steps from the crystal")
```

## If / else if / else

```kukicha
if dist > 3
    _ = api.Move(tid, pos.X + 1, pos.Y)
else if dist equals 0
    api.Say("on the crystal — holding position")
else
    api.Say("close — holding position")
```

- `if` / `else if` / `else` blocks are indentation-based, no braces.
- Use `equals` / `isnt` for comparisons, `>` / `<` as usual.
- `else if` chains are the idiomatic multi-way branch; three-plus
  alternatives can also be a `switch` (chapter 8).

## Your turn

1. Make the march smarter: when the token is *exactly* one step from
   the crystal but the crystal cell is occupied by an enemy, don't
   move — `api.Attack` comes in chapter 8.
2. Write a `CloserTo(x1, y1, x2, y2)` helper that returns the
   coordinate pair nearer to the crystal, and use it to move
   diagonally instead of always `+1` on X.
3. Change the threshold from 3 to 12 and watch what changes in the
   narration — the token stops marching much sooner.
