# Information about the game

## Core Game Rules

* grid board (24x24)

* each player has a group of 20 dice tokens that represent their life and move around the board
  * players start with **3 tokens already deployed** in their starting corner (3x3 grid area)
  * remaining 17 tokens can be deployed from reserve during gameplay to the same 3x3 corner area
  * **Deployment Zones** (3x3 grid in each corner):
    - Player 1 (bottom-left): cells (0,0) to (2,2)
    - Player 2 (bottom-right): cells (21,0) to (23,2)
    - Player 3 (top-left): cells (0,21) to (2,23)
    - Player 4 (top-right): cells (21,21) to (23,23)
* 2-4 players per game
* goal is to capture a power crystal in the middle of the board
* players start from each corner of the board
* power crystal is empowered by 4 generators in each quadrant of the board
* players win by holding the power crystal for 3 turns with 12 tokens
* each generator is "taken out" by 2 tokens holding it for 2 turns
* each generator "taken out" reduces the tokens needed to hold the crystal by 2
* **Token Stacking**: Multiple friendly tokens can occupy the same generator or crystal cell (required for capture)
* **Token Stacking Continued**: Multiple friendly tokens can't occupy the same space otherwise
* tokens have these numbers on their dice representing their health: 10, 8, 6, 4
* **Movement is dynamic**: tokens with **current health of 7 or more** move 1 space, tokens with **6 or less** move 2 spaces
  - This means damaged tokens become more mobile! An 8hp token that takes 4 damage becomes 4hp and can move 2 spaces
* each token attacks for 1/2 of their value (10hp → 5 damage, 8hp → 4 damage, etc)
* attacker takes no damage when attacking
* mystery squares (distributed throughout the board) trigger random events:
  - Heads: heal token to full health
  - Tails: teleport token back to deployment area (first empty cell in 3x3 corner zone)

## Visual Elements

### Generators
Each quadrant has a generator positioned at the center:
- **Bottom-Left**: (6, 6)
- **Bottom-Right**: (18, 6)
- **Top-Left**: (6, 18)
- **Top-Right**: (18, 18)

Generators have enhanced glow effects to make them more visible. When a generator is captured (disabled), the visual connection line to the crystal disappears.

### Crystal
Located at the center of the board (12, 12), the crystal is the objective. Flowing orange lines extend from each active generator toward the crystal, providing visual indication of which generators are still in play.
