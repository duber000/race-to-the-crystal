# Chapter 9: The Strategy Ladder

**Example: `learn/examples/10-strategy-ladder/`**

The game ships three AI strategies you can fight (or study):

| Strategy | Behavior |
|----------|----------|
| `random` | picks a legal action at random |
| `aggressive` | attacks if possible, else best move toward objectives, else deploys |
| `defensive` | deploys first, moves defensively, rarely attacks |

Change the opponent by configuring the simulation:

```kukicha
cfg := learn.NewConfig()
cfg.AIStrategy = gamepkg.AIStrategyNameAGGRESSIVE
sim := learn.NewSimulation(cfg)
sim.Run(PlayTurn)
```

The example in `10-strategy-ladder` is the "kill first" rung: pick the
attack that kills (`WillKill`), else the highest damage, else march,
else deploy.

```kukicha
for a in actions
    switch a as v
        when gamepkg.AttackAction
            if not found or v.WillKill or v.Damage > best_damage
                best_damage = v.Damage
                best_attacker = v.AttackerID as int
                best_defender = v.DefenderID as int
                found = true
```

## The ladder

Your goal is to climb these rungs, each one beating the last:

1. **Random** — `strategy=random` behavior, reimplemented with
   `random.Int(0, len(actions))`.
2. **MarchBot** — always deploy the strongest reserve, always march
   (your chapters 4-6 code).
3. **Killer** — the chapter example: kill-first attacks.
4. **Aggressive-lite** — attacks, then march toward *objectives*
   (crystal + uncaptured generators), then deploy.
5. **Your own** — a strategy with a named personality and a weakness
   the next rung exploits.

## Beating the AI

A note on balance: the game's AI is deliberately modest. A pure
MarchBot with kill-first attacks will beat the random strategy but
lose to aggressive on a small board. The interesting fights happen
when you add generator raids (each disabled generator lowers the
crystal requirement by 2 tokens — the aggressive strategy values them
for exactly this reason).

## Your turn

1. Fight the ladder: run your chapter-9 example against `random`,
   then `aggressive`, then `defensive`. Record wins/losses and turn
   counts. (Run with `timeout 120` — aggressive games can run long.)
2. Add generator raids: when no attack is available, march toward the
   *nearest uncontested generator* instead of the crystal. Reuse
   `api.Board()` + the `Distance` helper — or simpler: march toward
   (6,6), the nearest generator to your corner.
3. Write a `Defender` that keeps one token on the crystal cell
   (12,12) at all times and re-deploys to replace losses. Does it
   beat your Killer?
