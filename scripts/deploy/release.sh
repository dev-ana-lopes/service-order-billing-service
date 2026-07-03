#!/usr/bin/env sh
# ============================================================================
# LEGACY/FALLBACK: Docker Compose Release Script
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
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

cd "$APP_DIR"

if [ ! -f "$ENV_FILE" ]; then
  echo "[release] Missing env file: $ENV_FILE"
  exit 1
fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm migrate
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d api
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

