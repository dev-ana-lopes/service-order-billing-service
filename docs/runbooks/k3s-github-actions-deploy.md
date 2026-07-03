# k3s Deployment Through GitHub Actions

This runbook documents the current production/demo path for `service-order-billing-service`.

## Public URL

API Gateway:

```text
https://oubv5hamu5.execute-api.us-east-1.amazonaws.com
```

API Gateway must route to the k3s/Traefik backend through:

```text
http://32.197.10.136/{proxy}
```

## Required GitHub Secrets

- `APP_ENV`: full application environment file used to render Kubernetes
  ConfigMap/Secret manifests. Do not commit this content.
- `EC2_SSH_KEY`: private SSH key used by the workflow to connect to the k3s EC2
  instance.

## Required GitHub Variables

- `EC2_HOST`: current EC2 public IP or DNS, for example `32.197.10.136`.
- `EC2_USER`: SSH user, for example `ec2-user`.
- `EC2_PORT`: SSH port, usually `22`.

## APP_ENV Notes

Production `APP_ENV` should include:

```dotenv
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/service_order_db?ssl=require
CORS_ALLOWED_ORIGINS=http://32.197.10.136
TRUSTED_HOSTS=*
OTEL_ENABLED=false
DD_TRACE_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=
```

The API runtime uses `ssl=require`. The deploy workflow creates a separate
migration secret and converts the database URL to `sslmode=require` for Alembic.

Keep OpenTelemetry and Datadog tracing disabled for the current delivery. The
Datadog Agent is used for logs and Kubernetes/container visibility; traces via
OTLP are planned only after validating the Agent service exposes HTTP port
`4318`.

## Pipeline Flow

The workflow performs:

- lint
- tests
- Docker build
- push to GHCR
- render Kubernetes manifests with an explicit image
- copy rendered manifests to EC2
- run migration job
- apply deployment, service, HPA and ingress
- wait for rollout
- smoke test

## Re-run Pipeline

From GitHub:

1. Open the `Actions` tab.
2. Select `ci-cd-service-order-billing-service`.
3. Use `Run workflow` for manual execution, or re-run the failed job from the
   existing run.

From Git CLI, if configured:

```bash
gh workflow run ci-cd.yml --ref main
```

## Verify Kubernetes

```bash
kubectl get pods -n service-order
kubectl get jobs -n service-order
kubectl logs -n service-order deployment/service-order-billing-service --tail=100
kubectl get svc -n service-order
kubectl get ingress -n service-order
kubectl get hpa -n service-order
```

## Validate API Gateway

```bash
curl -i https://oubv5hamu5.execute-api.us-east-1.amazonaws.com/health
curl -i https://oubv5hamu5.execute-api.us-east-1.amazonaws.com/health/ready
curl -i https://oubv5hamu5.execute-api.us-east-1.amazonaws.com/docs
```

`/metrics` exists in the application as a technical endpoint. Datadog is the
primary observability tool for logs, Kubernetes/container visibility,
dashboards/monitors and Synthetic Monitoring:

```bash
curl -i https://oubv5hamu5.execute-api.us-east-1.amazonaws.com/metrics
```

## Validate Datadog

```bash
kubectl get pods -n datadog
kubectl get svc -n datadog
kubectl logs -n service-order deployment/service-order-billing-service --tail=100
kubectl get hpa -n service-order
```

In Datadog, confirm container logs for `service-order-billing-service`, JSON fields
`correlation_id` and `request_id`, Kubernetes/container visibility, and
Synthetic Monitoring checks for `/health` and `/health/ready`.

