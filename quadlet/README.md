# Systemd Quadlet Files

This directory contains systemd quadlet files for containerized deployment of Race to the Crystal using podman.

## Files

- **game-net.network** - Podman network configuration (game-net)
- **game-api.container** - FastAPI game server container
- **caddy.container** - Caddy reverse proxy with Mercure support

## Prerequisites

1. **Build the Caddy image** (requires custom binary with mercure plugin):
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
systemctl --user enable --now game-api.service caddy.service
```

## Container Names (DNS)

Podman's internal DNS resolves container names:
- `race-game-api` - Game API server (listens on port 8080 internally)
- `race-caddy` - Caddy reverse proxy with embedded Mercure

## Ports

- **Caddy**: http://127.0.0.1:8880 (internal port 80)
- **Game API**: http://race-game-api:8080 (internal), http://127.0.0.1:8888 (TCP desktop clients)

## Service Management

```bash
# Check status
systemctl --user status game-api.service

# View logs
journalctl --user -u game-api.service -f

# Restart service
systemctl --user restart caddy.service

# Stop all services
systemctl --user stop game-api.service caddy.service
```

## Troubleshooting

### Check Service Status
View status of all game services:
```bash
systemctl --user list-units | grep -E "(game-api|caddy|game-net)"
systemctl --user status game-api.service caddy.service
```

### Check Container Logs
View real-time logs from containers:
```bash
# Via systemd journal
journalctl --user -u game-api.service -f
journalctl --user -u caddy.service -f

# Via podman
podman logs race-game-api --tail 50
podman logs race-caddy --tail 50
```

### Check Container Status
```bash
podman ps -a
podman inspect race-game-api | grep -A 10 "State"
```

### DNS Resolution
Verify containers can resolve each other:
```bash
podman exec race-caddy nslookup race-game-api
podman network inspect game-net
```

### Caddy Configuration Issues

**Caddyfile Syntax Error**:
If caddy.service fails with "unrecognized directive" errors:
```bash
# Test Caddyfile syntax
podman run --rm -v ~/.config/containers/systemd/Caddyfile:/test.caddyfile:ro,Z \
  localhost/race-caddy:latest caddy adapt --config /test.caddyfile

# Check service status
systemctl --user status caddy.service
```

Common issues:
- Variable definitions like `ANONYMOUS_JWT=...` are not supported in Caddy v2
- Use `http://:80` not `:80` for address blocks
- Ensure proper indentation

**CORS Headers Missing**:
If browser shows "CORS header 'Access-Control-Allow-Origin' missing":
```bash
# Test CORS headers on Mercure endpoint
curl -I http://localhost:8880/.well-known/mercure

# Should return:
# Access-Control-Allow-Origin: *
# Access-Control-Allow-Methods: GET, POST, OPTIONS
```

Fix: Ensure Caddyfile has CORS headers in the Mercure proxy block (see `Caddyfile`).

### After Code Changes

When you update game code, rebuild and restart:
```bash
# 1. Rebuild the container
podman build -t race-to-the-crystal:latest -f Dockerfile .

# 2. Restart the service
systemctl --user restart game-api.service

# 3. Verify it's running
systemctl --user status game-api.service

# 4. Check logs for errors
journalctl --user -u game-api.service -n 50
```

### Web Client Issues

**Browser Cache**:
If web client shows old code after updates, users must hard refresh:
- **Firefox/Chrome**: `Ctrl + Shift + R` (or `Cmd + Shift + R` on Mac)
- Or: F12 → Right-click reload → "Empty Cache and Hard Reload"

**Verify Served Files**:
Check if updated code is being served:
```bash
curl -s http://localhost:8880/static/game_client.js | grep "specific-string-from-your-update"
```

### Network Issues

**Check Port Bindings**:
```bash
podman port race-game-api
podman port race-caddy
ss -tlnp | grep -E "(8880|8888|8080)"
```

**Network Configuration**:
The game-net network uses 10.89.0.0/24:
- race-game-api: 10.89.0.3
- race-caddy: 10.89.0.4

```bash
podman network inspect game-net | grep -A 5 "Containers"
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

### Player Can't Move Tokens

Check server logs for action attempts:
```bash
journalctl --user -u game-api.service --since "5 minutes ago" | grep -E "(MOVE|ATTACK|INVALID)"
```

Common causes:
1. **Browser cache** - Player needs hard refresh
2. **Wrong turn** - Check whose turn it is in the HUD
3. **Action validation failure** - Check for INVALID_ACTION messages in console
4. **WebSocket disconnected** - Check browser console for connection errors

## Production Notes

1. **Secrets**: Don't hardcode JWT tokens. Use EnvironmentFiles or systemd drop-ins
2. **SSL/TLS**: Caddy handles certificates automatically
3. **Auto-updates**: Consider using `podman auto-update`
