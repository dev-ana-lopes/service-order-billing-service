# Roteiro do Vídeo da Fase 3

## 1. Contexto

Apresentar os quatro repositórios:

- `service-order-billing-service`
- `service-order-auth-lambda`
- `service-order-infra-k8s`
- `service-order-infra-db`

Explicar que Kubernetes em k3s é o caminho principal da demo e Docker Compose fica apenas para desenvolvimento local.

## 2. Arquitetura

Mostrar o diagrama de componentes:

- Cliente chama API Gateway.
- API Gateway encaminha `/auth/cpf` para Lambda.
- Lambda consulta RDS e emite JWT.
- Cliente usa JWT para chamar a FastAPI no k3s.
- FastAPI persiste ordens de serviço no RDS.
- GitHub Actions publica imagem no GHCR e implanta no k3s.

## 3. Infraestrutura

Mostrar `terraform plan` dos repositórios `service-order-infra-k8s` e `service-order-infra-db`, destacando EC2/k3s, security groups e RDS privado.

## 4. Autenticação

Executar `POST /auth/cpf` com um CPF válido de cliente ativo e copiar o `access_token`.

## 5. API protegida

Chamar uma rota protegida da API com `Authorization: Bearer <token>`, abrir uma ordem de serviço e consultar o status.

## 6. Observabilidade

Mostrar:

- `/health`
- `/health/ready`
- `/metrics`
- correlation id nos headers e logs

## 7. Encerramento

Reforçar as decisões: k3s em EC2 para custo baixo, RDS para banco relacional gerenciado, Lambda/API Gateway para autenticação CPF e JWT compartilhado para integração entre bordas.

