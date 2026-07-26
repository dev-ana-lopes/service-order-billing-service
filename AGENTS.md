# AGENTS.md

Este arquivo define o contexto operacional para agentes Codex neste repositório.
Escopo: toda a árvore do projeto.

## 1) Visão geral do projeto

- Projeto: API monolítica em FastAPI para gestão de ordens de serviço de oficina mecânica.
- Stack principal: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Docker/Compose.
- Plataforma de demo principal: `k3s` em EC2 + PostgreSQL em RDS + GHCR.
- Fluxo legado preservado: EC2 + Docker Compose (fallback operacional).
- Objetivo acadêmico: sustentar entregas das Fases 1, 2 e 3 com baixo custo (AWS Academy, ~US$50).

## 2) Arquitetura esperada

- `src/domain`: entidades, enums, regras de negócio e contratos (ports).
- `src/application`: casos de uso e orquestração de regras.
- `src/infrastructure`: banco, repositórios, settings, logging, auth, e-mail.
- `src/presentation`: rotas FastAPI, schemas, serializers e dependências.
- Regra de dependência: `domain` não depende de framework; `application` depende de `domain`; `presentation` e `infrastructure` adaptam bordas.

## 3) Estrutura de pastas (referência rápida)

- `src/`: aplicação backend.
- `tests/`: testes unitários, integração e cenários de API.
- `alembic/`: migrations.
- `k8s/`: manifests base (com placeholder de imagem para render).
- `scripts/deploy/`: validação de `.env`, render de manifests, release legado.
- `infra/`: Terraform.
- `.github/workflows/ci-cd.yml`: pipeline principal (validate + deploy).

## 4) Setup e execução local

- Instalar dependências dev: `uv sync --dev`
- Subir stack local: `make compose-up`
- Parar stack local: `make compose-down`
- Logs da API local: `make compose-logs`
- Rodar API sem Docker (dev): `make run-dev`
- Health endpoints esperados: `http://localhost:8002/health` e `http://localhost:8002/health/ready`

## 5) Qualidade e testes

- Lint/format check: `make lint`
- Testes rápidos: `make test`
- Cobertura: `make test-cov`
- Integração com PostgreSQL real: `make test-integration`
- Migrações locais: `make migrate`

## 6) Docker e Compose

- Build local da imagem: `make build-docker`
- Execução local da imagem: `make docker-run`
- Compose produção (fallback): `make compose-prod-up` e `make compose-prod-down`
- Release legado/fallback: `scripts/deploy/release.sh`
- Regra: não promover fallback Compose como caminho principal de Kubernetes.

## 7) Kubernetes (k3s) e política de imagem

- Sempre renderizar manifests com imagem explícita antes de aplicar:
- `python3 scripts/deploy/prepare_env.py <env-file>`
- `python3 scripts/deploy/render_k8s_manifests.py --env-file <env-file> --output-dir <dir> --image <ghcr-image> [--namespace <ns>]`
- Nunca aplicar `k8s/deployment.yaml` ou `k8s/job-migrate.yaml` com placeholder (`__API_IMAGE__` ou `${API_IMAGE}`).
- Nunca depender de imagem local no cluster.
- A imagem de deploy deve ser GHCR no padrão `ghcr.io/<owner>/service-order-billing-service:<tag>`.

## 8) GHCR e versionamento de tags

- Tag principal de CI/CD: `sha-<commit_sha>` (padrão do workflow atual).
- Tag para testes manuais: `dev-<timestamp>`.
- Tag semântica (`vX.Y.Z`) para releases planejadas/documentadas.
- `ghcr.io/<owner>/service-order-billing-service:<tag>` deve ser consistente entre build/push e manifests renderizados.

## 9) GHCR público vs privado

- Público: simplifica pull no `k3s` sem `imagePullSecret`.
- Privado: criar secret de registry no namespace e referenciar no deployment.
- Se usar privado, documentar explicitamente no runbook os comandos de criação/rotação de secret.

## 10) Padrões de código Python/FastAPI

- Manter padrão de estilo já definido no projeto (`black`, `isort`, `flake8`).
- Reutilizar padrões de DTO/schema/use case/repository já existentes.
- Evitar acoplamento de regra de negócio com camada HTTP ou ORM.
- Priorizar mudanças pequenas, testáveis e com impacto localizado.

## 11) Regras de Clean Architecture e DDD

- Não mover regra de domínio para `presentation`.
- Casos de uso em `application` devem orquestrar contratos do `domain`.
- Implementações concretas de contratos ficam em `infrastructure`.
- Alterações de entidades/enums devem considerar impacto em use cases, serializers e testes.

## 12) Regras para Alembic

- Toda mudança persistente de schema deve ter migration.
- Migration deve ser pequena, reversível e coerente com estado anterior.
- Validar `upgrade head` localmente com `make migrate`.
- Não misturar refatoração de aplicação com refatoração de schema sem necessidade.

## 13) Variáveis sensíveis e secrets

- Nunca commitar secrets reais.
- Preferir variáveis `*_FILE` quando disponível.
- Não imprimir tokens/senhas em logs, scripts ou mensagens.
- Tratar `.env`, `.env.prod` e segredos de CI/CD como dados sensíveis.

## 14) CI/CD e deploy

- Fluxo principal: `.github/workflows/ci-cd.yml`.
- O job `validate` deve continuar cobrindo lint, testes e validação de render dos manifests.
- O job `deploy-production` deve manter build/push no GHCR + render + apply no Kubernetes.
- Mudanças em deploy devem preservar `k3s + EC2 + RDS` como estratégia principal da demo.

## 15) Documentação obrigatória

- Mudou comportamento público de API: atualizar `README.md` e/ou docs em `docs/`.
- Mudou processo de deploy/operação: atualizar `README.deploy.md` e `docs/runbooks/`.
- Mudou integração com Kubernetes/Terraform: atualizar docs correspondentes.

## 16) Checklist pré-PR

- Código aderente à arquitetura por camadas.
- Sem placeholder de imagem em manifest renderizado.
- Sem segredo real em arquivo versionado.
- `make lint` executado.
- `make test` executado.
- Se aplicável, `make test-cov` e/ou `make test-integration` executados.
- Migrações testadas quando houver alteração de schema.
- Documentação atualizada quando comportamento/processo mudou.

## 17) Critérios de aceite por fase

- Fase 1: domínio e regras centrais, CRUD/fluxos principais, autenticação, testes mínimos.
- Fase 2: Docker/Compose estável, Kubernetes com imagem explícita, Terraform funcional, CI/CD validando qualidade e deploy.
- Fase 3: evolução com observabilidade/integrações avançadas sem quebrar o fluxo principal de demonstração.

## 18) Gaps (necessário criar)

- `make compose-smoke` citado no README, mas sem target no `Makefile` atual.
- `make test-mailhog-e2e` citado no README, mas sem target no `Makefile` atual.
- API Gateway como componente dedicado não está automatizado neste repositório.
- Lambda/serverless não está implementado como fluxo operacional no estado atual.
- Observabilidade avançada (ex.: stack completa de métricas/tracing centralizados) não está fechada como automação de projeto.

## 19) Comportamento esperado do agente

- Antes de editar, ler contexto mínimo dos arquivos impactados.
- Preferir correção na causa raiz e evitar mudanças fora de escopo.
- Validar com os comandos disponíveis no projeto.
- Em dúvida entre caminhos de alto impacto, escolher o mais simples e consistente com `k3s + EC2 + RDS + GHCR`.

