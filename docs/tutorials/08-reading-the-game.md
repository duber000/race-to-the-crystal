# Chapter 8: Reading the Game — the Action List

**Example: `learn/examples/03-first-strategy/`**

So far you've been guessing what moves are legal. The game will simply
*tell you*: `api.Actions()` returns the typed list of everything you
may do right now.

## The four action variants

`api.Actions()` returns a list whose items are one of four variant
cases — a tagged union:

| Variant | Fields | Meaning |
|---------|--------|---------|
| `MoveAction` | `TokenID`, `ValidDestinations` | move that token to one of these cells |
| `AttackAction` | `AttackerID`, `DefenderID`, `Damage`, `WillKill` | attack, with the damage math done |
| `DeployAction` | `HealthValue`, `Positions`, `Remaining` | deploy from reserve to one of these cells |
| `EndTurnAction` | — | end your turn |

The list is filtered by phase and turn: during the AI's turn it's
empty; during your MOVEMENT phase it contains only moves and deploys;
during ACTION only attacks and the end-turn action.

## Switching over the variants

```kukicha
func DoAttack(api: reference learn.LearnerAPI, actions: list of gamepkg.ActionResponse) bool
    for a in actions
        switch a as v
            when gamepkg.AttackAction
                _ = api.Attack(v.AttackerID as int, v.DefenderID as int)
                return true
            default
                continue
    return false
```

- `switch a as v` binds the narrowed value: inside the `AttackAction`
  arm, `v` is the attack with its typed fields.
- `v.AttackerID as int` converts the game's typed token id to the
  plain int the LearnerAPI expects.
- The example chains helpers: attack if possible, else move, else
  deploy, else end. That ordering *is* a strategy.

## Why this matters

Writing your own move generator means reimplementing the game's rules
(movement range, occupancy, phase legality). `api.Actions()` already
did that work — your strategy becomes *choosing among legal options*,
which is the actual strategic content.

## Your turn

1. The example takes `ValidDestinations[0]` — the first legal cell,
   usually the wrong one. Instead pick the destination with the best
   score (nearest the crystal — you have the `Distance` helper).
2. Attack is first in the chain. What happens if you reorder to move
   first, attack second? Why is that a worse strategy?
3. The `AttackAction.WillKill` field tells you if the attack finishes
   the target. Write `BestAttack` that prefers killing blows (this is
   the exact pattern used in chapter 9's example).
