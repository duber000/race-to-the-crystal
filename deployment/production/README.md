# Production Deployment

**This directory contains production quadlet configuration files.**

## Documentation

**Complete production deployment documentation has moved to:**

**[deployment/docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)**

## Quick Reference

This directory contains:
- `game-api.container` - Game server quadlet with resource limits
- `caddy.container` - Caddy reverse proxy quadlet
- `Caddyfile` - Production Caddy configuration with HTTPS
- `game-net.network` - Podman network configuration
- `race-secrets.env.template` - Template for JWT secrets

## Quick Start

```bash
# See full deployment guide:
cat ../docs/DEPLOYMENT.md

# Or jump to production section:
# deployment/docs/DEPLOYMENT.md#production-deployment
```

## Files in This Directory

- **game-api.container** - Game server with resource limits and secrets
- **caddy.container** - Caddy proxy with resource limits
- **Caddyfile** - HTTPS configuration with Let's Encrypt
- **game-net.network** - Podman network (10.89.0.0/24)
- **race-secrets.env.template** - Secrets file template

## Related Documentation

- [Deployment Guide](../docs/DEPLOYMENT.md) - Complete deployment documentation
- [Mercure Guide](../docs/MERCURE.md) - Mercure SSE configuration
- [Dockerfiles](../dockerfiles/) - Container image definitions
