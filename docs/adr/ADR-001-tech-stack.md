# ADR-001: Tech Stack Selection

**Date:** 2026-07-30
**Status:** Accepted
**Deciders:** Engineering Team

---

## Context

We are building a personal finance AI platform (Personal CFO AI) that needs to:
- Serve a React-based web frontend
- Expose secure REST APIs
- Run AI agents and LLM workflows
- Store relational financial data (users, portfolios, holdings, transactions)
- Scale from personal use to potentially thousands of users

## Decision

### Frontend: React + TypeScript + Tailwind CSS
- React is the industry standard for interactive UIs
- TypeScript prevents runtime errors and improves refactoring confidence
- Tailwind enables rapid, consistent UI development without a heavy CSS framework
- shadcn/ui provides accessible, composable component primitives

### Backend: FastAPI (Python)
- FastAPI is the leading async Python web framework
- Native OpenAPI/Swagger support — docs are generated automatically
- Pydantic provides runtime data validation and environment-based config
- Python is the natural language for the AI services layer, ensuring consistency across backend and ai-services

### AI Services: LangGraph + LangChain
- LangGraph is purpose-built for stateful, multi-step agent workflows
- LangChain provides LLM-agnostic abstractions, enabling provider flexibility
- Keeps all AI logic isolated from the REST API layer

### Database: PostgreSQL + Redis
- PostgreSQL is the industry standard for relational financial data
- Redis handles session storage, caching, and rate limiting
- Alembic manages schema migrations with full version history

### Infrastructure: Docker + Docker Compose
- Ensures environment parity between development, CI, and production
- Single `docker compose up` command to start the entire stack
- Each service runs in an isolated container

## Consequences

- **Positive:** Clean separation of concerns; each layer can evolve independently
- **Positive:** React → FastAPI → AI Services architecture prevents frontend from directly calling AI
- **Positive:** All languages/frameworks are actively maintained with large ecosystems
- **Trade-off:** Two runtimes (Node.js for frontend, Python for backend/AI) require developers to be comfortable with both
- **Trade-off:** LangGraph adds complexity compared to direct LLM calls — justified when agent workflows become non-trivial
