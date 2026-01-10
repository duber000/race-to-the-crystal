# Production Deployment

This folder contains production-ready systemd quadlet configuration files for deploying Race to the Crystal to an internet-facing server.

## Overview

**Production URL:** https://your-domain.com:8880
**Max Players:** 4 concurrent players
**Ports:** 8880 (HTTP/HTTPS), 8444 (future use), 8888 (TCP - internal only)

## Files

- **Caddyfile** - Production Caddy config with HTTPS, Mercure, security headers
- **game-api.container** - Game server quadlet with resource limits and secrets
- **caddy.container** - Caddy reverse proxy quadlet with resource limits
- **game-net.network** - Podman network configuration (same as dev)

## Prerequisites

### 1. DNS Configuration
Verify DNS points to production server:
```bash
dig your-domain.com
# Should return your server's IP address
```

### 2. Create Non-Root User
For security, run containers as a non-root user:
```bash
# As root or sudo
useradd -m -s /bin/bash gameuser
loginctl enable-linger gameuser

# Verify lingering enabled
loginctl show-user gameuser | grep Linger
# Should show: Linger=yes
```

### 3. Firewall Configuration
Open required ports:

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
If using a cloud provider (AWS, GCP, Azure, DigitalOcean, etc.), also configure their firewall/security groups to allow:
- TCP port 8880 (inbound)
- TCP port 8444 (inbound, optional)

### 4. Build Container Images
Build the container images on the production server as the non-root user:

```bash
# Log in as the non-root user
su - gameuser

# Clone repository
git clone <repo-url> ~/race-to-the-crystal
cd ~/race-to-the-crystal

# Build Caddy binary with required modules (if not already built)
# Note: Pre-built caddy binary is included in the repo
# Only rebuild if you need to update modules or versions
# Install xcaddy: go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
# Then build:
# xcaddy build --with github.com/caddy-dns/hetzner@v2.0.0-preview-3 --with github.com/dunglas/mercure/caddy --with github.com/greenpau/caddy-security

# Build Caddy image (with Mercure plugin and Hetzner DNS)
chmod +x caddy
podman build -f Dockerfile.caddy -t localhost/race-caddy:latest .

# Build game API image
podman build -t localhost/race-to-the-crystal:latest .
```

## Deployment Steps

### Step 1: Generate Secrets

**As the non-root user**, generate strong random JWT secrets for Mercure:

```bash
# Generate secrets
PUBLISHER_JWT=$(openssl rand -base64 32)
SUBSCRIBER_JWT=$(openssl rand -base64 32)

# Create secrets file
mkdir -p ~/.config/containers/systemd
cat > ~/.config/containers/systemd/race-secrets.env <<EOF
MERCURE_PUBLISHER_JWT=$PUBLISHER_JWT
MERCURE_SUBSCRIBER_JWT=$SUBSCRIBER_JWT
# Optional: Add Hetzner DNS API token for DNS-01 challenge (if using Hetzner DNS)
# YOUR_HETZNER_AUTH_API_TOKEN=your_hetzner_api_token_here
EOF

# Secure the file
chmod 600 ~/.config/containers/systemd/race-secrets.env

# Verify
cat ~/.config/containers/systemd/race-secrets.env
```

**IMPORTANT:** Keep these secrets secure. Store them in a password manager for future reference.

### Step 2: Update Configuration with Your Domain

Edit the configuration files to use your domain:

```bash
cd ~/race-to-the-crystal

# Update game-api.container with your domain
sed -i 's/your-domain.com/YOURDOMAIN/g' quadlets-production/game-api.container

# Update Caddyfile with your domain
sed -i 's/your-domain.com/YOURDOMAIN/g' quadlets-production/Caddyfile

# Example: sed -i 's/your-domain.com/example.com/g' quadlets-production/*.container quadlets-production/Caddyfile
```

### Step 3: Deploy Quadlet Files

Copy the production configuration files:

```bash
# Create volume directories for Caddy
mkdir -p ~/.local/share/containers/systemd/caddy/{data,config}

# Copy quadlet files
cp quadlets-production/*.container ~/.config/containers/systemd/
cp quadlets-production/*.network ~/.config/containers/systemd/
cp quadlets-production/Caddyfile ~/.config/containers/systemd/

# Verify
ls -la ~/.config/containers/systemd/
```

### Step 4: Start Services

```bash
# Reload systemd to recognize new quadlet files
systemctl --user daemon-reload

# Start services (don't use enable with generated quadlet services)
systemctl --user start game-api.service caddy.service

# Check status
systemctl --user status game-api.service
systemctl --user status caddy.service
```

### Step 5: Verify Deployment

```bash
# Check containers are running
podman ps -a --filter "name=race-"

# Check logs
journalctl --user -u game-api.service -n 50
journalctl --user -u caddy.service -n 50

# Test local access
curl http://localhost:8880/

# Test external access (from different machine)
curl -I http://your-domain.com:8880/
```

### Step 6: Monitor Certificate Provisioning

Caddy will automatically request a Let's Encrypt certificate on first HTTPS access:

```bash
# Watch caddy logs for certificate provisioning
journalctl --user -u caddy.service -f

# Look for lines like:
# "successfully downloaded available certificate chains"
# "certificate obtained successfully"

# Verify certificate after provisioning
curl -vI https://your-domain.com:8880/ 2>&1 | grep -A 5 "SSL certificate"
```

**Note:** Initial certificate provisioning may take 1-2 minutes. The site will be accessible via HTTP while waiting.

## Post-Deployment

### Test Full Functionality

1. Open browser to: https://your-domain.com:8880
2. Create a new game
3. Verify READY button shows correctly
4. Start game with 2-4 players (open multiple browser windows/devices)
5. Test gameplay: move, attack, deploy tokens
6. Complete a full game to win condition
7. Check browser console for errors (F12)

### Monitor Resources

```bash
# Watch container resource usage
podman stats race-game-api race-caddy

# Check memory usage
podman inspect race-game-api | grep -A 5 Memory
podman inspect race-caddy | grep -A 5 Memory
```

### Set Up Persistence

User services will persist after logout thanks to lingering enabled in Prerequisites step 2. Verify:

```bash
# Check lingering status
loginctl show-user $USER | grep Linger
# Should show: Linger=yes

# If not enabled, run as root/sudo:
# sudo loginctl enable-linger yourusername
```

## Maintenance

### Update Game Code

When you push code updates:

```bash
# On production server
cd ~/race-to-the-crystal
git pull

# Rebuild container
podman build -t localhost/race-to-the-crystal:latest .

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

# Verify configuration
systemctl --user status caddy.service
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

### Restart Services

```bash
# Restart individual service
systemctl --user restart game-api.service
systemctl --user restart caddy.service

# Restart both
systemctl --user restart game-api.service caddy.service

# Stop and start
systemctl --user stop game-api.service caddy.service
systemctl --user start game-api.service caddy.service
```

### Rotate Secrets

If you need to rotate JWT secrets:

```bash
# Generate new secrets
NEW_PUBLISHER_JWT=$(openssl rand -base64 32)
NEW_SUBSCRIBER_JWT=$(openssl rand -base64 32)

# Update secrets file
cat > ~/.config/containers/systemd/race-secrets.env <<EOF
MERCURE_PUBLISHER_JWT=$NEW_PUBLISHER_JWT
MERCURE_SUBSCRIBER_JWT=$NEW_SUBSCRIBER_JWT
EOF

# Restart both services (they must use matching secrets)
systemctl --user restart game-api.service caddy.service
```

## Troubleshooting

### Certificate Issues

**Problem:** Certificate not provisioning

**Check:**
```bash
# Verify DNS resolves
dig your-domain.com

# Verify port 8880 is accessible externally
# From external machine:
nc -zv your-domain.com 8880

# Check Caddy logs
journalctl --user -u caddy.service | grep -i cert
journalctl --user -u caddy.service | grep -i acme
journalctl --user -u caddy.service | grep -i error
```

**Common Fixes:**
- Ensure both host firewall AND cloud provider firewall allow port 8880
- Verify DNS points to correct IP
- Check Caddy has write permissions to `~/.local/share/containers/systemd/caddy/data/` volume

### Service Won't Start

**Check:**
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

### WebSocket Connection Fails

**Check:**
```bash
# Verify WebSocket endpoint
curl -I https://your-domain.com:8880/ws

# Check browser console for errors
# Look for CORS errors or connection refused

# Verify Mercure endpoint
curl https://your-domain.com:8880/.well-known/mercure
```

### High Resource Usage

**Check:**
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

## Security Checklist

- [x] Strong JWT secrets generated (32+ bytes random)
- [x] Secrets stored in file (not inline in quadlet)
- [x] File permissions secure (600)
- [x] HTTPS enabled with auto certificate
- [x] CORS restricted to production domain
- [x] Security headers enabled
- [x] Resource limits configured
- [x] Rate limiting implemented (see SECURITY_IMPROVEMENTS.md)
- [x] Input validation implemented (see SECURITY_IMPROVEMENTS.md)
- [x] Running as non-root user with rootless containers
- [ ] Monitoring set up (optional)

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
cp quadlet/*.container ~/.config/containers/systemd/
cp Caddyfile ~/.config/containers/systemd/

# Reload and restart
systemctl --user daemon-reload
systemctl --user start game-api.service caddy.service
```

## URLs and Endpoints

- **Web Client:** https://your-domain.com:8880/
- **WebSocket:** wss://your-domain.com:8880/ws
- **Mercure Hub:** https://your-domain.com:8880/.well-known/mercure
- **Static Files:** https://your-domain.com:8880/static/
- **TCP Desktop Clients:** Internal only (port 8888, not exposed)

## Notes

- **Port 8880:** Used instead of standard 443 for rootless podman (no privileged port binding)
- **Certificates:** Caddy manages Let's Encrypt certificates automatically
- **Certificate Storage:** Persisted in `~/.local/share/containers/systemd/caddy/data/`
- **Renewal:** Caddy renews certificates automatically before expiration
- **TCP Port:** Desktop client port 8888 remains internal-only (no PublishPort)
- **User Services:** Running as regular user (not root) for security

## Support

For issues or questions:
- Check logs: `journalctl --user -u game-api.service -u caddy.service`
- Review SECURITY_IMPROVEMENTS.md for security details
- Check container status: `podman ps -a --filter "name=race-"`
- See troubleshooting section above for common issues
