# Chapter 5: Functions

**Example: `learn/examples/07-functions/`**

Your `PlayTurn` will outgrow a single block quickly. Functions are how
you keep it readable — one idea per function, composed in `PlayTurn`.

## The pieces

```kukicha
func StepTowardCrystal(api: reference learn.LearnerAPI, tid: int) bool
    ...
    if dx equals 0 and dy equals 0
        return false
    _ = api.Move(tid, pos.X + dx, pos.Y + dy)
    return true

func DeployOne(api: reference learn.LearnerAPI) bool
    reserve := api.Reserve()
    if reserve[10] equals 0
        return false
    for x from 0 to 3
        result := api.Place(10, x, 2)
        if result.Success
            return true
    return false
```

- Parameters are `name: Type`. The LearnerAPI is passed by reference
  (`reference` prefix) because your actions mutate the game.
- `-> Type` after the parameter list declares the return type.
- A function returns with `return value`.

## Composition

```kukicha
func PlayTurn(api: reference learn.LearnerAPI)
    api.Say("--- Turn {api.TurnNumber()} ---")

    if DeployOne(api)
        api.Say("deployed a 10hp token")

    moved := 0
    for tid in api.MyTokens()
        if StepTowardCrystal(api, tid)
            moved = moved + 1
    api.Say("moved {moved} token(s) toward the crystal")

    _ = api.Done()
```

The strategy reads top to bottom: deploy if possible, march everyone,
report. Each helper is independently testable and reusable.

## Your turn

1. Extract the "compute one step toward a target" logic into
   `StepToward(api, tid, tx, ty)` and make `StepTowardCrystal` a
   one-line call to it. Then re-point your whole army at a generator
   by changing one argument.
2. Write `Report(api)` that summarizes reserve and deployed counts at
   the top of every turn, and call it from `PlayTurn`.
3. Make `DeployOne` take the health value as a parameter and call it
   with 10, then with 4 once the 10hp reserve is gone.
