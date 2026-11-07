# Information about the game

## Core Game Rules

* grid board (18x18)

* each player has a group of 20 dice tokens that represent their life and move around the board
  * players start with **3 tokens already deployed** in their starting corner (3x3 grid area)
  * remaining 17 tokens can be deployed from reserve during gameplay to the same 3x3 corner area
  * **Deployment Zones** (3x3 grid in each corner):
    - Player 1 (bottom-left): cells (0,0) to (2,2)
    - Player 2 (bottom-right): cells (15,0) to (17,2)
    - Player 3 (top-left): cells (0,15) to (2,17)
    - Player 4 (top-right): cells (15,15) to (17,17)
* 2-4 players per game
* goal is to charge the central crystal to 80
* players start from each corner of the board
* power crystal is powered by 4 generators in each quadrant of the board
* players win by holding the crystal (+10 charge per turn) and holding generators (+5 per turn, Reactor +10) until their charge reaches 80
* each generator is captured by holding it with 2 tokens for 2 consecutive end-of-turn checks; capture is recapturable — lose the tokens and you lose the buff
* **Token Stacking**: Multiple friendly tokens can occupy the same generator or crystal cell (required for capture)
* **Token Stacking Continued**: Multiple friendly tokens can't occupy the same space otherwise
* tokens have these numbers on their dice representing their health: 10, 8, 6, 4
* **Health Rounding**: After taking damage, token health rounds DOWN to the nearest valid value (10, 8, 6, 4)
  - 10hp token takes 3 damage → 7hp → rounds to 6hp (survives)
  - 8hp token takes 5 damage → 3hp → rounds to 0hp (dies, no valid value below 4)
  - 6hp token takes 2 damage → 4hp (exact match, no rounding)
  - If resulting health is below 4, the token dies
* **Movement is dynamic**: tokens with **health 10-8** move 2 spaces, **6** move 3, **4** move 4
  - This means damaged tokens become more mobile!
* each token attacks for 1/2 of their value (10hp → 5 damage, 8hp → 4 damage, etc)
* attacker takes counter damage equal to defender's attackPower/2; defenders on a generator/crystal get +1 bonus; if attacker has 2+ allies adjacent to the defender, counter is negated (flanking)
* crystal pulses: at each objective update, 1 damage to all tokens adjacent to the crystal
* mystery squares (distributed throughout the board) trigger random events:
  - Heads: heal token to full health
  - Tails: teleport token back to deployment area (first empty cell in 3x3 corner zone)

## Generator Buffs (hold to keep)

* **MOVE_ENGINE** (top-left quadrant): +1 move to all tokens of the holder
* **REACTOR** (top-right quadrant): +10 crystal charge per turn (vs +5 for others)
* **FORGE** (bottom-left quadrant): heal 2 HP per turn to owner's tokens adjacent to this generator
* **DEPLOY_ARRAY** (bottom-right quadrant): holder may deploy an extra token per turn (stays in MOVEMENT phase after first deploy)

## Visual Elements

### Generators
Each quadrant has a generator positioned at the center:
- **Bottom-Left**: (4, 4)
- **Bottom-Right**: (13, 4)
- **Top-Left**: (4, 13)
- **Top-Right**: (13, 13)

Generators have enhanced glow effects to make them more visible. When a generator is captured, the visual connection line to the crystal appears in the holder's color.

### Crystal
Located at the center of the board (9, 9), the crystal is the objective. Flowing orange lines extend from each captured generator toward the crystal, providing visual indication of which generators are powering it.
