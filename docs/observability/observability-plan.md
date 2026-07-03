# Observability Plan

## Phase 3 Scope

Datadog is the observability tool for the current delivery. The accepted scope
is:

- container logs collected by the Datadog Agent;
- JSON application logs with `correlation_id` and `request_id`;
- Kubernetes/container visibility in Datadog;
- dashboards and monitors in Datadog;
- Synthetic Monitoring for `/health` and `/health/ready` through API Gateway;
- HPA evidence from Kubernetes, with CPU-based scaling from 2 to 5 pods.

## Current State

- JSON logging is implemented in the API.
- Correlation/request identifiers are present in request logs.
- `/health` and `/health/ready` are active and validated through API Gateway.
- HPA is configured in Kubernetes manifests with `minReplicas: 2`,
  `maxReplicas: 5` and CPU utilization target.
- Datadog Agent is installed via Helm in the `datadog` namespace for logs and
  container visibility.
- Traces via OTLP are not part of the current delivery.

## Required Evidence

- Datadog Logs showing `service-order-billing-service` container logs.
- A JSON request log containing `correlation_id` and `request_id`.
- Datadog Kubernetes/container visibility for the API pods.
- Datadog Synthetic Monitoring checks for:
  - `GET /health`;
  - `GET /health/ready`.
- `kubectl get hpa -n service-order` showing the HPA.
- API Gateway `/health` and `/health/ready` returning 200.

## Planned Evolution

OpenTelemetry traces may be enabled later, but only after confirming that the
Datadog Agent service exposes the OTLP HTTP receiver on port `4318`:

```bash
kubectl get svc -n datadog
kubectl describe svc -n datadog datadog-agent
```

Until that validation is complete, production must keep:

```dotenv
OTEL_ENABLED=false
DD_TRACE_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=
```

