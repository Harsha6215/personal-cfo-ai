# ai-services/

LangGraph-powered AI agents, LLM integrations, and prompt engineering.

## Responsibility
All AI capabilities live here — agents, prompt templates, RAG pipelines, embeddings, and LLM workflows. The backend calls this layer via internal APIs. The frontend never calls this layer directly.

## Stack
- **LangGraph** – agent orchestration and workflows
- **LangChain** – LLM abstractions and tooling
- **OpenAI / Anthropic / Bedrock** – LLM providers
- **ChromaDB / pgvector** – vector stores for RAG
- **FastAPI** – internal service API

## Structure

```
ai-services/
├── agents/          ← LangGraph agent definitions
├── prompts/         ← prompt templates (system, user, few-shot)
├── tools/           ← agent tools (web search, calculations, etc.)
├── memory/          ← conversation and long-term memory
├── rag/             ← retrieval-augmented generation pipelines
├── evaluation/      ← AI output evaluation and metrics
├── workflows/       ← multi-step LangGraph workflows
├── llms/            ← LLM provider wrappers and config
└── embeddings/      ← embedding models and vector operations
```

## Epic Scope Note
AI services are scaffolded in Epic 1 but remain empty until Epic 4 (AI Research Agents). Do not add agent logic here before Epic 4.

## Getting Started

```bash
# From repo root
docker compose up ai-services
```
