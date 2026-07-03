# Arquitetura da solução

## Visão geral

O sistema é um backend monolítico em FastAPI organizado em camadas inspiradas em Clean Architecture. A regra de negócio central é a gestão da ordem de serviço, incluindo abertura, orçamento, aprovação ou recusa e evolução operacional até entrega.

## Desenho visual das camadas

```mermaid
flowchart LR
    Client["Administrador / Cliente / Postman / Swagger"] --> Presentation["Presentation<br/>FastAPI routes<br/>Schemas<br/>Serializers"]

    subgraph Monolith["Monólito FastAPI"]
        Presentation --> Application["Application<br/>Use cases"]
        Application --> Domain["Domain<br/>Entities<br/>Enums<br/>Rules<br/>Ports"]
        Presentation --> Dependencies["Dependency wiring"]
        Dependencies --> Infrastructure
        Infrastructure["Infrastructure<br/>Repositories<br/>DB session<br/>JWT<br/>Email<br/>Settings<br/>Logging"] --> Domain
    end

    Infrastructure --> Postgres["PostgreSQL / RDS"]
    Infrastructure --> Email["SMTP / MailHog / NOOP"]
    Infrastructure --> Secrets["Env vars / GitHub Secrets / K8S Secret"]
```

## Como os componentes se conversam

### Regra principal

- `presentation` recebe a requisição HTTP e valida o payload;
- `presentation` chama um caso de uso da camada `application`;
- `application` usa contratos definidos pelo `domain`;
- `infrastructure` implementa esses contratos e fala com banco, JWT e e-mail;
- `domain` concentra as regras de negócio e não depende de FastAPI, SQLAlchemy ou SMTP.

### Dependências entre camadas

```mermaid
flowchart TD
    Presentation --> Application
    Application --> Domain
    Infrastructure --> Domain
    Presentation --> Infrastructure
```

- `presentation -> application`: orquestração dos casos de uso;
- `application -> domain`: regras, entidades e contratos;
- `infrastructure -> domain`: implementação de contratos;
- `presentation -> infrastructure`: somente para montagem de dependências.

## Fluxo principal de requisição

### Abertura da OS

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant API as FastAPI Route
    participant UC as CreateServiceOrderUseCase
    participant Cust as CustomerRepository
    participant Veh as VehicleRepository
    participant SO as ServiceOrderRepository
    participant Mail as EmailSender

    Admin->>API: POST /service-orders
    API->>UC: CreateServiceOrderDTO
    UC->>Cust: localizar ou criar cliente
    UC->>Veh: localizar ou criar veículo
    UC->>SO: salvar OS em WAITING_APPROVAL
    UC->>Mail: enviar orçamento com links
    API-->>Admin: 201 Created + service_order_id
```

### Recusa do orçamento por e-mail

```mermaid
sequenceDiagram
    actor Customer as Cliente
    participant Mail as E-mail / MailHog
    participant Public as Public Route
    participant Token as ApprovalTokenService
    participant Decision as ApplyServiceOrderApprovalDecisionUseCase
    participant Repo as ServiceOrderRepository

    Mail-->>Customer: link Rejeitar
    Customer->>Public: GET /public/service-orders/{id}/approval?token=...
    Public->>Token: validar token
    Public->>Decision: executar recusa
    Decision->>Repo: carregar OS WAITING_APPROVAL
    Decision->>Repo: persistir approval_decision=REJECTED
    Decision->>Repo: transicionar status para DIAGNOSIS
    Public-->>Customer: 200 + decision=REJECTED + status=DIAGNOSIS
```

## Fluxo da arquitetura limpa na prática

### Domain

- entidades: `ServiceOrder`, `Customer`, `Vehicle`, `CatalogService`, `InventoryPart`, `User`;
- enums: `ServiceOrderStatus`, `ApprovalDecision`;
- contratos: repositórios e serviços;
- regras centrais:
  - cálculo do orçamento;
  - transição de status;
  - aprovação e recusa do orçamento.

### Application

- encapsula os casos de uso;
- coordena persistência, autenticação e notificações;
- não conhece detalhes do framework HTTP.

Casos de uso centrais:

- autenticação e registro;
- CRUD de clientes, veículos, catálogo e peças;
- criação e consulta de ordens de serviço;
- aprovação e recusa do orçamento;
- atualização manual de status;
- métricas de tempo médio de execução.

### Infrastructure

- implementa repositórios com PostgreSQL;
- implementa autenticação JWT;
- implementa envio de e-mail via SMTP ou NOOP;
- concentra settings, segredos e logging.

### Presentation

- expõe as rotas FastAPI;
- valida request/response;
- traduz payload HTTP em DTOs e entidades serializadas.

## Decisões de modelagem relevantes

- a recusa do orçamento não cria `status=REJECTED`;
- o estado operacional da OS volta para `DIAGNOSIS`;
- a decisão do orçamento fica em `approval_decision=REJECTED`;
- isso separa claramente workflow da oficina de decisão comercial do cliente.

## Deploy e operação

### Pipeline

```mermaid
flowchart LR
    Dev["Push / PR"] --> GHA["GitHub Actions"]
    GHA --> CI["Lint + Tests + Coverage + Docker + Terraform + K8S validation"]
    CI --> GHCR["GHCR"]
    GHCR --> K3S["EC2 com k3s"]
    K3S --> API["Deployment service-order-billing-service"]
    API --> RDS["RDS PostgreSQL"]
```

### Estratégia operacional

- local: `docker-compose.yml` com MailHog para demonstração do fluxo de e-mail;
- demo principal: `k3s` single-node em EC2;
- banco fora do cluster: RDS PostgreSQL;
- fallback preservado: deploy legado com Docker Compose.

