# Component Diagram

```mermaid
flowchart LR
  Client[Cliente/Admin] --> APIGW[API Gateway HTTP API\n$default stage]
  APIGW -->|POST /auth/cpf| Lambda[Lambda Auth CPF/JWT\nservice-order-auth-cpf]
  APIGW -->|HTTP proxy\nhttp://32.197.10.136/{proxy}| Traefik[k3s on EC2\nTraefik/Ingress]
  Traefik --> API[service-order-billing-service\nFastAPI]
  Lambda --> RDS[(RDS PostgreSQL)]
  API --> RDS

  GHA[GitHub Actions] -->|build/push| GHCR[GHCR\nservice-order-billing-service:sha-*]
  GHA -->|SSH + kubectl| Traefik

  API --> Logs[JSON logs\ncorrelation_id/request_id]
  API --> Metrics[/metrics endpoint]
  Logs --> DD[Datadog Agent\ncontainer logs]
  DD --> DDO[Datadog\nlogs, dashboards, monitors]
  APIGW --> SYN[Datadog Synthetic Monitoring\n/health and /health/ready]
```

Notes:

- API Gateway was created through the AWS Console for the academic demo.
- CPF authentication Lambda code, packaging and operations are owned by
  `service-order-auth-lambda`; this repository only validates the JWTs it
  issues.
- Datadog is the current observability tool for logs, Kubernetes/container
  visibility, dashboards/monitors and Synthetic Monitoring.
- The API keeps traces disabled until the Datadog Agent OTLP HTTP receiver is
  validated.

