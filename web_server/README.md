# Web Client

Browser-based 3D client for Race to the Crystal using Babylon.js 8.

## Quick Start

```bash
# Start the unified server
uv run race-unified-server

# Open browser to http://localhost:8080
```

## Documentation

**Complete documentation has moved to [docs/WEB.md](../docs/WEB.md)**

Topics covered:
- Architecture and integration with unified server
- WebSocket protocol and message types
- Controls and gameplay
- Development guide
- Deployment and troubleshooting

## Migration Notice

The standalone FastAPI server (`race-web-server`) is deprecated. Use `race-unified-server` instead for full desktop + web client support.
