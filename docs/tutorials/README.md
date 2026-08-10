# Learn to Program with Kukicha — Race to the Crystal Edition

A hands-on course for programmers who want to learn Kukicha by writing
programs that play the game. Modeled on *Learn to Program with Minecraft*
(Craig Richardson): instead of scripting a Minecraft world with Python,
you script a Race to the Crystal game with Kukicha.

**You need:** a working Kukicha toolchain and this repo. Nothing else —
no server, no browser, no setup. The simulation runs the whole game
in-process.

## How it works

Your program is a `PlayTurn` function. The simulation creates a fresh
game, makes you player 0, fills the other seats with AI players, and
calls your function at the start of every one of your turns:

```kukicha
petiole main

import "race-to-the-crystal/learn" as learn

func PlayTurn(api: reference learn.LearnerAPI)
    api.Say("my turn!")
    _ = api.Place(10, 2, 2)
    _ = api.Done()

func main()
    sim := learn.NewSimulation(learn.NewConfig())
    sim.Run(PlayTurn)
```

Run it with:

```bash
kukicha run learn/examples/01-hello/
```

**The rules of the game:** a 24x24 board with the crystal at (12,12),
four generators at the quadrants, and deployment corners for each player.
You win by holding the crystal with enough tokens for three consecutive
turns (each disabled generator reduces the requirement by 2). Every
turn is two phases: MOVEMENT (move or deploy) then ACTION (attack or
end). The simulation ends your turn for you when `PlayTurn` returns.

**Two details that will save you time:**

- You may only take *one* action per phase — after a `Place` or `Move`
  the phase becomes ACTION, so you cannot place three tokens in one turn.
- Your starting three tokens are auto-deployed at (0,0), (1,0), (2,0) —
  the rest wait in your reserve.

## Course map

| Ch | Topic | Example |
|----|-------|---------|
| 1 | Your first program | `01-hello` |
| 2 | Variables and types | `04-variables` |
| 3 | Decisions and math | `05-decisions` |
| 4 | Loops | `06-loops` |
| 5 | Functions | `07-functions` |
| 6 | Lists and maps | `08-collections` |
| 7 | Types and methods | `09-strategist` |
| 8 | Reading the game: the action list | `03-first-strategy` |
| 9 | The strategy ladder | `10-strategy-ladder` |
| 10 | Going live (REST) | [10-going-live.md](10-going-live.md) |

## The LearnerAPI cheat sheet

| Call | What it does |
|------|--------------|
| `api.Say(msg)` | print a message |
| `api.Board()` | ASCII map of the 24x24 grid |
| `api.Observe()` | full situation report |
| `api.Victory()` | victory conditions + crystal progress |
| `api.Reserve()` | map of health -> tokens remaining |
| `api.Tokens()` / `api.MyTokens()` | description / list of your token ids |
| `api.TokenPosition(id)` | where one of your tokens is |
| `api.Place(health, x, y)` | deploy a reserve token (MOVEMENT) |
| `api.Move(id, x, y)` | move a token (MOVEMENT) |
| `api.Attack(a, b)` | attack with token a at token b (ACTION) |
| `api.Actions()` | the typed list of what you may do right now |
| `api.Done()` | end your turn (optional — the simulation does it) |
| `api.Memo(k, v)` / `api.Recall(k)` | remember a value between turns |
| `api.TurnNumber()` / `api.MyTurn()` / `api.Phase()` | game info |

For the full language, see the Kukicha `SKILL.md` and `cookbook.md`.
Every diagnostic the compiler throws has an explanation:
`kukicha explain <code>` or `kukicha check --explain`.
