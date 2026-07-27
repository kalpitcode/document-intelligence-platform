# Enterprise AI Document Intelligence Platform — Detailed Architecture Guide

## 1. Executive Summary & Design Philosophy
The **Enterprise AI Document Intelligence Platform** is built adhering to **Clean Architecture**, **SOLID principles**, the **Repository Pattern**, **Dependency Injection**, **Event-Driven Architecture**, and **Async Programming**.

The system decouples synchronous HTTP request/response lifecycles from heavy compute tasks (OCR processing, vector embedding generation, workflow DAG execution) via asynchronous messaging (RabbitMQ & Celery Workers).

---

## 2. Component Deep-Dives

### 2.1 Overall System Architecture
- **API Gateway Layer**: FastAPI application running ASGI Uvicorn servers behind NGINX Ingress.
- **Data Access Layer**: Asynchronous SQLAlchemy engine wrapping PostgreSQL 16 with repository pattern isolation.
- **Cache & Rate Limiting**: Redis 7 sliding window rate limiter and response cache.
- **Asynchronous Task Queue**: RabbitMQ message broker forwarding tasks to Celery worker pools.
- **Object Storage**: MinIO enterprise S3 object storage for raw and processed documents.
- **Vector Engine**: Qdrant vector database storing dense embeddings with payload filtering.

### 2.2 OCR Pipeline Architectural Rationale
The OCR pipeline processes multi-page PDF/DOCX documents:
1. Document byte streams uploaded to MinIO.
2. Async task pushed to RabbitMQ.
3. Celery worker executes PyMuPDF layout analysis and Tesseract OCR bounding-box text extraction.
4. Text is cleaned, normalized, and split into semantic chunks with metadata (page number, bounding box).

### 2.3 Knowledge Engine & Vector Indexing
1. Semantic text chunks passed to `sentence-transformers` (`all-MiniLM-L6-v2`).
2. Generates 384-dimensional dense floating-point vector representations.
3. Upserts vectors to Qdrant vector collections alongside structured payload metadata.

### 2.4 Hybrid Search Engine (Dense + BM25 Lexical)
Combines:
- **Dense Vector Search**: Cosine similarity match in Qdrant capturing semantic intent.
- **Lexical Keyword Search**: BM25 frequency matching for exact term alignment.
- **Reciprocal Rank Fusion (RRF)**: Merges ranked results using formula $RRF(d) = \sum \frac{1}{k + r(d)}$.

### 2.5 RAG Pipeline & Prompt Augmentation
1. Receives user query.
2. Performs hybrid vector search to retrieve top-$k$ context chunks.
3. Formulates structured system prompt with retrieved context.
4. Dispatches prompt to LLM provider via LiteLLM abstraction layer.

### 2.6 Workflow Engine Architecture
- Represents complex processing pipelines as Directed Acyclic Graphs (DAGs).
- Isolates individual execution steps with step status tracking (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`).

### 2.7 Observability & Reliability Layer
- **Prometheus Metrics**: High-performance thread-safe registry (`metrics_registry`).
- **Distributed Tracing**: OpenTelemetry W3C trace context (`traceparent`) propagation via `contextvars`.
- **Circuit Breaker**: Prevents cascading failures with `CLOSED` -> `OPEN` -> `HALF_OPEN` state transitions.

### 2.8 Kubernetes Deployment Architecture
Deployments scaled horizontally across nodes using Kubernetes HorizontalPodAutoscalers (HPA), protected by PodDisruptionBudgets (PDB), NetworkPolicies, and ResourceQuotas.
