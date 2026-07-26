# Enterprise AI Document Intelligence Platform

<p align="center">
  <strong>Production-grade enterprise platform for document intelligence, AI-powered search, and retrieval-augmented generation.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-blue.svg" alt="Python 3.12">
  <img src="https://img.shields.io/badge/FastAPI-0.115-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-red.svg" alt="SQLAlchemy 2.0">
  <img src="https://img.shields.io/badge/Pydantic-V2-orange.svg" alt="Pydantic V2">
  <img src="https://img.shields.io/badge/license-Proprietary-lightgrey.svg" alt="License">
</p>

---

## Overview

The Document Intelligence Platform enables organizations to:

- **Upload** documents in various formats
- **Extract** structured information using OCR and AI
- **Search** across millions of documents using semantic + keyword hybrid search
- **Interact** with documents through RAG-powered conversational AI
- **Automate** document workflows with intelligent routing

> **Current Status:** Foundation milestone — enterprise infrastructure, no business logic yet.

---

## Architecture

The platform follows **Clean Architecture** with strict separation of concerns:

```
┌─────────────────────────────────────────────────────┐
│                    API Layer                         │
│              (FastAPI Routes, Schemas)               │
├─────────────────────────────────────────────────────┤
│                  Service Layer                       │
│            (Business Logic, Orchestration)           │
├─────────────────────────────────────────────────────┤
│                Repository Layer                      │
│             (Data Access, Queries)                   │
├─────────────────────────────────────────────────────┤
│               Infrastructure Layer                   │
│     (Database, Cache, Messaging, Workers)            │
└─────────────────────────────────────────────────────┘
```

### Engineering Principles

| Principle | Implementation |
|-----------|---------------|
| Clean Architecture | Layered architecture with dependency inversion |
| SOLID | Single responsibility per module, dependency injection |
| Repository Pattern | Data access abstracted behind repository interfaces |
| 12-Factor App | Configuration via environment, stateless processes |
| DRY/KISS | Shared utilities, base classes, mixins |

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Language** | Python 3.12 |
| **Framework** | FastAPI |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic |
| **Database** | PostgreSQL 16 |
| **Cache** | Redis 7 |
| **Messaging** | RabbitMQ 3.13 |
| **Workers** | Celery 5.4 |
| **Validation** | Pydantic V2 |
| **Serialization** | ORJSON |
| **Container** | Docker + Docker Compose |
| **Dependencies** | Poetry |
| **Testing** | Pytest (async) |
| **Linting** | Ruff, Black, isort |

---

## Folder Structure

```
blackrockproject/
├── app/                          # Application source code
│   ├── __init__.py
│   ├── main.py                   # Application factory
│   ├── api/                      # API routes (versioned)
│   │   └── v1/
│   │       ├── router.py         # V1 router aggregator
│   │       └── endpoints/
│   │           ├── health.py     # Health/readiness/liveness
│   │           └── root.py       # Root + version endpoints
│   ├── core/                     # Core infrastructure
│   │   ├── config/               # Settings + environment configs
│   │   ├── database/             # SQLAlchemy engine + sessions
│   │   ├── cache/                # Redis connection manager
│   │   ├── messaging/            # RabbitMQ connection manager
│   │   ├── logging/              # Structured logging (JSON/console)
│   │   └── exceptions/           # Exception hierarchy + handlers
│   ├── schemas/                  # Pydantic V2 request/response models
│   ├── models/                   # SQLAlchemy ORM models (future)
│   ├── repositories/             # Data access layer (future)
│   ├── services/                 # Business logic layer (future)
│   ├── workers/                  # Celery tasks + configuration
│   ├── middlewares/              # CORS, Request ID, Logging, Timing
│   ├── dependencies/             # FastAPI dependency injection
│   └── utils/                    # Shared utilities
├── tests/                        # Test suite
│   ├── conftest.py               # Shared fixtures
│   ├── api/                      # API endpoint tests
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── migrations/                   # Alembic database migrations
├── scripts/                      # Startup and utility scripts
├── docs/                         # Project documentation
├── pyproject.toml                # Poetry + tool configuration
├── Dockerfile                    # Multi-stage production build
├── docker-compose.yml            # Full infrastructure stack
└── docker-compose.override.yml   # Development overrides
```

---

## Setup

### Prerequisites

- **Python 3.12+**
- **Docker** and **Docker Compose**
- **Poetry** (Python package manager)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd blackrockproject
   ```

2. **Copy environment configuration:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Install dependencies:**
   ```bash
   pip install poetry
   poetry install
   ```

4. **Install pre-commit hooks:**
   ```bash
   poetry run pre-commit install
   ```

---

## Running Locally

### With Docker (Recommended)

Start all services with hot-reload:

```bash
docker-compose up -d --build
```

Access the application:
- **API:** http://localhost:8000/api/v1/
- **API Docs:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc
- **Health:** http://localhost:8000/api/v1/health
- **RabbitMQ UI:** http://localhost:15672 (dip_user / dip_password)

### Without Docker

Start infrastructure services separately, then:

```bash
# Using the dev script
bash scripts/start-dev.sh

# Or directly with Uvicorn
poetry run uvicorn app.main:app --reload --port 8000
```

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=app --cov-report=html

# Specific test types
bash scripts/run-tests.sh unit
bash scripts/run-tests.sh api
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Runtime environment |
| `APP_DEBUG` | `false` | Enable debug mode |
| `APP_PORT` | `8000` | Server port |
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_USER` | `dip_user` | Database user |
| `POSTGRES_PASSWORD` | — | Database password |
| `POSTGRES_DB` | `document_intelligence` | Database name |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `RABBITMQ_HOST` | `localhost` | RabbitMQ host |
| `RABBITMQ_PORT` | `5672` | RabbitMQ port |
| `LOG_LEVEL` | `INFO` | Log level |
| `LOG_FORMAT` | `json` | Log format (json/console) |

See `.env.example` for the complete list.

---

## Development Workflow

1. **Create a feature branch** from `main`.
2. **Write code** following the architecture patterns.
3. **Write tests** for all new functionality.
4. **Run linters:**
   ```bash
   poetry run ruff check app/ tests/
   poetry run black app/ tests/
   poetry run isort app/ tests/
   ```
5. **Run tests:**
   ```bash
   poetry run pytest
   ```
6. **Submit a pull request** with a clear description.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/` | API root with metadata |
| `GET` | `/api/v1/version` | Application version |
| `GET` | `/api/v1/health` | Full system health check |
| `GET` | `/api/v1/health/live` | Liveness probe |
| `GET` | `/api/v1/health/ready` | Readiness probe |

---

## Future Roadmap

### Phase 2 — Authentication & Authorization
- JWT-based authentication
- Role-Based Access Control (RBAC)
- API key management

### Phase 3 — Document Management
- Document upload with MinIO storage
- OCR with Tesseract/Azure Form Recognizer
- Metadata extraction

### Phase 4 — AI & Search
- Vector embeddings with Qdrant
- Semantic search with OpenSearch
- Hybrid search (keyword + vector)

### Phase 5 — RAG & Chat
- Retrieval-Augmented Generation
- Conversational AI chat interface
- Context-aware document Q&A

### Phase 6 — Observability
- Prometheus metrics
- Grafana dashboards
- Distributed tracing

### Phase 7 — Workflow Automation
- Document processing pipelines
- Approval workflows
- Event-driven automation

---

## License

Proprietary — BlackRock, Inc. All rights reserved.
