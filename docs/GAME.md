# Information about the game

## Core Game Rules

* grid board (24x24)

* each player has a group of 20 dice tokens that represent their life and move around the board
  * players start with **3 tokens already deployed** in their starting corner
  * remaining 17 tokens can be deployed from reserve during gameplay
* 2-4 players per game
* goal is to capture a power crystal in the middle of the board
* players start from each corner of the board
* power crystal is empowered by 4 generators in each quadrant of the board
* **Visual Feedback**: Flowing animated lines connect active generators to the crystal; lines disappear when generators are captured
* players win by holding the power crystal for 3 turns with 12 tokens
* each generator is "taken out" by 2 tokens holding it for 2 turns
* each generator "taken out" reduces the tokens needed to hold the crystal by 2
* **Token Stacking**: Multiple friendly tokens can occupy the same generator or crystal cell (required for capture)
* tokens have these numbers on their dice representing their health: 10, 8, 6, 4
* 6 and 4 health tokens can move two spaces, 10 and 8 health tokens move 1 space
* each token attacks for 1/2 of their value (10hp → 5 damage, 8hp → 4 damage, etc)
* attacker takes no damage when attacking
* mystery squares (distributed throughout the board) trigger random events:
  - Heads: heal token to full health
  - Tails: teleport token back to starting corner

## Visual Elements

### Generators
Each quadrant has a generator positioned at the center:
- **Top-Left**: (6, 6)
- **Top-Right**: (18, 6)
- **Bottom-Left**: (6, 18)
- **Bottom-Right**: (18, 18)

Generators have enhanced glow effects to make them more visible. When a generator is captured (disabled), the visual connection line to the crystal disappears.

### Crystal
Located at the center of the board (12, 12), the crystal is the objective. Flowing orange lines extend from each active generator toward the crystal, providing visual indication of which generators are still in play.
