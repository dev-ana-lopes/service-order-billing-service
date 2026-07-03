# Runbook de Deploy em EC2 + RDS

## Objetivo

Executar deploy de produção da API com Kubernetes (`k3s`) na EC2 e PostgreSQL no RDS.

## Fluxo oficial (primário)

- Build e push da imagem no GHCR via GitHub Actions
- Conexão SSH do runner na EC2
- Execução de `prepare_env.py`, render de manifests e `kubectl apply/wait/rollout` dentro da EC2

## Pré-requisitos

- Infra criada pelo Terraform em `infra/`
- EC2 com `k3s`, `kubectl`, `docker` e acesso ao RDS
- Acesso SSH da pipeline para a EC2
- Repositório disponível em `/opt/service-order-billing-service` na EC2 (sincronizado no workflow)

## Configuração do GitHub (produção)

### Secrets

- `APP_ENV_PROD` (conteúdo do `.env.prod`)
- `EC2_SSH_KEY` (chave privada SSH)

### Variables

- `EC2_HOST` (IP/DNS público da EC2)
- `EC2_USER` (ex.: `ec2-user`)
- `EC2_PORT` (opcional, default `22`)

## Pipeline de deploy Kubernetes (CI/CD)

1. `validate` (PR/push): lint, testes, validação de render de manifests
2. `build-publish` (push/main): build + push para `ghcr.io/<owner>/service-order-billing-service:sha-<commit_sha>`
3. `deploy-k8s-ec2` (push/main): SSH na EC2 e execução do deploy no cluster local `k3s`

## Passo a passo manual (contingência)

Use este fluxo somente para operação assistida ou troubleshooting.

### 1. Conectar na EC2

```bash
ssh -i <key>.pem ec2-user@<ec2_public_ip>
```

### 2. Preparar ambiente

```bash
cd /opt/service-order-billing-service
cp .env.prod.example .env.prod
# preencher variáveis reais
python3 scripts/deploy/prepare_env.py .env.prod
```

### 3. Definir imagem do GHCR

```bash
export IMAGE_REF=ghcr.io/<owner>/service-order-billing-service:sha-<commit_sha>
```

### 4. Renderizar manifests com imagem explícita

```bash
python3 scripts/deploy/render_k8s_manifests.py \
  --env-file .env.prod \
  --output-dir .rendered-k8s \
  --image "${IMAGE_REF}" \
  --namespace service-order
```

### 5. Aplicar recursos no `k3s`

```bash
kubectl apply -f .rendered-k8s/namespace.yaml
kubectl apply -f .rendered-k8s/configmap.rendered.yaml -f .rendered-k8s/secret.rendered.yaml

kubectl delete job -n service-order service-order-billing-service-migrate --ignore-not-found
kubectl apply -f .rendered-k8s/job-migrate.yaml
kubectl wait --for=condition=complete job/service-order-billing-service-migrate -n service-order --timeout=300s

kubectl apply -f .rendered-k8s/deployment.yaml -f .rendered-k8s/service.yaml -f .rendered-k8s/hpa.yaml
kubectl rollout status deployment/service-order-billing-service -n service-order --timeout=300s
```

### 6. Validar pós-deploy

```bash
kubectl get all -n service-order -o wide
kubectl get hpa -n service-order
curl http://<ec2-public-ip>/health
curl http://<ec2-public-ip>/health/ready
```

## Fallback legado (Docker Compose)

O fluxo Compose permanece apenas para contingência operacional. Para esse procedimento, consulte `README.deploy.md`.

