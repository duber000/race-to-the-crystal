# Development Deployment

**This directory contains development quadlet configuration files for local testing.**

## Documentation

**Complete deployment documentation has moved to:**

**[deployment/docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)**

## Quick Reference

This directory contains:
- `game-api.container` - Game server quadlet (development mode)
- `caddy.container` - Caddy reverse proxy quadlet (development mode)
- `game-net.network` - Podman network configuration

## Quick Start

```bash
# Build containers
cd ../dockerfiles
podman build -f Dockerfile -t localhost/race-to-the-crystal:latest ../..
podman build -f Dockerfile.caddy -t localhost/race-caddy:latest ../..

# Deploy
cp ../development/*.{container,network} ~/.config/containers/systemd/
systemctl --user daemon-reload
systemctl --user start game-api.service caddy.service

# Access at http://localhost:8880
```

## Differences from Production

Development configuration:
- Uses HTTP (not HTTPS)
- Listens on localhost only
- No resource limits
- Development JWT secrets (not secure)
- No rate limiting

## Files in This Directory

- **game-api.container** - Game server without resource limits
- **caddy.container** - Caddy proxy without HTTPS
- **game-net.network** - Podman network (10.89.0.0/24)

## Related Documentation

- [Deployment Guide](../docs/DEPLOYMENT.md) - Complete deployment guide
- [Mercure Guide](../docs/MERCURE.md) - Mercure configuration
- [Dockerfiles](../dockerfiles/) - Container image definitions
