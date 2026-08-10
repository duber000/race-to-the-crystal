# Chapter 7: Types and Methods

**Example: `learn/examples/09-strategist/`**

Free functions work, but a strategy has state: a name, a target, a move
count. Give it a type.

## Declaring a type

```kukicha
type Strategist
    name: string
    target_x: int
    target_y: int
    move_count: int
```

`type Name` followed by indented fields. Build values with a literal:
`Strategist{name: "MarchBot", target_x: 12, target_y: 12, move_count: 0}`.
A constructor function keeps the defaults in one place:

```kukicha
func NewStrategist() Strategist
    return Strategist{name: "MarchBot", target_x: 12, target_y: 12, move_count: 0}
```

## Methods

A method binds a function to a type. The receiver comes first with
`on`:

```kukicha
func Describe on s: reference Strategist string
    return "{s.name} (heading to {s.target_x},{s.target_y}; {s.move_count} moves made)"

func Step on s: reference Strategist(api: reference learn.LearnerAPI, tid: int)
    pos := api.TokenPosition(tid)
    ...
    s.move_count = s.move_count + 1
```

Call them with dot syntax: `bot.Describe()`, `bot.Step(api, tid)`.
The `reference` receiver matters: `Step` mutates `move_count`, so the
method must receive the object by reference, not a copy.

## The game forgets your objects

Here is the catch that makes this chapter interesting: **your object
does not survive between turns.** `PlayTurn` runs fresh every turn. The
fix is to rebuild your strategist from remembered state each turn:

```kukicha
bot := NewStrategist()
bot.name = api.Recall("bot_name")
bot.move_count = parse.IntOr(api.Recall("bot_moves"), 0)

# ...play the turn...

api.Memo("bot_name", bot.name)
api.Memo("bot_moves", "{bot.move_count}")
```

`Memo`/`Recall` is the game's notebook: strings in, strings out. Store
numbers as strings and parse them back with `parse.IntOr`.

## Your turn

1. Add a `captures` counter to `Strategist` and bump it whenever the
   narration shows a mystery-square heal. (You can't see the event
   directly — use `api.Board()` or check `TokenPosition` changes.)
2. Add a `Decide(api) bool` method that returns whether the strategist
   wants to deploy this turn, and call it from `PlayTurn`.
3. Give `Strategist` a `team` — a list of token ids — and teach `Step`
   to march the whole team. Rebuild the team from `MyTokens()` each turn.
