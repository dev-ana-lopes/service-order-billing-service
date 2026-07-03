# Deployment Runbooks

Kubernetes is the primary production/demo deployment path for this repository.
Docker Compose is preserved only as a legacy fallback.

## Primary Deployment: Kubernetes

Status: active and automated through GitHub Actions.

Target:

- k3s on EC2
- PostgreSQL on RDS
- image published to GHCR
- API exposed by API Gateway HTTP API:
  `https://oubv5hamu5.execute-api.us-east-1.amazonaws.com`

The Kubernetes deployment is:

- automated by `.github/workflows/ci-cd.yml`;
- rendered with an explicit GHCR image tag;
- applied remotely on the EC2 k3s host via SSH;
- deployed through namespace, ConfigMap, Secret, migration Job, Deployment,
  Service, Ingress and HPA manifests;
- validated by migration job, rollout status and public smoke test;
- observed with Datadog Agent logs, Kubernetes/container visibility, dashboard
  evidence and Synthetic Monitoring.

For the detailed runbook, see `docs/runbooks/k3s-github-actions-deploy.md`.

## CI/CD Requirements

GitHub Environment `production` must provide:

- Secret `APP_ENV`
- Secret `EC2_SSH_KEY`
- Variable `EC2_HOST`
- Variable `EC2_USER`
- Variable `EC2_PORT`

`APP_ENV` must keep tracing disabled for the current delivery:

```dotenv
OTEL_ENABLED=false
DD_TRACE_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=
DD_SERVICE=service-order-billing-service
DD_ENV=production
DD_VERSION=3.0.0
```

The workflow in this repository does not package, deploy or validate Terraform
for the CPF authentication Lambda. That belongs to `service-order-auth-lambda`.

## Observability

Datadog is the official observability tool for Phase 3. The Datadog Agent is
installed via Helm in the `datadog` namespace and collects Kubernetes container
logs. The API emits JSON logs with `correlation_id`, `request_id`, request
metadata, service, env and version.

Prometheus/Grafana is not the active delivery stack. `/metrics` remains
available as a technical endpoint of the API.

## HPA

The API HPA must remain:

- `minReplicas: 2`
- `maxReplicas: 5`
- CPU `averageUtilization: 70`

## Fallback: Legacy Docker Compose Deployment

Status: deprecated and preserved for emergency use only.

Use this path only for emergency recovery or local operational comparison.

```bash
cp .env.prod.example .env.prod
python3 scripts/deploy/prepare_env.py .env.prod
API_IMAGE=service-order-billing-service:prod ./scripts/deploy/release.sh
```

Validate:

```bash
curl http://<host>:8000/health
curl http://<host>:8000/health/ready
curl http://<host>:8000/docs
```

The legacy Compose flow uses the same application schema and environment
validation, but it is not the main Phase 3 demonstration path.

