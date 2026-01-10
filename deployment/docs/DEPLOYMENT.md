# Deployment Guide

This guide covers deploying Race to the Crystal using containerized deployment with Podman and systemd quadlets.

## Overview

Race to the Crystal can be deployed in two modes:

- **Development** - Local testing with minimal security (localhost only)
- **Production** - Internet-facing server with HTTPS, security hardening, and resource limits

## Quick Start

### Development Deployment

```bash
# Build containers
cd deployment/dockerfiles
podman build -f Dockerfile -t localhost/race-to-the-crystal:latest ../..
podman build -f Dockerfile.caddy -t localhost/race-caddy:latest ../..

# Deploy development configuration
cp deployment/development/*.{container,network} ~/.config/containers/systemd/
cp Caddyfile ~/.config/containers/systemd/

# Start services
systemctl --user daemon-reload
systemctl --user start game-api.service caddy.service

# Access at http://localhost:8880
```

### Production Deployment

See [Production Deployment](#production-deployment) section below for complete production setup with HTTPS, domain configuration, and security hardening.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Caddy (race-caddy)                             │
│  - HTTPS with Let's Encrypt                     │
│  - Embedded Mercure hub (SSE)                   │
│  - Reverse proxy to game API                    │
│  Ports: 8880 (HTTP/HTTPS), 8444 (future)        │
└─────────────────┬───────────────────────────────┘
                  │
                  │ Internal network (game-net)
                  │
┌─────────────────▼───────────────────────────────┐
│  Game API (race-game-api)                       │
│  - Unified server (TCP + HTTP/WebSocket)        │
│  - Desktop clients: TCP port 8888               │
│  - Web clients: HTTP/WebSocket port 8080        │
│  - Mercure publisher integration                │
└─────────────────────────────────────────────────┘
```

## Development Deployment

### Prerequisites

1. **Podman** installed
2. **Systemd** user mode enabled

### Build Images

```bash
cd deployment/dockerfiles

# Build game server
podman build -f Dockerfile -t localhost/race-to-the-crystal:latest ../..

# Build Caddy with Mercure plugin
chmod +x ../../caddy  # Ensure binary is executable
podman build -f Dockerfile.caddy -t localhost/race-caddy:latest ../..

# Verify images
podman images | grep race
```

### Deploy Configuration

```bash
# Create quadlet directory
mkdir -p ~/.config/containers/systemd

# Copy quadlet files
cp deployment/development/*.container ~/.config/containers/systemd/
cp deployment/development/*.network ~/.config/containers/systemd/
cp Caddyfile ~/.config/containers/systemd/

# Reload and start
systemctl --user daemon-reload
systemctl --user start game-api.service caddy.service
```

### Verify

```bash
# Check status
systemctl --user status game-api.service caddy.service

# Check containers
podman ps

# Test web client
curl http://localhost:8880/

# Open in browser
firefox http://localhost:8880
```

### Service Management

```bash
# View logs
journalctl --user -u game-api.service -f
journalctl --user -u caddy.service -f

# Restart service
systemctl --user restart game-api.service

# Stop services
systemctl --user stop game-api.service caddy.service
```

### Update Code

```bash
# Rebuild container
cd deployment/dockerfiles
podman build -f Dockerfile -t localhost/race-to-the-crystal:latest ../..

# Restart service
systemctl --user restart game-api.service

# Verify
journalctl --user -u game-api.service -n 50
```

## Production Deployment

### Prerequisites

#### 1. DNS Configuration

Verify DNS points to your production server:

```bash
dig your-domain.com
# Should return your server's public IP
```

#### 2. Create Non-Root User

For security, run containers as a dedicated non-root user:

```bash
# As root or sudo
useradd -m -s /bin/bash gameuser
loginctl enable-linger gameuser

# Verify lingering enabled (services persist after logout)
loginctl show-user gameuser | grep Linger
# Should show: Linger=yes
```

#### 3. Firewall Configuration

**Host Firewall:**

```bash
# Using firewalld (Fedora/RHEL/CentOS/AlmaLinux)
sudo firewall-cmd --permanent --add-port=8880/tcp
sudo firewall-cmd --permanent --add-port=8444/tcp
sudo firewall-cmd --reload

# Using ufw (Ubuntu/Debian)
sudo ufw allow 8880/tcp
sudo ufw allow 8444/tcp

# Verify
sudo firewall-cmd --list-ports  # firewalld
sudo ufw status                 # ufw
```

**Cloud Provider Firewall:**

If using AWS, GCP, Azure, DigitalOcean, etc., also configure their security groups/firewall to allow:
- TCP port 8880 (inbound)
- TCP port 8444 (inbound, optional)

#### 4. Build Container Images

```bash
# Log in as the non-root user
su - gameuser

# Clone repository
git clone <repo-url> ~/race-to-the-crystal
cd ~/race-to-the-crystal/deployment/dockerfiles

# Build Caddy image (includes Mercure plugin)
chmod +x ../../caddy
podman build -f Dockerfile.caddy -t localhost/race-caddy:latest ../..

# Build game API image
podman build -f Dockerfile -t localhost/race-to-the-crystal:latest ../..

# Verify
podman images | grep race
```

### Deployment Steps

#### Step 1: Generate Secrets

Generate strong random JWT secrets for Mercure:

```bash
# Generate secrets
PUBLISHER_JWT=$(openssl rand -base64 32)
SUBSCRIBER_JWT=$(openssl rand -base64 32)

# Create secrets file
mkdir -p ~/.config/containers/systemd
cat > ~/.config/containers/systemd/race-secrets.env <<EOF
MERCURE_PUBLISHER_JWT=$PUBLISHER_JWT
MERCURE_SUBSCRIBER_JWT=$SUBSCRIBER_JWT
EOF

# Secure the file
chmod 600 ~/.config/containers/systemd/race-secrets.env

# Verify
cat ~/.config/containers/systemd/race-secrets.env
```

**IMPORTANT:** Store these secrets in a password manager for future reference.

#### Step 2: Configure Domain

Update configuration files with your domain:

```bash
cd ~/race-to-the-crystal

# Update game-api.container
sed -i 's/your-domain.com/example.com/g' deployment/production/game-api.container

# Update Caddyfile
sed -i 's/your-domain.com/example.com/g' deployment/production/Caddyfile

# Replace example.com with your actual domain
```

#### Step 3: Deploy Configuration

```bash
# Create volume directories for Caddy
mkdir -p ~/.local/share/containers/systemd/caddy/{data,config}

# Copy production quadlet files
cp deployment/production/*.container ~/.config/containers/systemd/
cp deployment/production/*.network ~/.config/containers/systemd/
cp deployment/production/Caddyfile ~/.config/containers/systemd/

# Verify
ls -la ~/.config/containers/systemd/
```

#### Step 4: Start Services

```bash
# Reload systemd to recognize new quadlet files
systemctl --user daemon-reload

# Start services
systemctl --user start game-api.service caddy.service

# Check status
systemctl --user status game-api.service
systemctl --user status caddy.service
```

#### Step 5: Monitor Certificate Provisioning

Caddy automatically requests Let's Encrypt certificates on first HTTPS access:

```bash
# Watch for certificate provisioning
journalctl --user -u caddy.service -f

# Look for lines like:
# "successfully downloaded available certificate chains"
# "certificate obtained successfully"

# Test from external machine
curl -I https://your-domain.com:8880/
```

**Note:** Initial certificate provisioning may take 1-2 minutes.

#### Step 6: Verify Deployment

```bash
# Check containers
podman ps -a --filter "name=race-"

# Check logs
journalctl --user -u game-api.service -n 50
journalctl --user -u caddy.service -n 50

# Test local access
curl http://localhost:8880/

# Test external access (from different machine)
curl -I https://your-domain.com:8880/
```

### Post-Deployment

#### Test Full Functionality

1. Open browser: `https://your-domain.com:8880`
2. Create a new game
3. Join with 2-4 players (multiple browser windows/devices)
4. Test gameplay: move, attack, deploy tokens
5. Complete a full game to win condition
6. Check browser console for errors (F12)

#### Monitor Resources

```bash
# Watch container resource usage
podman stats race-game-api race-caddy

# Check configured limits
podman inspect race-game-api | grep -A 5 Memory
```

## Maintenance

### Update Game Code

```bash
# On production server
cd ~/race-to-the-crystal
git pull

# Rebuild container
cd deployment/dockerfiles
podman build -f Dockerfile -t localhost/race-to-the-crystal:latest ../..

# Restart service
systemctl --user restart game-api.service

# Verify
systemctl --user status game-api.service
journalctl --user -u game-api.service -n 50
```

### Update Caddy Configuration

```bash
# Edit Caddyfile
vim ~/.config/containers/systemd/Caddyfile

# Restart Caddy
systemctl --user restart caddy.service

# Verify
systemctl --user status caddy.service
```

### Rotate Secrets

```bash
# Generate new secrets
NEW_PUBLISHER_JWT=$(openssl rand -base64 32)
NEW_SUBSCRIBER_JWT=$(openssl rand -base64 32)

# Update secrets file
cat > ~/.config/containers/systemd/race-secrets.env <<EOF
MERCURE_PUBLISHER_JWT=$NEW_PUBLISHER_JWT
MERCURE_SUBSCRIBER_JWT=$NEW_SUBSCRIBER_JWT
EOF

# Restart both services (must use matching secrets)
systemctl --user restart game-api.service caddy.service
```

### View Logs

```bash
# Real-time logs
journalctl --user -u game-api.service -f
journalctl --user -u caddy.service -f

# Last N lines
journalctl --user -u game-api.service -n 100

# Since timestamp
journalctl --user -u game-api.service --since "1 hour ago"

# Filter by priority
journalctl --user -u game-api.service -p err
```

## Troubleshooting

### Service Won't Start

```bash
# View detailed status
systemctl --user status game-api.service --no-pager -l

# Check quadlet generation
/usr/libexec/podman/quadlet -user -dryrun

# Verify image exists
podman images | grep race

# Check network exists
podman network ls | grep game-net
```

### Certificate Issues

```bash
# Verify DNS resolves
dig your-domain.com

# Verify port accessible externally (from external machine)
nc -zv your-domain.com 8880

# Check Caddy logs
journalctl --user -u caddy.service | grep -i cert
journalctl --user -u caddy.service | grep -i acme
journalctl --user -u caddy.service | grep -i error
```

**Common Fixes:**
- Ensure host AND cloud provider firewall allow port 8880
- Verify DNS points to correct IP
- Check Caddy has write permissions to certificate volume

### WebSocket Connection Fails

```bash
# Verify WebSocket endpoint
curl -I https://your-domain.com:8880/ws

# Check browser console for errors (CORS, connection refused)

# Verify Mercure endpoint
curl https://your-domain.com:8880/.well-known/mercure
```

### High Resource Usage

```bash
# View resource usage
podman stats race-game-api race-caddy

# Increase limits if needed
vim ~/.config/containers/systemd/game-api.container
# Edit Memory=, CPUQuota= values

# Reload and restart
systemctl --user daemon-reload
systemctl --user restart game-api.service
```

### Browser Cache Issues

If web client shows old code after updates:

- **Firefox/Chrome**: `Ctrl + Shift + R` (or `Cmd + Shift + R` on Mac)
- Or: F12 → Right-click reload → "Empty Cache and Hard Reload"

## Security Checklist

Production deployment includes:

- ✅ Strong JWT secrets (32+ bytes random)
- ✅ Secrets stored in file (not inline)
- ✅ File permissions secure (600)
- ✅ HTTPS enabled with auto certificates
- ✅ CORS restricted to production domain
- ✅ Security headers enabled
- ✅ Resource limits configured
- ✅ Rate limiting implemented
- ✅ Input validation implemented
- ✅ Rootless containers (non-root user)
- ⚠️ TCP port 8888 internal-only (desktop clients via VPN)

**See [MERCURE.md](MERCURE.md) for Mercure-specific security configuration.**

## Rollback Procedure

If deployment fails:

```bash
# Stop services
systemctl --user stop game-api.service caddy.service

# Remove production configs
rm ~/.config/containers/systemd/game-api.container
rm ~/.config/containers/systemd/caddy.container
rm ~/.config/containers/systemd/Caddyfile

# Restore development configs (if needed)
cp deployment/development/*.container ~/.config/containers/systemd/
cp deployment/development/*.network ~/.config/containers/systemd/
cp Caddyfile ~/.config/containers/systemd/

# Reload and restart
systemctl --user daemon-reload
systemctl --user start game-api.service caddy.service
```

## Production Endpoints

- **Web Client:** https://your-domain.com:8880/
- **WebSocket:** wss://your-domain.com:8880/ws
- **Mercure Hub:** https://your-domain.com:8880/.well-known/mercure
- **Static Files:** https://your-domain.com:8880/static/
- **TCP Desktop Clients:** Internal only (port 8888, not exposed)

## Configuration Files

**Development:**
- `deployment/development/game-api.container` - Game server (dev mode)
- `deployment/development/caddy.container` - Caddy proxy (dev mode)
- `deployment/development/game-net.network` - Podman network

**Production:**
- `deployment/production/game-api.container` - Game server (production)
- `deployment/production/caddy.container` - Caddy proxy (production)
- `deployment/production/Caddyfile` - Caddy configuration with HTTPS
- `deployment/production/game-net.network` - Podman network
- `deployment/production/race-secrets.env.template` - Secrets template

**Dockerfiles:**
- `deployment/dockerfiles/Dockerfile` - Game server image
- `deployment/dockerfiles/Dockerfile.caddy` - Caddy image with Mercure

## Notes

- **Port 8880:** Used instead of 443 for rootless podman (no privileged port binding)
- **Certificates:** Caddy manages Let's Encrypt certificates automatically
- **Renewal:** Caddy renews certificates before expiration
- **TCP Port:** Desktop client port 8888 remains internal-only for security
- **User Services:** Running as regular user (not root)
- **Lingering:** User services persist after logout (enabled in prerequisites)

## Support

For issues or questions:
- Check logs: `journalctl --user -u game-api.service -u caddy.service`
- Review [MERCURE.md](MERCURE.md) for Mercure configuration
- Check container status: `podman ps -a --filter "name=race-"`
- See troubleshooting section above
