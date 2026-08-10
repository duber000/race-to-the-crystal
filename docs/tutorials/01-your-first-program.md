# Chapter 1: Your First Program

**Example: `learn/examples/01-hello/`**

You already know how to code. This chapter is about the shape of a
Kukicha program that plays the game — the one pattern every later
chapter builds on.

## The shape of every program

```kukicha
petiole main                          # 1. package declaration

import "race-to-the-crystal/learn" as learn   # 2. imports

func PlayTurn(api: reference learn.LearnerAPI)  # 3. your turn function
    api.Say("--- my turn ---")
    _ = api.Place(10, 2, 2)
    _ = api.Done()

func main()                           # 4. entry point
    sim := learn.NewSimulation(learn.NewConfig())
    sim.Run(PlayTurn)
```

- **`petiole main`** — every multi-file program declares its package name
  first. `main` is the program's package.
- **`func PlayTurn(...)`** — the simulation calls this at the start of
  each of your turns. Everything you want to do this turn goes here.
- **`func main()`** — the entry point. It creates a simulation and runs
  it. `sim.Run` takes your `PlayTurn` function and calls it every turn.

## What the LearnerAPI does for you

- `api.Say(msg)` prints a message — your window into the game.
- `api.Reserve()` returns a map of health values (10, 8, 6, 4) to how
  many tokens of that kind you still have in reserve.
- `api.Place(10, 2, 2)` deploys a 10hp token at (2,2). The corner cells
  (0,0)…(2,2) are your deployment zone — but your starting tokens already
  sit on (0,0), (1,0), (2,0), so deploy at (2,2).
- `api.Done()` ends your turn. (Optional: the simulation ends your turn
  automatically when `PlayTurn` returns.)

## Run it

```bash
kukicha run learn/examples/01-hello/
```

You will see the opening board, then each of your turns narrated:
what you placed, what the game did in response, and the turn passing
to the AI. Every action you take is echoed back with the game's own
message — a `Place` that succeeds says where the token landed; one that
fails says exactly why.

## Two things to notice

1. **The game talks back.** `Place` returns an `ActionResult` with a
   human-readable `Message`. The simulation prints it automatically.
   Treat these messages as your debugging window.
2. **`_ =`** is the blank assignment. `Place` returns a value you don't
   need yet — `_ =` says "I know there's a result, I'm ignoring it."

## Your turn

1. Change the deployed health from 10 to 4 and rerun. What changes in
   the narration?
2. Deploy to (2, 2) twice in the same turn. What does the second call
   say, and why? (Hint: read the MOVEMENT vs ACTION note in the README.)
3. Add `api.Say(api.Board())` at the start of `PlayTurn`. Now you can
   see the board before you act.
