# service-order-billing-service

Billing service skeleton for FIAP Phase 4.

This repository is a Phase 4 microservice skeleton created from service-order-api.
All implementation code must be written in English.

## Phase 1 Scope

- FastAPI application skeleton.
- Health, readiness, liveness, and metrics endpoints.
- Docker, Kubernetes manifests, GitHub Actions, and SonarCloud configuration.
- Minimal tests that keep the repository deployable before business rules are added.

Business endpoints, persistence models, messaging, Saga handlers, and BDD scenarios are intentionally added in later phases.

## Local Development

`ash
uv sync --dev
make lint
make test
make test-cov
make run-dev
`

## Endpoints

- GET /health
- GET /health/live
- GET /health/ready
- GET /metrics

## CI/CD

The pipeline is prepared for lint, tests, coverage, SonarCloud, GHCR image publishing, manifest rendering, and k3s deploy.
