# RFC: Authentication Strategy

## Status

Accepted for Phase 3 demo.

## Context

The platform has two authentication contexts:

- customers authenticating by CPF;
- administrators authenticating with the main API flow.

Phase 3 also requires a serverless function and API Gateway.

## Decision

Use API Gateway as the public entry point. Route CPF authentication to the
Lambda `service-order-auth-cpf`, and route application traffic to
`service-order-billing-service` running on k3s.

Customer authentication:

- Client sends CPF to `POST /auth/cpf`.
- Lambda validates CPF and checks `customers` in RDS.
- Lambda issues a JWT signed with `CUSTOMER_JWT_SECRET`.
- `service-order-billing-service` validates customer JWTs with the same
  `CUSTOMER_JWT_SECRET`.

Admin authentication:

- Admin JWTs remain owned by `service-order-billing-service`.
- Admin tokens are signed with `JWT_SECRET`.
- Admin and customer secrets are intentionally separate.

## Consequences

- The Lambda can evolve independently from the monolithic API.
- Customer JWT validation remains lightweight in the API.
- Secrets must be synchronized carefully between Lambda and API.
- API Gateway centralizes public ingress for the demo.

## Current Academic Limitation

The Lambda is owned by the `service-order-auth-lambda` repository. This API
repository only consumes the customer JWTs issued by that Lambda and documents
the public API Gateway route at a high level.

