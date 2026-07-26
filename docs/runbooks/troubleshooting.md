# Troubleshooting

## API sobe e cai em loop

Verificações:

- `docker compose --env-file .env.prod -f docker-compose.prod.yml logs api`
- validar `DATABASE_URL`
- validar segredos JWT e approval token
- confirmar se `APP_BASE_URL` e `SMTP_HOST` não são placeholders

## `/health/ready` retorna `503`

Verificações:

- `docker compose ps`
- conectividade EC2 -> RDS na porta `5432`
- Security Group do RDS permitindo origem do SG da EC2
- migrations aplicadas com sucesso

## Falha nas migrations

Verificações:

- `docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm migrate`
- revisar `DATABASE_URL`
- revisar versões do Alembic e estado do schema

## Login retorna `401`

Verificações:

- usuário registrado
- senha correta
- `JWT_SECRET` consistente entre geração e validação
- header `Authorization: Bearer <token>`

## Aprovação pública retorna `400` ou `410`

Verificações:

- token expirado
- token de outra OS
- segredo de aprovação alterado após geração do email
- relógio do servidor com horário correto

## Email não é enviado

Local:

- validar `SMTP_HOST=mailhog`
- abrir `http://localhost:8025`

Produção:

- validar `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME` e `SMTP_PASSWORD`
- testar conectividade de saída da EC2 para o provedor SMTP
- revisar logs da API

## Kubernetes Troubleshooting

### Pods em CrashLoopBackOff

```bash
kubectl logs -n service-order -l app=service-order-billing-service --tail=100

kubectl describe pod <pod-name> -n service-order

kubectl get pods -n service-order -o wide
```

Causas comuns:

- `DATABASE_URL` inválida ou inacessível
- Secrets não encontradas no namespace (`JWT_SECRET`, `APPROVAL_TOKEN_SECRET`)
- Image não disponível no registry
- Probe de readiness falhando (veja `/health/ready`)

### Pods em ImagePullBackOff

```bash

kubectl describe pod <pod-name> -n service-order

docker pull ghcr.io/<owner>/service-order-billing-service:sha-<commit>

kubectl get secret -n service-order | grep ghcr
```

### Migration Job Falhando

```bash
kubectl describe job service-order-billing-service-migrate -n service-order

kubectl logs job/service-order-billing-service-migrate -n service-order --all-containers=true

kubectl run -it --rm debug --image=busybox --restart=Never -- \
  sh -c "nc -zv <database-host> 5432"
```

Causas comuns:

- `DATABASE_URL` inválida ou incompleta
- Banco de dados não acessível da EC2/cluster
- Schema já existe e migration falha
- Alembic versioning corrompido

### Service não acessível

```bash

kubectl get endpoints -n service-order -o wide

kubectl port-forward -n service-order svc/service-order-billing-service 8002:80

curl http://localhost:8002/health
```

### Health check falhando

```bash
kubectl logs deployment/service-order-billing-service -n service-order --tail=100

kubectl exec -it <pod-name> -n service-order -- curl http://localhost:8000/health

kubectl get pod <pod-name> -n service-order -o yaml | grep -A 10 "readinessProbe\|livenessProbe"
```

### HPA não está escalando

```bash

kubectl get hpa -n service-order

kubectl top pod -n service-order
kubectl top node

kubectl get deployment metrics-server -n kube-system
```

Causas comuns:

- Metrics Server não instalado (Kubernetes padrão, mas k3s já vem com)
- Resource requests não definidos na Deployment
- CPU usage abaixo de 70%

---

## CI/CD Troubleshooting

### CI falha no publish

Verificações:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `ECR_REGISTRY`
- `ECR_REPOSITORY`

## CI falha no deploy

Verificações:

- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_PRIVATE_KEY`
- `APP_ENV_PROD`
- existência do diretório `/opt/service-order-billing-service` na EC2

## Checklist de segurança operacional

- remover arquivos `.env` do versionamento
- usar segredos fortes e distintos
- restringir `allowed_ssh_cidrs`
- restringir `app_ingress_cidrs`
- limitar `CORS_ALLOWED_ORIGINS`
- validar backups e retenção do RDS
- rotacionar credenciais do SMTP e do registry

