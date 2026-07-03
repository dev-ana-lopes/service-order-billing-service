# Datadog Runbook

Datadog is the primary observability tool for the current Phase 3 delivery.
The active scope is logs, Kubernetes/container visibility, dashboards/monitors
and Synthetic Monitoring for the public health endpoints.

Traces via OTLP are not enabled yet. Keep API tracing disabled until the
Datadog Agent service is confirmed to expose the OTLP HTTP receiver on port
`4318`.

## Current Production Flags

Keep these values in the API environment for the current delivery:

```dotenv
OTEL_ENABLED=false
DD_TRACE_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=
```

The API still emits JSON logs with `correlation_id` and `request_id`. The
Datadog Agent collects container logs from Kubernetes.

## Agent Installation

The Agent is installed outside this repository through Helm in the `datadog`
namespace. The Helm values used for the delivery must enable:

- logs collection;
- container log collection for all containers;
- Kubernetes/container visibility.

Validate the namespace and Agent pods:

```bash
kubectl get pods -n datadog
kubectl get svc -n datadog
```

Validate application logs from Kubernetes:

```bash
kubectl logs -n service-order deployment/service-order-billing-service --tail=50
```

Then confirm in Datadog Logs that `service:service-order-billing-service` entries include
`correlation_id` and `request_id`.

## Synthetic Monitoring

Create Datadog Synthetic API tests for the public API Gateway endpoints:

```text
GET https://oubv5hamu5.execute-api.us-east-1.amazonaws.com/health
GET https://oubv5hamu5.execute-api.us-east-1.amazonaws.com/health/ready
```

Expected result: HTTP `200` for both endpoints. `/health/ready` also validates
database readiness through the API.

## HPA Evidence

The API HPA is configured in Kubernetes to monitor CPU and scale pods between
2 and 5 replicas:

```bash
kubectl get hpa -n service-order
kubectl describe hpa service-order-billing-service -n service-order
```

## Planned Trace Enablement

Before enabling traces, confirm that the Agent service exposes OTLP HTTP on
port `4318`:

```bash
kubectl get svc -n datadog
kubectl describe svc -n datadog datadog-agent
```

Only after that validation should tracing be enabled and the API should point
to the Datadog Agent OTLP HTTP endpoint in the `datadog` namespace. Do not
enable this for the current delivery without validating the receiver.

