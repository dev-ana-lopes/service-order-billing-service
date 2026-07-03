# Phase 3 Delivery Checklist

## Repositories

- `service-order-billing-service`
- `service-order-auth-lambda`
- `service-order-infra-k8s`
- `service-order-infra-db`

## Public Entry Point

- API Gateway:
  `https://oubv5hamu5.execute-api.us-east-1.amazonaws.com`
- Validated routes:
  - `/health`
  - `/health/ready`
  - `/docs`
- Optional technical validation:
  - `/metrics`
  - CPF auth route through final API Gateway route, if not already captured

## Current Status

- GitHub Actions for `service-order-billing-service`: validates lint/tests, builds Docker,
  pushes GHCR image, renders manifests, deploys to k3s, runs migration, waits
  for rollout and runs smoke tests.
- `service-order-auth-lambda`: owns the CPF authentication Lambda code,
  packaging, deployment notes and any Lambda-specific infrastructure.
- GitHub Actions for `service-order-infra-k8s`: validates Terraform; apply is
  intentionally manual because the real state is local.
- GitHub Actions for `service-order-infra-db`: validates Terraform; apply is
  intentionally manual because the real state is local.
- Lambda `service-order-auth-cpf`: public CPF authentication dependency behind
  API Gateway. Operational details are documented in `service-order-auth-lambda`.
- k3s: running on EC2 and serving the API through Traefik/Ingress.
- RDS: PostgreSQL available and used by API/Lambda.
- Datadog Agent: installed via Helm in namespace `datadog` for logs and
  Kubernetes/container visibility.
- Traces via OTLP: disabled until the Agent service exposes HTTP port `4318`.

## What to Demonstrate in the Video

- Open the four repositories and show their responsibilities.
- Show GitHub Actions success for each repository.
- Show API Gateway URL and routes returning 200.
- Show Swagger at `/docs`.
- Show `POST /auth/cpf` through API Gateway as the public customer
  authentication route.
- Show `kubectl get pods -n service-order`.
- Show `kubectl get hpa -n service-order`.
- Show RDS PostgreSQL instance status.
- Show Datadog logs with request/correlation id.
- Show Datadog Kubernetes/container visibility, dashboards/monitors and
  Synthetic Monitoring for `/health` and `/health/ready`.

## Evidence to Capture

- Actions green in the four repositories.
- API Gateway `/health`, `/health/ready` and `/docs`.
- API Gateway `POST /auth/cpf` evidence.
- `kubectl get pods -n service-order`.
- `kubectl get jobs -n service-order`.
- `kubectl get hpa -n service-order`.
- RDS status.
- Swagger UI.
- JSON logs in Datadog with request/correlation id.
- Datadog dashboard/monitor screenshot.
- Datadog Synthetic Monitoring evidence for `/health` and `/health/ready`.

## Pending Confirmations

- `soat-architecture` added to the four repositories.
- Final video recorded.
- Final PDF generated.
- Public `/metrics` validation completed if used as technical API evidence.
- Datadog evidence captured.
- OTLP traces remain disabled until Agent port `4318` is validated.

