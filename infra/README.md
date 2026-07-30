# infra/

Infrastructure as code — cloud provisioning and deployment configuration.

## Responsibility
All infrastructure definitions live here. Currently scoped to local Docker Compose. Will expand in later epics to include cloud infrastructure (AWS/GCP/Azure).

## Structure

```
infra/
├── terraform/       ← Terraform modules (future epics)
├── k8s/             ← Kubernetes manifests (future epics)
└── env/             ← Environment-specific configs
    ├── local/
    ├── staging/
    └── production/
```

## Epic 1 Scope
Infrastructure in Epic 1 is limited to Docker Compose (`docker-compose.yml` at the project root). Terraform and Kubernetes are scoped to later epics when the platform is ready for cloud deployment.
