1. Port MercurePublisher from web_server/mercure_publisher.py to the unified server
  2. Add Mercure publishing to server/game_server.py when broadcasting game state
  3. Add Vulcain Link headers to server/http_handler.py
  4. Integrate the mercure_client.js with the existing game_client.js
  5. Add fallback logic (WebSocket if Mercure unavailable)
