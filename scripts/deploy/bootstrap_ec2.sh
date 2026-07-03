#!/usr/bin/env sh
# ============================================================================
# LEGACY/FALLBACK: Docker Compose Bootstrap
# ============================================================================
# This script is part of the LEGACY deployment pipeline using Docker Compose.
# 
# PRIMARY DEPLOYMENT: Kubernetes (see scripts/deploy/render_k8s_manifests.py)
# 
# Use this script only for:
# - Emergency recovery of a Compose-based deployment
# - Fallback if Kubernetes deployment is unavailable
# - Manual testing of the legacy flow
# 
# For production deployments, use GitHub Actions CI/CD with Kubernetes.
# ============================================================================

set -eu

APP_DIR="${APP_DIR:-/opt/service-order-billing-service}"
DOCKER_COMPOSE_VERSION="${DOCKER_COMPOSE_VERSION:-v2.27.0}"

if command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="dnf"
elif command -v yum >/dev/null 2>&1; then
  PKG_MANAGER="yum"
else
  echo "[bootstrap] Unsupported Linux distribution: missing dnf/yum"
  exit 1
fi

sudo "$PKG_MANAGER" update -y
sudo "$PKG_MANAGER" install -y docker git
sudo systemctl enable docker
sudo systemctl start docker

if ! docker compose version >/dev/null 2>&1; then
  sudo mkdir -p /usr/local/lib/docker/cli-plugins
  sudo curl -SL \
    "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

sudo usermod -aG docker "${SUDO_USER:-ec2-user}" || true
sudo mkdir -p "$APP_DIR"
sudo chown -R "${SUDO_USER:-ec2-user}":"${SUDO_USER:-ec2-user}" "$APP_DIR"

echo "[bootstrap] Docker and Docker Compose are ready."
echo "[bootstrap] Reconnect your SSH session if group membership was updated."

