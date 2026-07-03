# ADR-0005: Observabilidade

## Status

Aceita.

## Decisao

Usar Datadog como ferramenta principal de observabilidade da entrega atual.
O Agent e instalado via Helm no namespace `datadog` e coleta logs de todos os
containers. A `service-order-billing-service` gera logs JSON com `correlation_id` e
`request_id`.

A entrega atual cobre logs, Kubernetes/container visibility,
dashboards/monitores Datadog e Synthetic Monitoring para `/health` e
`/health/ready` via API Gateway.

Tracing via OpenTelemetry/OTLP permanece desabilitado ate validar o receiver
HTTP `4318` no servico do Datadog Agent.

## Consequencias

- Centraliza a demonstracao de saude e comportamento da API no Datadog.
- Mantem tracing opcional por variavel de ambiente, mas desligado na entrega
  atual.
- Evita falhas por endpoint OTLP nao validado.
- Mantem `/metrics` como endpoint tecnico da API, sem dependencia de stack
  adicional para a entrega.

