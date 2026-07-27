# Project Architecture & Directory Layout Guide

```
c:\Users\DELL\kalpit_workspace\blackrockproject
├── app/
│   ├── api/                  # FastAPI V1 Routers & Endpoints
│   │   └── v1/
│   │       ├── endpoints/    # Auth, Documents, Processing, Search, Chat, AI, Workflows, Health, Observability
│   │       └── router.py     # Central V1 Aggregator Router
│   ├── core/                 # Infrastructural Abstractions
│   │   ├── cache/            # Redis Connection Manager & Cache Services
│   │   ├── config/           # Pydantic Settings & Environment Configurations
│   │   ├── database/         # SQLAlchemy Async Engine, Session Factory, Base Model
│   │   ├── exceptions/       # Custom Exception Hierarchy & Handlers
│   │   ├── logging/          # Contextvars & JSON Structured Formatter
│   │   ├── messaging/        # RabbitMQ aio-pika Connection Manager
│   │   ├── observability/    # Prometheus Metrics Registry, OTEL Tracing, Alerts Engine
│   │   ├── resiliency/       # CircuitBreaker, Connection Pool Metrics, Retry/Timeout policies
│   │   ├── security/         # Password Hashers, JWT Token Service, Cryptographic Utils
│   │   ├── storage/          # MinIO S3 Object Storage Provider
│   │   └── vector/           # Qdrant Vector DB Provider & Embedding Generators
│   ├── models/               # SQLAlchemy ORM Data Models (User, Document, Workflow, etc.)
│   ├── repositories/         # Data Access Layer implementing Repository Pattern
│   ├── schemas/              # Pydantic Schemas for Request Validation & Response Models
│   ├── services/             # Core Business Logic & Orchestration Services
│   ├── workers/              # Celery App Configuration & Asynchronous Worker Tasks
│   └── main.py               # Application Factory & ASGI Lifespan Entrypoint
├── deploy/                   # Infrastructure as Code (Kubernetes Manifests & Helm Chart)
│   ├── helm/                 # Production Helm Chart
│   └── k8s/                  # 13 Production Kubernetes Resource Manifests
├── docs/                     # Technical Guides, Diagrams, Benchmarks & Interview Material
├── migrations/               # Alembic Schema Migrations
├── scripts/                  # Security Scanning, DB Backup & Restore Scripts
├── tests/                    # Unit, Integration, Deployment & Load Test Suite
├── Dockerfile                # Multi-stage Container Specification
├── docker-compose.prod.yml   # Production Compose Profile
└── pyproject.toml            # Poetry Specifications & Tool Settings
```

---

## Package Responsibilities

- **`app/api/v1`**: Handles HTTP request parsing, status codes, OpenAPI route declarations, and dependency injections.
- **`app/core`**: Infrastructure foundation completely agnostic of specific domain rules. Contains database drivers, cache layers, security, logging, metrics, tracing, circuit breakers, and storage providers.
- **`app/models`**: Database schema definitions declared via SQLAlchemy declarative ORM base.
- **`app/repositories`**: Decouples business services from database operations via abstract data operations.
- **`app/schemas`**: Enforces strict input validation and serialization specs using Pydantic V2.
- **`app/services`**: Implements core business logic, RAG retrieval, OCR parsing, and workflow execution.
- **`app/workers`**: Background task handling using Celery and RabbitMQ for long-running CPU workloads.
