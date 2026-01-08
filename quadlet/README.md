# Systemd Quadlet Files

This directory contains systemd quadlet files for containerized deployment of Race to the Crystal using podman.

## Files

- **game-net.network** - Podman network configuration (game-net)
- **game-api.container** - FastAPI game server container
- **caddy.container** - Caddy reverse proxy with Mercure/Vulcain support
- **mercure.container** - Mercure hub for real-time updates

## Prerequisites

1. **Build the Caddy image** (requires custom binary with mercure/vulcain plugins):
   ```bash
   chmod +x caddy
   podman build -f Dockerfile.caddy -t localhost/race-caddy:latest .
   ```

2. **Build the game API image**:
   ```bash
   podman build -t localhost/race-to-the-crystal:latest .
   ```

## Installation (Rootless/User Mode)

```bash
# Create user quadlet directory
mkdir -p ~/.config/containers/systemd

# Copy quadlet files
cp *.container *.network ~/.config/containers/systemd/

# Copy Caddyfile
cp ../Caddyfile ~/.config/containers/systemd/

# Reload systemd and start services
systemctl --user daemon-reload
systemctl --user enable --now game-api.service caddy.service mercure.service
```

## Container Names (DNS)

Podman's internal DNS resolves container names:
- `race-game-api` - Game API server (listens on port 8080 internally)
- `race-caddy` - Caddy reverse proxy
- `race-mercure` - Mercure SSE hub

## Ports

- **Caddy**: http://127.0.0.1:8880 (internal port 80)
- **Game API**: http://race-game-api:8080 (internal), http://127.0.0.1:8888 (TCP desktop clients)
- **Mercure**: http://race-mercure:3000 (internal SSE hub)

## Service Management

```bash
# Check status
systemctl --user status game-api.service

# View logs
journalctl --user -u game-api.service -f

# Restart service
systemctl --user restart caddy.service

# Stop all services
systemctl --user stop game-api.service caddy.service mercure.service
```

## Troubleshooting

### DNS Resolution
Verify containers can resolve each other:
```bash
podman exec race-caddy nslookup race-game-api
```

### Services not found
If systemd can't find the services, ensure the quadlet generator is working:
```bash
/usr/libexec/podman/quadlet -user -dryrun
```

### Permission denied on caddy binary
Ensure the caddy binary is executable:
```bash
chmod +x caddy
podman build -f Dockerfile.caddy -t localhost/race-caddy:latest .
```

## Production Notes

1. **Secrets**: Don't hardcode JWT tokens. Use EnvironmentFiles or systemd drop-ins
2. **SSL/TLS**: Caddy handles certificates automatically
3. **Auto-updates**: Consider using `podman auto-update`
