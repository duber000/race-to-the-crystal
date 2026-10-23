# MCP proxy for Race to the Crystal (Phase 2.1 complete)

Thin stdio MCP server built on `stdlib/mcp`. Run it with a game server URL,
token, and game id:

```
GAME_SERVER_URL=http://localhost:8080 GAME_TOKEN=<jwt> GAME_ID=<gid> ./mcp
```

Tools: get_visible_state, get_legal_actions, move_token, attack, deploy_token,
end_turn, say. No game logic, no state — proxy only.
