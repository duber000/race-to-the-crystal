# Production Deployment Checklist

## Overview
This document tracks deployment tasks for Race to the Crystal to an internet-facing server.

**Configuration:**
- Maximum 4 players at any given time
- TCP port 8888 (desktop clients) remains internal-only
- Web clients via HTTPS (port 8880)
- Rootless containers running as non-root user

## Deployment Checklist

### 1. Generate Strong JWT Secrets ⚠️ CRITICAL
**Status:** TODO
**Priority:** P0

**Current Issue:**
- `MERCURE_PUBLISHER_JWT=dev_key` (game-api.container:19)
- `MERCURE_PUBLISHER_JWT=dev_secret_key` (caddy.container:18)
- `MERCURE_SUBSCRIBER_JWT=dev_secret_key` (caddy.container:19)

**Tasks:**
- [ ] Generate strong random JWT secrets (32+ bytes)
- [ ] Create production environment file: `/etc/race-to-the-crystal/secrets.env`
- [ ] Update quadlet files to use `EnvironmentFile` instead of inline secrets
- [ ] Secure file permissions (600, root-only or service-user-only)
- [ ] Document secret rotation procedure

**Commands:**
```bash
# Generate secrets
PUBLISHER_JWT=$(openssl rand -base64 32)
SUBSCRIBER_JWT=$(openssl rand -base64 32)

# Create secrets file
sudo mkdir -p /etc/race-to-the-crystal
sudo tee /etc/race-to-the-crystal/secrets.env > /dev/null <<EOF
MERCURE_PUBLISHER_JWT=$PUBLISHER_JWT
MERCURE_SUBSCRIBER_JWT=$SUBSCRIBER_JWT
EOF
sudo chmod 600 /etc/race-to-the-crystal/secrets.env
```

---

### 2. Enable HTTPS/TLS with Domain ⚠️ CRITICAL
**Status:** TODO
**Priority:** P0

**Current Issue:**
- Caddyfile uses `http://:80` (plain HTTP, no TLS)
- No domain name configured

**Tasks:**
- [ ] Verify DNS: `your-domain.com` points to server IP
- [ ] Update Caddyfile to use domain name (enables auto-HTTPS)
- [ ] Ensure ports 80/443 are accessible for Let's Encrypt validation
- [ ] Test certificate auto-renewal
- [ ] Verify HTTPS redirect works

**Updated Caddyfile:**
```caddyfile
{
    order mercure before respond
}

your-domain.com {
    # Caddy automatically provisions Let's Encrypt certificates

    # Embedded Mercure Hub configuration
    mercure {
        publisher_jwt {env.MERCURE_PUBLISHER_JWT}
        subscriber_jwt {env.MERCURE_SUBSCRIBER_JWT}
        anonymous
        cors_origins https://your-domain.com
    }

    # Proxy to FastAPI backend
    reverse_proxy race-game-api:8080 {
        header_up Host {http.request.header.Host}
        header_up X-Real-IP {http.request.remote.host}
        header_up X-Forwarded-For {http.request.remote.host}
        header_up X-Forwarded-Proto {http.request.proto}
    }
}
```

---

### 3. Fix Mercure Public URL ⚠️ CRITICAL
**Status:** TODO
**Priority:** P0

**Current Issue:**
- `MERCURE_PUBLIC_URL=http://127.0.0.1:8880/.well-known/mercure` (localhost-only)
- Web clients from external networks cannot connect

**Tasks:**
- [ ] Update game-api.container environment variable
- [ ] Update any hardcoded references in web client code
- [ ] Test from external network after deployment

**Updated Config:**
```ini
Environment=MERCURE_PUBLIC_URL=https://your-domain.com/.well-known/mercure
```

---

### 4. Restrict CORS Origins ⚠️ HIGH
**Status:** TODO
**Priority:** P1

**Current Issue:**
- `cors_origins *` allows any website to embed/access the game

**Tasks:**
- [ ] Update Caddyfile to restrict CORS to domain only
- [ ] Test web client still works after restriction

**Already covered in Task #2 Caddyfile update**

---

### 5. Add Rate Limiting ✅ COMPLETED
**Status:** COMPLETED
**Priority:** P1

**Implementation:**
Created comprehensive rate limiting system in `server/rate_limiter.py` with three layers:

1. **Connection Rate Limiting:**
   - Max 8 concurrent connections per IP address (4 players + buffer)
   - 60-second sliding window tracking
   - Automatic cleanup of expired connections
   - IP-based tracking using X-Real-IP / X-Forwarded-For headers

2. **Action Rate Limiting:**
   - Token bucket algorithm (5 actions/second per player)
   - Burst capacity of 10 actions (2x rate)
   - Prevents action spamming and DoS attacks
   - Applied to all game actions (MOVE, ATTACK, DEPLOY, END_TURN)

3. **Game Creation Rate Limiting:**
   - Max 10 games created per player per hour
   - Prevents lobby spam and resource exhaustion
   - Sliding window tracking

**Files Modified:**
- `server/rate_limiter.py` - New rate limiting module (300 lines)
- `server/websocket_handler.py` - Integrated rate limiting into WebSocket handler
- `tests/test_rate_limiter.py` - Comprehensive test suite (15 tests, all passing)

**Testing:**
- All 15 unit tests passing
- Connection limits verified
- Action throttling verified
- Game creation limits verified
- Independent limits per IP/player verified

---

### 6. Add Container Resource Limits ✅ COMPLETED
**Status:** COMPLETED
**Priority:** P2

**Implementation:**
Resource limits added to production quadlet files in `quadlets-production/` folder.

**Tasks Completed:**
- [x] Determined appropriate resource limits for 4 players
- [x] Added limits to production quadlet files
- [ ] Test under load (to be done during deployment)
- [ ] Monitor resource usage in production (to be done during deployment)

**Recommended Limits (4 players):**
```ini
# game-api.container
[Container]
Memory=1G
MemorySwap=2G
CPUQuota=100%
PidsLimit=100

# caddy.container
[Container]
Memory=256M
MemorySwap=512M
CPUQuota=50%
PidsLimit=50
```

---

### 7. Input Validation & Sanitization ✅ COMPLETED
**Status:** COMPLETED
**Priority:** P2

**Implementation:**
Integrated existing validation from `server/lobby.py` into WebSocket handlers and added new validations:

1. **Player Name Validation:**
   - Max 30 characters (MAX_PLAYER_NAME_LENGTH)
   - Allowed: alphanumeric, spaces, underscores, hyphens, periods
   - Regex: `^[a-zA-Z0-9_\- \.]+$`
   - Blocks: control characters, shell metacharacters (`;& |$><\`)
   - Prevents: directory traversal (`..`), leading/trailing whitespace
   - Applied in `_handle_connect()` before accepting player

2. **Game Name Validation:**
   - Max 50 characters (MAX_GAME_NAME_LENGTH)
   - Same character restrictions as player names
   - Same security checks (control chars, shell metacharacters)
   - Applied in `_handle_create_game()` before creating lobby

3. **Game Parameters Validation:**
   - `max_players`: must be integer between 2 and 4
   - Type checking and range validation
   - Prevents invalid game configurations

4. **WebSocket Message Size Limit:**
   - Reduced from 10 MB to 64 KB (`max_msg_size=64 * 1024`)
   - Prevents memory exhaustion attacks
   - Sufficient for all game messages (typically < 10 KB)

**Files Modified:**
- `server/websocket_handler.py` - Added validation to connection and game creation handlers
- `server/lobby.py` - Already contains `validate_player_name()` and `validate_game_name()` functions

**Validation Details:**
- All validation raises `ValueError` with descriptive error messages
- Errors logged with `logger.warning()` for security monitoring
- Client receives clear error message via `_send_error()`
- Malicious inputs rejected before any processing

---

### 8. TCP Port Security (Desktop Clients)
**Status:** DEFERRED
**Priority:** P3

**Current Decision:**
- Keep TCP port 8888 internal-only for now
- Only expose web client (HTTPS) to internet
- Desktop clients must connect via VPN/SSH tunnel

**Future Tasks (if exposing TCP):**
- [ ] Add TLS encryption to TCP protocol
- [ ] Add authentication to desktop client connections
- [ ] Use stunnel or similar TLS wrapper

---

## Production Quadlet Files

### game-api.container (Production)
```ini
[Unit]
Description=Race to the Crystal - FastAPI Game Backend
Documentation=https://github.com/duber000/race-to-the-crystal
After=network-online.target
Wants=network-online.target

[Container]
Image=localhost/race-to-the-crystal:latest
ContainerName=race-game-api
Network=game-net.network

# Environment configuration (non-sensitive)
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=TCP_PORT=8888
Environment=HTTP_PORT=8080
Environment=MERCURE_HUB_URL=http://race-caddy/.well-known/mercure
Environment=MERCURE_PUBLIC_URL=https://your-domain.com/.well-known/mercure
Environment=MERCURE_TOPIC_PREFIX=https://your-domain.com/game

# Secrets from file
EnvironmentFile=/etc/race-to-the-crystal/secrets.env

# Resource limits
Memory=1G
MemorySwap=2G
CPUQuota=100%
PidsLimit=100

[Service]
Type=notify
Restart=unless-stopped
RestartSec=5s

[Install]
WantedBy=default.target
```

### caddy.container (Production)
```ini
[Unit]
Description=Caddy Web Server with Mercure Support
Documentation=https://caddyserver.com
After=network-online.target game-api.service
Wants=network-online.target
Wants=game-api.service

[Container]
Image=localhost/race-caddy:latest
ContainerName=race-caddy
Network=game-net.network

# Publish ports (rootless - use firewalld forwarding for 80/443)
PublishPort=8880:80
PublishPort=8444:443

# Secrets from file
EnvironmentFile=/etc/race-to-the-crystal/secrets.env

# Mount Caddyfile configuration
Volume=%h/.config/containers/systemd/Caddyfile:/etc/caddy/Caddyfile:ro,Z

# Persistent certificate storage
Volume=%h/.local/share/containers/systemd/caddy/data:/data,Z
Volume=%h/.local/share/containers/systemd/caddy/config:/config,Z

# Resource limits
Memory=256M
MemorySwap=512M
CPUQuota=50%
PidsLimit=50

[Service]
Type=notify
Restart=unless-stopped
RestartSec=5s

[Install]
WantedBy=default.target
```

---

## Deployment Steps

### Pre-Deployment
2. [ ] Verify DNS: `dig your-domain.com` points to server

### Deployment
1. [ ] Complete Task #1: Generate JWT secrets
2. [ ] Complete Task #2: Update Caddyfile for HTTPS
3. [ ] Complete Task #3: Fix Mercure public URL
4. [ ] Complete Task #6: Add resource limits
5. [ ] Complete Task #8: Configure port forwarding
6. [ ] Copy updated quadlet files to production server
7. [ ] Rebuild containers on production server
8. [ ] Test from external network: `https://your-domain.com:8880`
9. [ ] Monitor logs for errors
10. [ ] Test full gameplay flow with 4 players

### Post-Deployment
1. [ ] Complete Task #5: Implement rate limiting
2. [ ] Complete Task #7: Add input validation
3. [ ] Monitor resource usage
4. [ ] Document any issues/lessons learned
5. [ ] Set up automated backups (game state, certificates)

---

## Testing Checklist

- [ ] DNS resolves correctly: `dig your-domain.com`
- [ ] HTTPS certificate valid: `curl -I https://your-domain.com:8880`
- [ ] Web client loads: Open `https://your-domain.com:8880` in browser
- [ ] WebSocket connects: Check browser console, no errors
- [ ] Mercure SSE connects: Check Network tab for EventSource connection
- [ ] Can create game and join lobby
- [ ] Can start game with 2-4 players
- [ ] Can move tokens, attack, deploy
- [ ] Can complete full game to win condition
- [ ] Rate limits work: Try spamming actions
- [ ] Resource limits work: Monitor container stats under load

---

## Rollback Plan

If deployment fails:
1. Stop production services: `systemctl --user stop game-api.service caddy.service`
2. Restore backup quadlet files
3. Restore backup Caddyfile
4. Restart services: `systemctl --user daemon-reload && systemctl --user start game-api.service caddy.service`
5. Revert DNS if needed

---

## Notes

- **Certificate Renewal:** Caddy handles Let's Encrypt renewal automatically
- **Secret Rotation:** Document procedure for rotating JWT secrets without downtime
- **Monitoring:** Consider adding basic health checks (curl endpoint every 5 min)
- **Backups:** Game state is in-memory only (no persistence) - consider adding if needed
