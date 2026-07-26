# Solution Architecture

## Plataforma local

```mermaid
flowchart TB
    Dev["Desenvolvedor / Banca"] --> Compose["docker compose"]

    subgraph Local["Ambiente local"]
        Compose --> API["API FastAPI<br/>localhost:8002"]
        Compose --> DB["PostgreSQL<br/>localhost:5432"]
        Compose --> MailHog["MailHog<br/>localhost:8025 / localhost:1025"]
    end

    API --> DB
    API --> MailHog
```

### Objetivo do ambiente local

- desenvolvimento rápido;
- demonstração do fluxo de orçamento por e-mail;
- execução de testes funcionais com MailHog;
- smoke test do Compose.

## Plataforma de demonstração na AWS

```mermaid
flowchart TB
    Dev["GitHub Actions"] --> GHCR["GHCR"]
    Dev --> TF["Terraform"]
    TF --> AWS["AWS Academy"]

    subgraph AWS["Conta AWS Academy"]
        subgraph Network["VPC simples"]
            EC2["EC2 t3.small ou t3.medium<br/>k3s single-node"]
            RDS["RDS PostgreSQL<br/>db.t4g.micro"]
        end
    end

    GHCR --> EC2
    EC2 --> Pod["service-order-billing-service pod(s)"]
    Pod --> RDS
```

### Componentes

- Terraform provisiona rede, EC2, security groups e RDS;
- `k3s` hospeda a API e o HPA;
- GHCR distribui a imagem da aplicação;
- GitHub Actions valida e publica os artefatos.

## Desenho do deploy em `k3s`

```mermaid
flowchart LR
    Render["render_k8s_manifests.py"] --> Config["ConfigMap renderizado"]
    Render --> Secret["Secret renderizado"]
    Render --> Job["Job de migrate"]
    Render --> Deploy["Deployment"]
    Render --> HPA["HPA"]
    Render --> Service["Service LoadBalancer"]

    Job --> DB["RDS PostgreSQL"]
    Deploy --> DB
    HPA --> Deploy
```

## Trade-offs assumidos

- `k3s` single-node prioriza custo e simplicidade;
- o HPA demonstra escalabilidade de pods, não de nós;
- o RDS fora do cluster melhora clareza arquitetural para a banca;
- GHCR evita adicionar um registry AWS extra na demonstração.

