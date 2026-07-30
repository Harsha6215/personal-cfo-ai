"""
Personal CFO AI — AI Services
FastAPI application entry point for AI/agent workloads.
The backend calls this service internally. The frontend never calls this directly.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Personal CFO AI — AI Services",
    description="LangGraph agents, LLM workflows, and RAG pipelines.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  # only backend can call this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "ai-services"}


@app.get("/version", tags=["System"])
async def version():
    """Returns the current version."""
    return {"version": "0.1.0"}
