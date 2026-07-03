# Checklist da Fase 3

Este arquivo e o ponto canonico para a checklist da Fase 3. O historico
detalhado permanece em `docs/checklists/fase3-checklist.md`.

## Validacao tecnica

- API FastAPI versionada e testada.
- Autenticacao de cliente por JWT emitido pela Lambda.
- Healthchecks `/health` e `/health/ready`.
- Observabilidade principal no Datadog, com logs de containers, logs JSON com
  correlation id/request id, dashboards/monitores e Synthetic Monitoring.
- Metricas da aplicacao em `/metrics` como endpoint tecnico da API.
- Correlation id gerado ou propagado por requisicao.
- HPA monitora CPU e escala pods entre 2 e 5 replicas.
- Manifests Kubernetes renderizados com imagem GHCR explicita.
- RDS PostgreSQL isolado em subnets privadas.
- CI/CD com lint, testes, build de imagem e deploy controlado.

## Demonstracao

- Provisionar k3s em EC2.
- Provisionar RDS PostgreSQL.
- Publicar imagem `ghcr.io/<owner>/service-order-billing-service:sha-<commit>`.
- Aplicar manifests renderizados no k3s.
- Publicar Lambda e API Gateway.
- Chamar `POST /auth/cpf`.
- Usar o Bearer Token na API protegida.
- Mostrar logs no Datadog, healthchecks via API Gateway/Synthetic Monitoring e
  HPA entre 2 e 5 replicas.

