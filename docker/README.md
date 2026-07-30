# docker/

Dockerfiles for each service.

## Structure

```
docker/
├── frontend.Dockerfile
├── backend.Dockerfile
└── ai-services.Dockerfile
```

## Usage

Dockerfiles here are referenced by `docker-compose.yml` at the project root.
Do not run them directly — use `docker compose up` from the root.
