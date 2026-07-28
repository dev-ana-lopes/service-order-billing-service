# Arquitetura final — Fase 4

Este documento descreve a arquitetura implementada no ecossistema de ordens de serviço. A visão sistêmica e os contratos são mantidos nos três repositórios.

## Visão geral

![Diagrama geral da arquitetura](architecture-final.svg)

```text
flowchart LR
    Client[Cliente / Swagger / Postman] --> OS[os-service]
    OS --> OSDB[(PostgreSQL<br/>os_service_db)]
    OS <--> MQ[RabbitMQ<br/>service-order.events]
    MQ <--> Billing[billing-service<br/>FastAPI]
    Billing --> BillingDB[(PostgreSQL<br/>billing_service_db)]
    Billing --> MP[Mercado Pago<br/>Checkout Pro ou mock]
    MQ <--> Execution[execution-service<br/>FastAPI + worker]
    Execution --> ExecDB[(MongoDB<br/>execution_db)]
```

Cada serviço possui seu próprio banco e não acessa o banco dos demais. RabbitMQ transporta os eventos da Saga; HTTP expõe comandos e consultas. O `billing-service` consome `OS_OPENED`, cria o orçamento e publica eventos de orçamento e pagamento.

## Estratégia Saga: orquestração

A Saga é orquestrada pelo `os-service`, que mantém o estado global da OS e publica `EXECUTION_REQUESTED` depois de receber `PAYMENT_CONFIRMED`. O Billing não coordena o processo completo: ele é responsável apenas por orçamento e pagamento.

```text
flowchart LR
    OS[os-service] -->|OS_OPENED| B[billing-service]
    B -->|QUOTE_CREATED| OS
    B -->|QUOTE_APPROVED / PAYMENT_PREFERENCE_CREATED| OS
    B -->|PAYMENT_CONFIRMED ou PAYMENT_FAILED| OS
    OS -->|EXECUTION_REQUESTED| E[execution-service]
    E -->|EXECUTION_QUEUED / STARTED / COMPLETED / FAILED| OS
```

O envelope de cada evento contém `event_id`, `event_type`, `correlation_id`, `occurred_at` e `payload`. O worker grava eventos processados em `processed_events`, tornando o consumo idempotente. Falhas publicam `PAYMENT_FAILED` ou `EXECUTION_FAILED`; o orquestrador registra a compensação na OS sem tentar rollback entre bancos.

## Papel do billing-service

Este serviço é dono de:

- orçamento e seus itens/valor;
- aprovação do orçamento;
- pagamento e preferência de checkout;
- reconciliação do pagamento e publicação de `PAYMENT_CONFIRMED` ou `PAYMENT_FAILED`.

Em `PAYMENT_PROVIDER_MODE=mock`, o gateway fake permite testes determinísticos. Em `mercado_pago`, o adapter usa Checkout Pro e `external_reference=service_order_id`. A confirmação é feita por `POST /payments/{payment_id}/sync`, que consulta o Mercado Pago e valida referência, valor, moeda e unicidade. A implementação atual não usa webhook.

## Bancos e tecnologias

O PostgreSQL `billing_service_db` é acessado por SQLAlchemy, com Alembic para migrations e ownership exclusivo do Billing. RabbitMQ é acessado por adapters de publicação/consumo; o SDK do Mercado Pago fica isolado na infraestrutura atrás de `PaymentGatewayPort`. Python/FastAPI fornece a API e Swagger; Clean Architecture mantém regras de orçamento/pagamento independentes de HTTP, fila, banco e provedor.

Docker empacota API, worker e migration; Kubernetes/k3s separa os deployments e permite execução de baixo custo. GitHub Actions automatiza validações e deploy, e logs JSON com `correlation_id`/`request_id` apoiam a observabilidade.

## Justificativa da divisão

Financeiro tem regras, credenciais, persistência e ritmo de mudança próprios. Separá-lo de OS evita compartilhar tabelas e permite trocar o gateway ou alterar o modelo de pagamento sem alterar o domínio de execução. A fronteira exige eventos e consistência eventual, compensados por contratos explícitos, idempotência e orquestração central no `os-service`.

## Contratos relevantes

| Evento | Ação do Billing |
| --- | --- |
| `OS_OPENED` | cria e persiste orçamento; publica `QUOTE_CREATED` |
| aprovação do orçamento | cria pagamento/preferência; publica `QUOTE_APPROVED` e `PAYMENT_PREFERENCE_CREATED` |
| sincronização confirmada | atualiza pagamento; publica `PAYMENT_CONFIRMED` |
| sincronização recusada/falha | atualiza pagamento; publica `PAYMENT_FAILED` |

O Billing não lê PostgreSQL do `os-service` nem MongoDB do `execution-service`.
