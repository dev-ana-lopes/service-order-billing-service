# RFC: Multi-Repository CI/CD Strategy

## Status

Accepted for Phase 3 demo.

## Repositories

- `service-order-billing-service`: FastAPI application, Docker image, k8s manifests and
  application deployment workflow.
- `service-order-auth-lambda`: CPF authentication Lambda, package artifact,
  tests, deployment notes and Lambda-specific infrastructure.
- `service-order-infra-k8s`: EC2/k3s infrastructure Terraform.
- `service-order-infra-db`: RDS PostgreSQL infrastructure Terraform.

## CI/CD Decisions

Application CI/CD is automated because the deployment target already exists and
the workflow can safely render manifests, run migrations and roll out a new
image in k3s.

Infrastructure CI validates Terraform but does not apply automatically. The
current AWS Academy resources were created from local Terraform state or manual
console workarounds. Running `terraform apply` from GitHub Actions with an
empty or different state could attempt to recreate existing VPC, security group,
EC2 or RDS resources.

The CPF authentication Lambda is owned by `service-order-auth-lambda`. The
`service-order-billing-service` workflow must not package, deploy or validate Terraform for
that Lambda.

## Current Validation

Repositories should keep workflows scoped to their ownership. Infrastructure
repositories validate Terraform; the API repository validates application code,
rendered manifests and k3s deployment behavior.

Common validation includes:

- formatting checks;
- tests where applicable;
- Terraform validation in infrastructure repositories when applicable.

## Production Path

For a real production setup:

1. Configure remote state with S3/DynamoDB or Terraform Cloud.
2. Import existing resources when needed.
3. Grant CI least-privilege AWS permissions.
4. Enable protected environment approval for `terraform apply`.
5. Keep application deploy independent from infrastructure apply.

