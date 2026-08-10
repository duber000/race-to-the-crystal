# Chapter 2: Variables and Types

**Example: `learn/examples/04-variables/`**

Kukicha is statically typed, but you rarely write types: `:=` declares a
variable and infers its type.

## Declaring variables

```kukicha
turn := api.TurnNumber()     # int
has_10 := reserve[10] > 0    # bool
api.Say("Turn {turn}")       # string interpolation
```

- `:=` declares and assigns. The type is inferred from the right side.
- Strings interpolate: any `{expr}` inside a double-quoted string is
  evaluated and inserted.
- `=` (without the colon) *reassigns* an existing variable.

## Maps

`api.Reserve()` returns a **map** — the game's dictionary of health
values to remaining counts:

```kukicha
reserve := api.Reserve()
has_10 := reserve[10] > 0
```

The full type is `map of int to int`, but you will almost never write
it — the inference handles it. Index a map with `map[key]`; a missing
key yields the zero value (0 for int), which is why
`reserve[10] > 0` is a safe existence check.

## Booleans

Kukicha spells boolean logic in English:

| Kukicha | means |
|---------|-------|
| `and` / `or` / `not` | `&&` / `\|\|` / `!` |
| `equals` / `isnt` | `==` / `!=` |
| `is empty` / `isnt empty` | nil / empty checks |

```kukicha
if has_10
    _ = api.Place(10, 2, 2)
else if has_4
    _ = api.Place(4, 2, 2)
else
    api.Say("reserve is empty")
```

## Your turn

1. The example places at (2,2) every turn until the 10hp reserve is
   gone. What happens on the turn after the cell is occupied? (The
   narration will tell you — read it.)
2. Add a counter: declare `turns := 0` in `main()`, increment it in
   `PlayTurn`... it won't persist — `PlayTurn` is called fresh each
   turn. That is what `api.Memo` is for (chapter 7). Try it:
   `api.Memo("turns", "{turn}")` and recall it next turn.
3. Print `reserve` itself: `api.Say("{reserve}")`. Maps stringify.
