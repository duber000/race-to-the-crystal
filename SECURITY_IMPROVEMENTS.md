# Security Improvements Summary

This document summarizes the security improvements implemented for production deployment of Race to the Crystal.

## Overview

Comprehensive security hardening completed for production deployment. All high and medium priority security tasks have been implemented and tested.

## Completed Improvements

### 1. Rate Limiting (Priority: P1 - CRITICAL)

**Implementation:** Three-layer rate limiting system

#### Connection Rate Limiting
- **Limit:** 8 concurrent connections per IP address
- **Window:** 60-second sliding window
- **Purpose:** Prevents connection flooding/DoS attacks
- **Features:**
  - IP-based tracking using X-Real-IP / X-Forwarded-For headers
  - Automatic cleanup of expired connections
  - Graceful error messages to legitimate users

#### Action Rate Limiting
- **Algorithm:** Token bucket
- **Limit:** 5 actions per second per player
- **Burst Capacity:** 10 actions (allows legitimate bursts)
- **Purpose:** Prevents action spamming and gameplay abuse
- **Applied To:** MOVE, ATTACK, DEPLOY, END_TURN actions

#### Game Creation Rate Limiting
- **Limit:** 10 games per player per hour
- **Window:** 1-hour sliding window
- **Purpose:** Prevents lobby spam and resource exhaustion

**Files:**
- `server/rate_limiter.py` - Rate limiting module (300 lines)
- `server/websocket_handler.py` - Integration into WebSocket handler
- `tests/test_rate_limiter.py` - Test suite (15 tests, all passing)

**Testing:**
```bash
# Run tests
uv run pytest tests/test_rate_limiter.py -v

# Results: 15 passed in 2.64s
# - Connection limits verified
# - Action throttling verified
# - Game creation limits verified
# - Independent limits per IP/player verified
```

---

### 2. Input Validation & Sanitization (Priority: P2 - MEDIUM)

**Implementation:** Comprehensive validation for all user inputs

#### Player Name Validation
- **Max Length:** 30 characters
- **Allowed Characters:** Alphanumeric, spaces, underscores, hyphens, periods
- **Regex:** `^[a-zA-Z0-9_\- \.]+$`
- **Blocked:**
  - Control characters (ASCII 0-31)
  - Shell metacharacters: `;`, `&`, `|`, `$`, `>`, `<`, `` ` ``, `\`
  - Directory traversal patterns (`..`)
  - Leading/trailing whitespace
- **Applied:** `_handle_connect()` before accepting player

#### Game Name Validation
- **Max Length:** 50 characters
- **Same restrictions as player names**
- **Additional checks:** Same security validations
- **Applied:** `_handle_create_game()` before creating lobby

#### Game Parameter Validation
- **max_players:**
  - Type: Must be integer
  - Range: 2-4 players only
  - Prevents: Invalid configurations, resource exhaustion

#### WebSocket Message Size Limit
- **Previous:** 10 MB (excessive, memory exhaustion risk)
- **New:** 64 KB (sufficient for all game messages)
- **Typical Message Size:** < 10 KB
- **Purpose:** Prevents memory exhaustion attacks

**Files:**
- `server/websocket_handler.py` - Validation integrated into handlers
- `server/lobby.py` - Validation functions (`validate_player_name()`, `validate_game_name()`)

**Validation Flow:**
1. Input received from client
2. Validation function called (raises `ValueError` on failure)
3. Error logged with `logger.warning()` for security monitoring
4. Client receives clear error message
5. Request rejected before any processing

---

### 3. Container Resource Limits (Priority: P2 - MEDIUM)

**Implementation:** Resource constraints in production quadlet files

#### Game API Container
```ini
Memory=1G                # Max memory usage
MemorySwap=2G            # Max memory + swap
CPUQuota=100%            # Max 1 CPU core
PidsLimit=100            # Max 100 processes/threads
```

#### Caddy Container
```ini
Memory=256M              # Max memory usage
MemorySwap=512M          # Max memory + swap
CPUQuota=50%             # Max 0.5 CPU cores
PidsLimit=50             # Max 50 processes/threads
```

**Files:**
- `quadlets-production/game-api.container`
- `quadlets-production/caddy.container`

**Purpose:**
- Prevents resource exhaustion
- Ensures fair resource sharing
- Protects host system from runaway processes
- Appropriate for 4-player maximum capacity

---

### 4. Production Configuration Separation

**Implementation:** Dedicated production configuration folder

**Structure:**
```
quadlets-production/
├── Caddyfile                    # HTTPS with domain, restricted CORS
├── caddy.container              # Resource limits, secrets file
├── game-api.container           # Resource limits, production URLs
├── game-net.network             # Podman network config
├── race-secrets.env.template    # Secret generation template
└── README.md                    # Deployment guide
```

**Benefits:**
- Local development configs unchanged (`quadlet/` folder)
- Production-specific settings isolated
- Easy deployment and rollback
- Secrets never committed to git

**Key Differences from Development:**
- HTTPS enabled with custom domain
- Secrets loaded from file (not inline)
- CORS restricted to production domain
- Resource limits enforced
- Security headers enabled
- Mercure public URL configured for external access

---

## Security Checklist

### Completed Items
- [x] Rate limiting for connections (8 per IP)
- [x] Rate limiting for actions (5 per second per player)
- [x] Rate limiting for game creation (10 per hour per player)
- [x] Input validation for player names
- [x] Input validation for game names
- [x] Input validation for game parameters
- [x] WebSocket message size limit (64 KB)
- [x] Container memory limits
- [x] Container CPU limits
- [x] Container PID limits
- [x] Production config separation
- [x] Secrets template created
- [x] Comprehensive test coverage (15 tests)

### Deployment Tasks
- [ ] Generate production JWT secrets
- [ ] Configure DNS for production domain
- [ ] Deploy to production server
- [ ] Enable HTTPS with Let's Encrypt
- [ ] Configure cloud provider firewall
- [ ] Test rate limits under load
- [ ] Monitor resource usage in production
- [ ] Set up log monitoring (optional)

### Not Implemented (Out of Scope)
- Authentication system (deferred - future feature)
- Monitoring/metrics (optional)
- Automated backups (game state is ephemeral)

---

## Rate Limit Configuration

### Tuning Parameters

All rate limits are configurable in `server/rate_limiter.py`:

```python
MAX_CONNECTIONS_PER_IP = 8           # Max concurrent connections per IP
MAX_ACTIONS_PER_SECOND = 5           # Max actions per player per second
MAX_GAMES_CREATED_PER_HOUR = 10      # Max games created per player per hour
CONNECTION_WINDOW_SECONDS = 60       # Time window for connection tracking
```

### Recommended Adjustments

Based on production usage, consider adjusting:

- **MAX_CONNECTIONS_PER_IP**: Increase if legitimate users hit limit (e.g., multiple family members)
- **MAX_ACTIONS_PER_SECOND**: Decrease if action spam still occurs, increase if legitimate fast play affected
- **MAX_GAMES_CREATED_PER_HOUR**: Adjust based on usage patterns

### Monitoring Rate Limits

Check rate limiter stats:
```python
stats = rate_limiter.get_stats()
# Returns:
# {
#     "active_ips": 5,
#     "total_active_connections": 8,
#     "tracked_players_actions": 4,
#     "tracked_players_game_creation": 2
# }
```

---

## Validation Configuration

### Character Restrictions

Configured in `server/lobby.py`:

```python
MAX_PLAYER_NAME_LENGTH = 30
MAX_GAME_NAME_LENGTH = 50
ALLOWED_PLAYER_NAME_CHARS = r"^[a-zA-Z0-9_\- \.]+$"
ALLOWED_GAME_NAME_CHARS = r"^[a-zA-Z0-9_\- \.]+$"
```

### Security Filters

Both player and game names are checked for:
- Control characters (ASCII 0-31)
- Shell metacharacters: `;& |$><\``
- Directory traversal: `..`
- Whitespace abuse: leading/trailing spaces

---

## Testing

### Rate Limiting Tests

Run comprehensive test suite:
```bash
uv run pytest tests/test_rate_limiter.py -v
```

**Test Coverage:**
- Token bucket refill logic
- Sliding window expiration
- Connection rate limits
- Action rate limits
- Game creation rate limits
- Independent limits per IP/player
- Statistics tracking

### Manual Testing

**Test Rate Limits:**
1. Open 9+ browser tabs to same server → 9th connection should be rejected
2. Spam move actions rapidly → Should see rate limit error
3. Create 11 games quickly → 11th should be rejected

**Test Validation:**
1. Try player name with special chars (`test; rm -rf /`) → Should be rejected
2. Try game name with 100 chars → Should be rejected
3. Try max_players=10 → Should be rejected

---

## Deployment Notes

### Production Checklist

Before deploying to production:

1. **Generate Secrets:**
   ```bash
   PUBLISHER_JWT=$(openssl rand -base64 32)
   SUBSCRIBER_JWT=$(openssl rand -base64 32)
   ```

2. **Create Secrets File:**
   ```bash
   cat > ~/.config/containers/systemd/race-secrets.env <<EOF
   MERCURE_PUBLISHER_JWT=$PUBLISHER_JWT
   MERCURE_SUBSCRIBER_JWT=$SUBSCRIBER_JWT
   EOF
   chmod 600 ~/.config/containers/systemd/race-secrets.env
   ```

3. **Deploy Configs:**
   ```bash
   cp quadlets-production/*.container ~/.config/containers/systemd/
   cp quadlets-production/*.network ~/.config/containers/systemd/
   cp quadlets-production/Caddyfile ~/.config/containers/systemd/
   ```

4. **Start Services:**
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now game-api.service caddy.service
   ```

### Monitoring

Watch for rate limit violations:
```bash
journalctl --user -u game-api.service -f | grep -i "rate limit"
```

Watch for validation failures:
```bash
journalctl --user -u game-api.service -f | grep -i "invalid"
```

### Adjusting Limits

If legitimate users are being rate limited:

1. Edit `server/rate_limiter.py`
2. Adjust constants (e.g., `MAX_CONNECTIONS_PER_IP = 12`)
3. Rebuild container: `podman build -t localhost/race-to-the-crystal:latest .`
4. Restart service: `systemctl --user restart game-api.service`

---

## Impact on Gameplay

### Normal Gameplay - No Impact

Rate limits designed to allow normal gameplay:
- **Actions:** 5/second allows rapid play (60+ moves per minute)
- **Burst:** 10-action burst for initial rapid moves
- **Connections:** 8 per IP supports entire household

### Prevented Attacks

- **Connection Flooding:** Max 8 connections per IP prevents DoS
- **Action Spam:** 5/second prevents automated action spam
- **Lobby Spam:** 10 games/hour prevents lobby pollution
- **Memory Exhaustion:** 64 KB message limit prevents memory attacks
- **Code Injection:** Input validation prevents shell injection
- **Directory Traversal:** Validation prevents path manipulation

---

## Future Improvements

Potential future enhancements (not required for initial deployment):

1. **Authentication System:**
   - User accounts and login
   - Persistent player profiles
   - Friend lists and private games

2. **Advanced Rate Limiting:**
   - Adaptive limits based on player behavior
   - Whitelist for trusted IPs
   - Progressive penalties for repeat offenders

3. **Monitoring & Metrics:**
   - Prometheus metrics export
   - Grafana dashboards
   - Alerting for anomalies

4. **DDoS Protection:**
   - Cloudflare integration
   - Geographic rate limiting
   - Challenge-response for suspicious traffic

---

## References

- **Rate Limiting Implementation:** `server/rate_limiter.py`
- **Validation Functions:** `server/lobby.py`
- **WebSocket Integration:** `server/websocket_handler.py`
- **Tests:** `tests/test_rate_limiter.py`
- **Production Configs:** `quadlets-production/`
- **Deployment Guide:** `quadlets-production/README.md`
- **TODO Tracking:** `DEPLOY_TODO.md`
