# Software Architecture & Engineering Design Interview Guide

This guide provides architectural rationales, design trade-offs, and technology selection analysis for senior engineering interviews (Google, Microsoft, Amazon, BlackRock, Stripe).

---

## 1. Core Framework & Storage Selection

### Q1: Why FastAPI over Django / Flask?
- **Rationale**: FastAPI leverages Python 3.12 `asyncio` natively, producing high IO throughput comparable to Node.js/Go. Pydantic V2 provides automatic schema validation compiled in Rust.
- **Trade-offs**: Django offers an out-of-the-box admin panel and ORM, but is synchronously bound by default. Flask lacks native async schema validation.
- **Alternatives Considered**: Go (Gin / Fiber), Node.js (NestJS). FastAPI was chosen to seamlessly integrate Python's AI/ML ecosystem (`sentence-transformers`, `tesseract`).

### Q2: Why PostgreSQL over MongoDB?
- **Rationale**: Financial and enterprise document metadata requires ACID compliance, relational integrity (users $\rightarrow$ documents $\rightarrow$ workflows), and robust JSONB indexing support.
- **Trade-offs**: Relational schema migrations require rigid planning via Alembic.
- **Alternatives Considered**: MongoDB, CockroachDB.

### Q3: Why Redis?
- **Rationale**: In-memory speed ($< 1\text{ ms}$ latency) for sliding-window rate limiting, token invalidation blacklists, and temporary result caching.
- **Alternatives**: Memcached (lacks rich data structures like sorted sets needed for sliding window rate limiters).

### Q4: Why RabbitMQ & Celery over Kafka?
- **Rationale**: Document processing task queues require task routing, retries, and worker ack mechanics rather than event stream playback. RabbitMQ provides light, low-overhead AMQP messaging.
- **Alternatives**: Apache Kafka (overkill for simple task queues; higher operational complexity).

### Q5: Why MinIO over local filesystem?
- **Rationale**: Provides S3 API compatibility, enabling local development while allowing seamless migration to AWS S3 / Google Cloud Storage without changing backend application code.

### Q6: Why Qdrant over Milvus / Pinecone?
- **Rationale**: Qdrant is written in Rust, provides fast vector indexing, low memory footprint, and native payload filtering.
- **Alternatives**: Pinecone (proprietary SaaS; violates local air-gapped enterprise requirements).

---

## 2. Architectural Design Patterns

### Q7: Why Hybrid Search (Dense Vector + BM25 Lexical)?
- **Rationale**: Dense vector embeddings excel at capturing semantic context, but fail with exact keyword match lookups (e.g. serial numbers, legal codes, financial ticker symbols). Combining dense vectors with BM25 via Reciprocal Rank Fusion (RRF) produces higher precision retrieval ($+24\%$ MRR).

### Q8: Why Repository Pattern & Clean Architecture?
- **Rationale**: Decouples business logic (`app/services`) from database driver mechanics (`app/repositories`). Enables mocking data layers during unit testing without needing live database connections.

### Q9: Why Event-Driven Architecture?
- **Rationale**: Prevents long-running OCR extraction or embedding generation from blocking HTTP request threads. Keeps API response times under 50ms while background workers process document workloads.

### Q10: Why Kubernetes & Helm?
- **Rationale**: Provides declarative scaling, rolling updates, self-healing pod recovery, resource quotas, and standardized multi-environment deployments.
