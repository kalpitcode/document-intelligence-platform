# Enterprise AI Document Intelligence Platform — Architecture & System Design

## 1. Overall System Architecture

```mermaid
graph TD
    Client[Client Applications / Web Frontends] -->|HTTPS / REST API| Ingress[Ingress Controller / NGINX]
    Ingress -->|Route /api/v1| API[FastAPI Application Instances]
    
    subgraph Core Platform Plumbing
        API --> DB[(PostgreSQL Database)]
        API --> Cache[(Redis Cache & Rate Limiter)]
        API --> Queue[(RabbitMQ Message Broker)]
    end

    subgraph Document Processing & Vector Search
        Queue --> Worker[Celery Worker Cluster]
        Worker --> Storage[(MinIO Object Storage)]
        Worker --> OCR[OCR & Document Parsing Engine]
        Worker --> Embed[Embedding Generator]
        Embed --> Qdrant[(Qdrant Vector Database)]
    end

    subgraph LLM & RAG Orchestration
        API --> RAG[RAG & Hybrid Search Engine]
        RAG --> Qdrant
        RAG --> LLM[LiteLLM Provider API / Ollama]
    end

    subgraph Monitoring & Observability
        API --> Prometheus[Prometheus Exporter /metrics]
        API --> OTEL[OpenTelemetry Tracing Context]
    end
```

---

## 2. OCR & Document Processing Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI Gateway
    participant MinIO as MinIO S3 Storage
    participant Celery as Celery Task Queue
    participant Worker as OCR Pipeline Worker
    participant DB as Postgres Database

    User->>API: POST /api/v1/documents (Upload File)
    API->>MinIO: Store raw document binary
    API->>DB: Record Document Model (PENDING)
    API->>Celery: Publish 'process_document' task
    API-->>User: HTTP 202 Accepted (Document ID)

    Celery->>Worker: Consume processing task
    Worker->>MinIO: Fetch raw document
    Worker->>Worker: Run Tesseract / PyMuPDF OCR
    Worker->>Worker: Extract Structured Layout & Tables
    Worker->>DB: Save Processed Document Metadata & Chunks (COMPLETED)
```

---

## 3. RAG Query & Conversational Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI Chat Endpoint
    participant Embed as Sentence Transformer Model
    participant Qdrant as Qdrant Vector Engine
    participant LLM as LiteLLM Model Provider

    User->>API: POST /api/v1/chat/query (Prompt)
    API->>Embed: Generate Query Vector Embedding
    Embed-->>API: Dense Vector Representation
    API->>Qdrant: Hybrid Vector + BM25 Lexical Search
    Qdrant-->>API: Relevant Document Chunks & Context
    API->>LLM: Formulate Prompt with Context
    LLM-->>API: Generated Answer & Citations
    API-->>User: Structured Response + Source References
```

---

## 4. Workflow Engine Orchestration

```mermaid
graph LR
    Start([Workflow Trigger]) --> Validate[Validate Input]
    Validate --> Step1[Step 1: Document OCR]
    Step1 --> Step2[Step 2: Table Extraction]
    Step2 --> Step3[Step 3: Chunking & Embedding]
    Step3 --> Step4[Step 4: Vector Indexing]
    Step4 --> Finish([Workflow Complete])
```

---

## 5. Deployment Architecture & K8s Topology

```mermaid
graph TB
    subgraph Kubernetes Cluster: dip-production
        Ingress[Ingress NGINX Controller]
        
        subgraph Pods Deployment
            API1[API Pod 1]
            API2[API Pod 2]
            API3[API Pod 3]
        end

        subgraph Worker Deployment
            W1[Celery Worker 1]
            W2[Celery Worker 2]
        end

        Ingress --> API1
        Ingress --> API2
        Ingress --> API3
    end
```
